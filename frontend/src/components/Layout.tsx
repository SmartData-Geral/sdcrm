import React, { useCallback, useEffect, useState } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";

const HamburgerIcon = () => (
  <svg viewBox="0 0 24 24" aria-hidden>
    <path d="M3 12h18M3 6h18M3 18h18" />
  </svg>
);

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

const SidebarIcon: React.FC<{ kind: "dashboard" | "crm" | "cadastros" | "usuarios" | "integracoes" }> = ({ kind }) => {
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
    integracoes: (
      <path d="M10 13a5 5 0 007 0l3-3a5 5 0 00-7-7l-1 1M14 11a5 5 0 00-7 0l-3 3a5 5 0 007 7l1-1" />
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
  return { crm: false, upsell: false, cadastros: false };
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
      breadcrumb: ["Dashboard", "CRM"],
      title: "Dashboard CRM",
      description: "Indicadores e funil de oportunidades do CRM.",
    };
  }
  if (pathname.startsWith("/oportunidades-kanban")) {
    return {
      breadcrumb: ["Dashboard", "CRM", "Kanban"],
      title: "Kanban de Oportunidades",
      description: "Acompanhe o pipeline de oportunidades por etapa.",
    };
  }
  if (pathname.startsWith("/upsell/oportunidades-kanban")) {
    return {
      breadcrumb: ["Dashboard", "Upsell", "Kanban"],
      title: "Kanban de Upsell",
      description: "Acompanhe o pipeline de upsell por etapa.",
    };
  }
  if (pathname.startsWith("/upsell/oportunidades/") && pathname.includes("/contrato/novo")) {
    return {
      breadcrumb: ["Dashboard", "Upsell", "Oportunidades", "Contrato"],
      title: "Novo contrato",
      description: "Crie um contrato vinculado a uma oportunidade de upsell.",
    };
  }
  if (pathname.startsWith("/upsell/oportunidades/")) {
    return {
      breadcrumb: ["Dashboard", "Upsell", "Oportunidades"],
      title: "Detalhe da Oportunidade",
      description: "Visualize informações completas e histórico da oportunidade de upsell.",
    };
  }
  if (pathname.startsWith("/upsell/oportunidades")) {
    return {
      breadcrumb: ["Dashboard", "Upsell", "Oportunidades"],
      title: "Upsell",
      description: "Gerencie oportunidades do funil de upsell.",
    };
  }
  if (pathname.startsWith("/oportunidades/")) {
    return {
      breadcrumb: ["Dashboard", "CRM", "Oportunidades"],
      title: "Detalhe da Oportunidade",
      description: "Visualize informações completas e histórico da oportunidade.",
    };
  }
  if (pathname.startsWith("/propostas/")) {
    return {
      breadcrumb: ["Dashboard", "CRM", "Propostas"],
      title: "Editor de Propostas",
      description: "Edite conteúdo, publique e acompanhe eventos da proposta.",
    };
  }
  if (pathname.startsWith("/cadastros/propostas")) {
    return {
      breadcrumb: ["Dashboard", "Cadastros", "Propostas"],
      title: "Cadastros de Propostas",
      description: "Gerencie templates e itens base para propostas comerciais.",
    };
  }
  if (pathname.startsWith("/cadastros/agentes-ia")) {
    return {
      breadcrumb: ["Dashboard", "Cadastros", "Agentes"],
      title: "Agentes de IA",
      description: "Configure prompts de sistema, provider e modelo LLM por fluxo.",
    };
  }
  if (pathname.startsWith("/cadastros/contratos")) {
    return {
      breadcrumb: ["Dashboard", "Cadastros", "Contratos"],
      title: "Cadastros de Contratos",
      description: "Gerencie modelos base, cláusulas e variações para geração de contratos.",
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
  if (pathname.startsWith("/contratos/novo")) {
    return {
      breadcrumb: ["Dashboard", "CRM", "Contratos"],
      title: "Novo contrato (avulso)",
      description: "Crie um contrato avulso a partir de um modelo base.",
    };
  }
  if (pathname.startsWith("/contratos/")) {
    return {
      breadcrumb: ["Dashboard", "CRM", "Contratos"],
      title: "Contrato",
      description: "Edite o contrato e prepare o preview.",
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
  if (pathname.startsWith("/cadastros/metas-mensais")) {
    return {
      breadcrumb: ["Dashboard", "Cadastros", "Metas mensais"],
      title: "Metas mensais",
      description: "Cadastre e visualize metas de recebimento, conversão e MRR por mês.",
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
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
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
    setMobileSidebarOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    document.body.style.overflow = mobileSidebarOpen ? "hidden" : "";
    return () => { document.body.style.overflow = ""; };
  }, [mobileSidebarOpen]);

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
      if ((path.startsWith("/upsell/oportunidades") || path.startsWith("/upsell/oportunidades-kanban")) && !prev.upsell) {
        next = { ...next, upsell: true };
        setStoredOpen(next);
      }
      if (path.startsWith("/contratos") && !prev.crm) {
        next = { ...prev, crm: true };
        setStoredOpen(next);
      }
      if (
        (path.startsWith("/como-conheceu") ||
          path.startsWith("/motivos-cancelamento") ||
          path.startsWith("/produtos") ||
          path.startsWith("/etapas-kanban") ||
          path.startsWith("/cadastros/propostas") ||
          path.startsWith("/cadastros/metas-mensais") ||
          path.startsWith("/cadastros/agentes-ia") ||
          path.startsWith("/cadastros/contratos") ||
          path.startsWith("/empresas")) &&
        !prev.cadastros
      ) {
        next = { ...next, cadastros: true };
        setStoredOpen(next);
      }
      return next;
    });
  }, [location.pathname]);

  const handleCompanyChange = (value: string) => {
    const nextCompanyId = value ? Number(value) : null;
    if (nextCompanyId === companyId) return;
    setCompanyId(nextCompanyId);
    window.location.reload();
  };

  return (
    <div className={`app-layout${mobileSidebarOpen ? " sidebar-open" : ""}`}>
      {mobileSidebarOpen && (
        <div className="sidebar-overlay" onClick={() => setMobileSidebarOpen(false)} />
      )}
      <aside className="sidebar">
        <div className="brand-block">
          <span className="brand-logo" aria-hidden>
            <svg viewBox="0 0 24 24" fill="none">
              <rect x="3" y="3" width="8" height="8" rx="2" fill="#3b82f6" />
              <rect x="13" y="3" width="8" height="5" rx="2" fill="#60a5fa" />
              <rect x="13" y="10" width="8" height="11" rx="2" fill="#93c5fd" />
              <rect x="3" y="13" width="8" height="8" rx="2" fill="#bfdbfe" />
            </svg>
          </span>
          <strong className="brand-title">Smart CRM</strong>
        </div>
        {empresas.length > 0 && (
          <div className="sidebar-company">
            <label className="sidebar-company-label">Empresa</label>
            <select
              className="sidebar-company-select"
              value={companyId ?? ""}
              onChange={(e) => handleCompanyChange(e.target.value)}
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
                <NavLink to="/contratos/novo" className={({ isActive }) => `sidebar-link sidebar-link--nested${isActive ? " active" : ""}`}>
                  Contratos (avulso)
                </NavLink>
              </div>
            )}
          </div>

          <div className="sidebar-group">
            <button
              type="button"
              className={`sidebar-group-toggle ${openGroups.upsell ? " is-open" : ""}`}
              onClick={() => toggleGroup("upsell")}
              aria-expanded={openGroups.upsell}
            >
              <span className="sidebar-group-label">
                <SidebarIcon kind="crm" />
                <span>Upsell</span>
              </span>
              <span className="sidebar-group-icon" aria-hidden>▼</span>
            </button>
            {openGroups.upsell && (
              <div className="sidebar-group-items">
                <NavLink to="/upsell/oportunidades" className={({ isActive }) => `sidebar-link sidebar-link--nested${isActive ? " active" : ""}`}>
                  Oportunidades
                </NavLink>
                <NavLink to="/upsell/oportunidades-kanban" className={({ isActive }) => `sidebar-link sidebar-link--nested${isActive ? " active" : ""}`}>
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
                <NavLink to="/cadastros/metas-mensais" className={({ isActive }) => `sidebar-link sidebar-link--nested${isActive ? " active" : ""}`}>
                  Metas mensais
                </NavLink>
                <NavLink to="/cadastros/propostas" className={({ isActive }) => `sidebar-link sidebar-link--nested${isActive ? " active" : ""}`}>
                  Propostas
                </NavLink>
                <NavLink to="/cadastros/contratos" className={({ isActive }) => `sidebar-link sidebar-link--nested${isActive ? " active" : ""}`}>
                  Contratos
                </NavLink>
                <NavLink to="/cadastros/agentes-ia" className={({ isActive }) => `sidebar-link sidebar-link--nested${isActive ? " active" : ""}`}>
                  Agentes
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
            <div className="sidebar-group">
              <button
                type="button"
                className={`sidebar-group-toggle ${openGroups.integracoes ? " is-open" : ""}`}
                onClick={() => toggleGroup("integracoes")}
                aria-expanded={openGroups.integracoes}
              >
                <span className="sidebar-group-label">
                  <SidebarIcon kind="integracoes" />
                  <span>Integrações</span>
                </span>
                <span className="sidebar-group-icon" aria-hidden>▼</span>
              </button>
              {openGroups.integracoes && (
                <div className="sidebar-group-items">
                  <NavLink to="/integracoes/chaves" className={({ isActive }) => `sidebar-link sidebar-link--nested${isActive ? " active" : ""}`}>
                    Chaves de API
                  </NavLink>
                  <NavLink to="/integracoes/webhooks" className={({ isActive }) => `sidebar-link sidebar-link--nested${isActive ? " active" : ""}`}>
                    Webhooks
                  </NavLink>
                  <NavLink to="/integracoes/logs" className={({ isActive }) => `sidebar-link sidebar-link--nested${isActive ? " active" : ""}`}>
                    Log de integração
                  </NavLink>
                </div>
              )}
            </div>
          )}

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
          <div className="sidebar-footer-info">
            <span className="user-name">{user?.usuNome}</span>
            <span className="user-role">{user?.usuAdmin ? "Administrador" : "Usuário"}</span>
          </div>
          <button type="button" className="sidebar-footer-btn" onClick={logout} title="Sair">
            <svg viewBox="0 0 24 24" aria-hidden>
              <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4M16 17l5-5-5-5M21 12H9" />
            </svg>
          </button>
        </div>
      </aside>

      <div className="content-area">
        <header className="top-header">
          <button
            type="button"
            className="mobile-nav-toggle"
            onClick={() => setMobileSidebarOpen((v) => !v)}
            aria-label={mobileSidebarOpen ? "Fechar menu" : "Abrir menu"}
            aria-expanded={mobileSidebarOpen}
          >
            <HamburgerIcon />
          </button>
          <div className="top-header-inner">
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
          </div>
        </header>
        <main className="app-main">{children}</main>
      </div>
    </div>
  );
};

export default Layout;

