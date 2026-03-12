import React, { useCallback, useEffect, useState } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";

const SIDEBAR_OPEN_KEY = "sd_sidebar_groups";

interface EmpresaItem {
  empId: number;
  empNome: string;
}

interface HeaderData {
  breadcrumb: string[];
  title: string;
  description: string;
}

const SidebarIcon: React.FC<{ kind: "dashboard" | "crm" | "cadastros" | "usuarios" }> = ({ kind }) => {
  const iconMap = {
    dashboard: (
      <path d="M3 3h8v8H3zM13 3h8v5h-8zM13 10h8v11h-8zM3 13h8v8H3z" />
    ),
    crm: (
      <path d="M3 4h18v4H3zM3 10h18v4H3zM3 16h12v4H3z" />
    ),
    cadastros: (
      <path d="M5 3h11l3 3v15H5zM16 3v4h4M8 12h8M8 16h8" />
    ),
    usuarios: (
      <path d="M12 12a4 4 0 100-8 4 4 0 000 8zm-7 9a7 7 0 0114 0" />
    ),
  } as const;

  return (
    <span className="sidebar-main-icon" aria-hidden>
      <svg viewBox="0 0 24 24" focusable="false">
        {iconMap[kind]}
      </svg>
    </span>
  );
};

function getStoredOpen(): Record<string, boolean> {
  try {
    const s = localStorage.getItem(SIDEBAR_OPEN_KEY);
    if (s) return JSON.parse(s) as Record<string, boolean>;
  } catch {
    /* ignore */
  }
  return { crm: false, cadastros: false };
}

function setStoredOpen(open: Record<string, boolean>) {
  try {
    localStorage.setItem(SIDEBAR_OPEN_KEY, JSON.stringify(open));
  } catch {
    /* ignore */
  }
}

function getHeaderData(pathname: string): HeaderData {
  if (pathname === "/") {
    return {
      breadcrumb: ["Dashboard"],
      title: "Dashboard",
      description: "Visão geral do sistema e indicadores principais.",
    };
  }
  if (pathname.startsWith("/oportunidades-kanban")) {
    return {
      breadcrumb: ["Dashboard", "CRM", "Kanban"],
      title: "Kanban de Oportunidades",
      description: "Acompanhe o pipeline de oportunidades por etapa.",
    };
  }
  if (pathname.startsWith("/oportunidades/")) {
    return {
      breadcrumb: ["Dashboard", "CRM", "Oportunidades"],
      title: "Detalhe da Oportunidade",
      description: "Visualize informações completas e histórico da oportunidade.",
    };
  }
  if (pathname.startsWith("/oportunidades")) {
    return {
      breadcrumb: ["Dashboard", "CRM", "Oportunidades"],
      title: "Oportunidades",
      description: "Gerencie oportunidades e acompanhe o funil comercial.",
    };
  }
  if (pathname.startsWith("/empresas")) {
    return {
      breadcrumb: ["Dashboard", "CRM", "Empresas"],
      title: "Empresas",
      description: "Gerencie as empresas habilitadas no ambiente.",
    };
  }
  if (pathname.startsWith("/usuarios")) {
    return {
      breadcrumb: ["Dashboard", "Administração", "Usuários"],
      title: "Usuários",
      description: "Gerencie perfis, acessos e status dos usuários.",
    };
  }
  if (pathname.startsWith("/produtos")) {
    return {
      breadcrumb: ["Dashboard", "Cadastros", "Produtos"],
      title: "Produtos",
      description: "Mantenha o catálogo de produtos e serviços.",
    };
  }
  if (pathname.startsWith("/etapas-kanban")) {
    return {
      breadcrumb: ["Dashboard", "Cadastros", "Etapas Kanban"],
      title: "Etapas Kanban",
      description: "Configure etapas do funil e ordem de execução.",
    };
  }
  if (pathname.startsWith("/motivos-cancelamento")) {
    return {
      breadcrumb: ["Dashboard", "Cadastros", "Motivos de Cancelamento"],
      title: "Motivos de Cancelamento",
      description: "Padronize motivos para fechamento perdido.",
    };
  }
  if (pathname.startsWith("/como-conheceu")) {
    return {
      breadcrumb: ["Dashboard", "Cadastros", "Como Conheceu"],
      title: "Como Conheceu",
      description: "Gerencie origens e canais de aquisição.",
    };
  }
  if (pathname.startsWith("/clientes")) {
    return {
      breadcrumb: ["Dashboard", "CRM", "Clientes"],
      title: "Clientes",
      description: "Acompanhe o cadastro e status dos clientes.",
    };
  }
  return {
    breadcrumb: ["Dashboard"],
    title: "Painel",
    description: "Gerencie dados e padroes visuais com uma interface unificada.",
  };
}

