import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";

export const LogoutBtn = () => {
  const [isAuthenticated, setIsAuthenticated] = useState(null);

  useEffect(() => {
    const verifyAuth = async () => {
      try {
        const response = await fetch(`${process.env.BACKEND_URL}/protected`, {
          method: "GET",
          credentials: "include",
        });

        if (response.ok) {
          setIsAuthenticated(true);
        } else {
          setIsAuthenticated(false);
        }
      } catch (error) {
        setIsAuthenticated(false);
      }
    };

    verifyAuth();
  }, []);

  const handleLogout = async () => {
    try {
      const response = await fetch(`${process.env.BACKEND_URL}/logout`, {
        method: "POST",
        credentials: "include",
      });

      if (!response.ok) {
        throw new Error("Error al cerrar sesión");
      }

      localStorage.removeItem("token");

      window.location.href = "/";
    } catch (error) {
      console.error(error);
    }
  };

  if (!isAuthenticated) {
    return null;
  }

  return (
    <Link to="/" onClick={handleLogout}>
      <button className="btn btn-danger">Cerrar sesión</button>
    </Link>
  );
};
