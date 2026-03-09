import React from "react";
import { NavLink } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";

const Layout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, logout } = useAuth();

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="brand-block">
          <span className="brand-caption">Smart Data</span>
          <strong className="brand-title">SD Framework</strong>
        </div>
        <nav className="sidebar-nav">
          <NavLink to="/" end className={({ isActive }) => `sidebar-link${isActive ? " active" : ""}`}>
            Dashboard
          </NavLink>
          <NavLink to="/clientes" className={({ isActive }) => `sidebar-link${isActive ? " active" : ""}`}>
            Clientes
          </NavLink>
        </nav>
        <div className="sidebar-footer">
          <span className="user-name">{user?.usuNome}</span>
          <button type="button" onClick={logout}>
            Sair
          </button>
        </div>
      </aside>

      <div className="content-area">
        <header className="top-header">
          <h1>Painel administrativo</h1>
          <p>Gerencie dados e padroes visuais com uma interface unificada.</p>
        </header>
        <main className="app-main">{children}</main>
      </div>
    </div>
  );
};

export default Layout;

