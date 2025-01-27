"""
This module takes care of starting the API Server, Loading the DB and Adding the endpoints
"""
import os
from flask import Flask, request, jsonify, url_for, send_from_directory, make_response
from flask_cors import CORS
from flask_migrate import Migrate
from flask_swagger import swagger
from api.utils import APIException, generate_sitemap
from api.models import db
from api.routes import api
from api.admin import setup_admin
from api.commands import setup_commands
import jwt
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta

from api.models import User

ENV = "development" if os.getenv("FLASK_DEBUG") == "1" else "production"
static_file_dir = os.path.join(os.path.dirname(
    os.path.realpath(__file__)), '../public/')
app = Flask(__name__)
app.url_map.strict_slashes = False

CORS(app, supports_credentials=True, origins=["http://localhost:3000"])

db_url = os.getenv("DATABASE_URL")
if db_url is not None:
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url.replace(
        "postgres://", "postgresql://")
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:////tmp/test.db"

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = "mi-clave-super-secreta"
MIGRATE = Migrate(app, db, compare_type=True)
db.init_app(app)

setup_admin(app)

setup_commands(app)

app.register_blueprint(api, url_prefix='/api')


@app.errorhandler(APIException)
def handle_invalid_usage(error):
    return jsonify(error.to_dict()), error.status_code

@app.route('/')
def sitemap():
    if ENV == "development":
        return generate_sitemap(app)
    return send_from_directory(static_file_dir, 'index.html')

@app.route('/<path:path>', methods=['GET'])
def serve_any_other_file(path):
    if not os.path.isfile(os.path.join(static_file_dir, path)):
        path = 'index.html'
    response = send_from_directory(static_file_dir, path)
    response.cache_control.max_age = 0 
    return response

@app.route('/api/signup', methods=['POST'])
def signup():
    body = request.get_json()

    if not body or not body.get('email') or not body.get('password'):
        return jsonify({"msg": "Email and password are required"}), 400

    username = body.get('username')
    email = body['email']
    password = body['password']

    existing_user = db.session.query(User).filter_by(email=email).first()
    if existing_user:
        return jsonify({"msg": "User already exists"}), 400

    hashed_password = generate_password_hash(password)

    new_user = User(username=username, email=email, password=hashed_password, is_active=True)
    db.session.add(new_user)
    db.session.commit()

    token = jwt.encode({
        'id': new_user.id,
        'exp': datetime.utcnow() + timedelta(days=1)
    }, app.config['JWT_SECRET_KEY'], algorithm="HS256")

    response = make_response({"msg": "User created"})

    response.set_cookie(
        'access_token',
        token,
        httponly=True,
        secure=True,
        samesite='None'
    )

    return response

@app.route('/api/login', methods=['POST'])
def login():
    body = request.get_json()

    if not body or not body.get('email') or not body.get('password'):
        return jsonify({"msg": "Email and password are required"}), 400

    email = body['email']
    password = body['password']

    user = db.session.query(User).filter_by(email=email).first()
    if not user:
        return jsonify({"msg": "User does not exist"}), 400

    if not check_password_hash(user.password, password):
        return jsonify({"msg": "Invalid password"}), 400

    token = jwt.encode({
        'id': user.id,
        'exp': datetime.utcnow() + timedelta(days=1)
    }, app.config['JWT_SECRET_KEY'], algorithm="HS256")

    response = make_response({"msg": "Login successful"})

    response.set_cookie(
        'access_token',
        token,
        httponly=True,
        secure=True,
        samesite='None'
    )

    return response

@app.route('/api/logout', methods=['POST'])
def logout():
    response = make_response({"msg": "Logout successful"})

    response.set_cookie(
        'access_token',
        '',
        httponly=True,
        secure=True,
        samesite='None',
        expires=0
    )

    return response

@app.route('/api/protected', methods=['GET'])
def protected():
    token = request.cookies.get('access_token')

    if not token:
        return jsonify({"msg": "Missing token"}), 400

    try:
        payload = jwt.decode(token, app.config['JWT_SECRET_KEY'], algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        return jsonify({"msg": "Token has expired"}), 400
    except jwt.InvalidTokenError:
        return jsonify({"msg": "Invalid token"}), 400

    user = db.session.query(User).get(payload['id'])

    return jsonify({"msg": f"Welcome {user.username}"})