const Layout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, logout, companyId, setCompanyId, api } = useAuth();
  const [empresas, setEmpresas] = useState<EmpresaItem[]>([]);
  const [openGroups, setOpenGroups] = useState<Record<string, boolean>>(getStoredOpen);
  const location = useLocation();
  const headerData = getHeaderData(location.pathname);

  const toggleGroup = useCallback((key: string) => {
    setOpenGroups((prev) => {
      const next = { ...prev, [key]: !prev[key] };
      setStoredOpen(next);
      return next;
    });
  }, []);

  useEffect(() => {
    if (!user) return;
    api
      .get<{ items: EmpresaItem[] }>("/empresas")
      .then((res) => {
        const list = res.data.items ?? [];
        setEmpresas(list);
        if (list.length === 1 && companyId === null) {
          setCompanyId(list[0].empId);
        }
      })
      .catch(() => setEmpresas([]));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]);

  // Auto-expand group when current route is inside it
  useEffect(() => {
    const path = location.pathname;
    setOpenGroups((prev) => {
      let next = prev;
      if ((path.startsWith("/oportunidades") || path.startsWith("/oportunidades-kanban")) && !prev.crm) {
        next = { ...prev, crm: true };
        setStoredOpen(next);
      }
      if (
        (path.startsWith("/como-conheceu") ||
          path.startsWith("/motivos-cancelamento") ||
          path.startsWith("/produtos") ||
          path.startsWith("/etapas-kanban") ||
          path.startsWith("/empresas")) &&
        !prev.cadastros
      ) {
        next = { ...next, cadastros: true };
        setStoredOpen(next);
      }
      return next;
    });
  }, [location.pathname]);

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="brand-block">
          <span className="brand-caption">Smart Data</span>
          <strong className="brand-title">SD Framework</strong>
        </div>
        {empresas.length > 0 && (
          <div className="sidebar-company">
            <label className="sidebar-company-label">Empresa</label>
            <select
              className="sidebar-company-select"
              value={companyId ?? ""}
              onChange={(e) => setCompanyId(e.target.value ? Number(e.target.value) : null)}
            >
              <option value="">Selecione</option>
              {empresas.map((e) => (
                <option key={e.empId} value={e.empId}>
                  {e.empNome}
                </option>
              ))}
            </select>
          </div>
        )}
        <nav className="sidebar-nav">
          <NavLink to="/" end className={({ isActive }) => `sidebar-link${isActive ? " active" : ""}`}>
            <span className="sidebar-link-main">
              <SidebarIcon kind="dashboard" />
              <span>Dashboard</span>
            </span>
          </NavLink>

          <div className="sidebar-group">
            <button
              type="button"
              className={`sidebar-group-toggle ${openGroups.crm ? " is-open" : ""}`}
              onClick={() => toggleGroup("crm")}
              aria-expanded={openGroups.crm}
            >
              <span className="sidebar-group-label">
                <SidebarIcon kind="crm" />
                <span>CRM</span>
              </span>
              <span className="sidebar-group-icon" aria-hidden>▼</span>
            </button>
            {openGroups.crm && (
              <div className="sidebar-group-items">
                <NavLink to="/oportunidades" className={({ isActive }) => `sidebar-link sidebar-link--nested${isActive ? " active" : ""}`}>
                  Oportunidades
                </NavLink>
                <NavLink to="/oportunidades-kanban" className={({ isActive }) => `sidebar-link sidebar-link--nested${isActive ? " active" : ""}`}>
                  Kanban
                </NavLink>
              </div>
            )}
          </div>

          <div className="sidebar-group">
            <button
              type="button"
              className={`sidebar-group-toggle ${openGroups.cadastros ? " is-open" : ""}`}
              onClick={() => toggleGroup("cadastros")}
              aria-expanded={openGroups.cadastros}
            >
              <span className="sidebar-group-label">
                <SidebarIcon kind="cadastros" />
                <span>Cadastros</span>
              </span>
              <span className="sidebar-group-icon" aria-hidden>▼</span>
            </button>
            {openGroups.cadastros && (
              <div className="sidebar-group-items">
                <NavLink to="/como-conheceu" className={({ isActive }) => `sidebar-link sidebar-link--nested${isActive ? " active" : ""}`}>
                  Como conheceu
                </NavLink>
                <NavLink to="/motivos-cancelamento" className={({ isActive }) => `sidebar-link sidebar-link--nested${isActive ? " active" : ""}`}>
                  Motivos cancelamento
                </NavLink>
                <NavLink to="/produtos" className={({ isActive }) => `sidebar-link sidebar-link--nested${isActive ? " active" : ""}`}>
                  Produtos
                </NavLink>
                <NavLink to="/etapas-kanban" className={({ isActive }) => `sidebar-link sidebar-link--nested${isActive ? " active" : ""}`}>
                  Etapas Kanban
                </NavLink>
                {user?.usuAdmin && (
                  <NavLink to="/empresas" className={({ isActive }) => `sidebar-link sidebar-link--nested${isActive ? " active" : ""}`}>
                    Empresas
                  </NavLink>
                )}
              </div>
            )}
          </div>

          {user?.usuAdmin && (
            <NavLink to="/usuarios" className={({ isActive }) => `sidebar-link${isActive ? " active" : ""}`}>
              <span className="sidebar-link-main">
                <SidebarIcon kind="usuarios" />
                <span>Usuários</span>
              </span>
            </NavLink>
          )}
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
          <div className="top-breadcrumb" aria-label="Breadcrumb">
            {headerData.breadcrumb.map((item, idx) => (
              <React.Fragment key={item}>
                {idx > 0 && <span className="top-breadcrumb-sep"> &gt; </span>}
                <span>{item}</span>
              </React.Fragment>
            ))}
          </div>
          <h1>{headerData.title}</h1>
          <p>{headerData.description}</p>
        </header>
        <main className="app-main">{children}</main>
      </div>
    </div>
  );
};

export default Layout;

