import React, { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import Layout from "../../components/Layout";
import { DataTable } from "../../components/DataTable";
import Loader from "../../components/Loader";
import Modal from "../../components/Modal";
import ConfirmDialog from "../../components/ConfirmDialog";
import ActionIconButton from "../../components/ActionIconButton";
import ListingToolbar from "../../components/ListingToolbar";
import ListingTableCard from "../../components/ListingTableCard";
import PaginationBar from "../../components/PaginationBar";
import OptionalTextareaField from "../../components/OptionalTextareaField";
import UserAvatar from "../../components/UserAvatar";
import { useAuth } from "../../contexts/AuthContext";
import { getOportunidadePipelineContext } from "../../utils/oportunidadePipeline";

interface OportunidadeItem {
  opoId: number;
  opoTitulo: string;
  opoNomeContato: string | null;
  opoEmpresaContato: string | null;
  opoEmail: string | null;
  opoTelefone: string | null;
  opoSolucao: string | null;
  opoProId: number | null;
  opoEtkId: number | null;
  opoUsuResponsavelId: number | null;
  opoCcoId: number | null;
  opoLeadScore: number | null;
  opoTemperatura: string | null;
  opoStatusFechamento: string | null;
  opoReuniaoConfirmada: boolean;
  opoPropostaEnviada: boolean;
  opoDataRecebimento: string | null;
  opoDataUltimoContato: string | null;
  opoValorOportunidade: number | null;
  opoValorFechado: number | null;
  opoDoresMotivadores: string | null;
  opoComentarios: string | null;
  opoAtivo: boolean;
}

interface ListResponse {
  items: OportunidadeItem[];
  total: number;
  page: number;
  page_size: number;
}

interface EtapaItem {
  etkId: number;
  etkNome: string;
}
interface ProdutoItem {
  proId: number;
  proNome: string;
}
interface UsuarioItem {
  usuId: number;
  usuNome: string;
  usuAvatarUrl?: string | null;
}
interface ComoConheceuItem {
  ccoId: number;
  ccoNome: string;
}

type AbaStatus = "ativo" | "ganho" | "perdido" | "stand-by";

const ABA_CONFIG: { value: AbaStatus; label: string; tabClass: string }[] = [
  { value: "ativo", label: "Ativo", tabClass: "tab--ativo" },
  { value: "ganho", label: "Ganho", tabClass: "tab--ganho" },
  { value: "perdido", label: "Perdido", tabClass: "tab--perdido" },
  { value: "stand-by", label: "Stand-by", tabClass: "tab--standby" },
];

const OportunidadesPage: React.FC = () => {
  const { api, user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const pipelineContext = useMemo(() => getOportunidadePipelineContext(location.pathname), [location.pathname]);
  const [items, setItems] = useState<OportunidadeItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(25);
  const [total, setTotal] = useState(0);
  const [tabCounts, setTabCounts] = useState<Record<string, number>>({});
  const [responsavelFiltroDraft, setResponsavelFiltroDraft] = useState<number | null>(null);
  const [solucaoFiltroDraft, setSolucaoFiltroDraft] = useState<number | null>(null);
  const [dataUltimoContatoInicioDraft, setDataUltimoContatoInicioDraft] = useState("");
  const [dataUltimoContatoFimDraft, setDataUltimoContatoFimDraft] = useState("");
  const [responsavelFiltro, setResponsavelFiltro] = useState<number | null>(null);
  const [solucaoFiltro, setSolucaoFiltro] = useState<number | null>(null);
  const [dataUltimoContatoInicio, setDataUltimoContatoInicio] = useState("");
  const [dataUltimoContatoFim, setDataUltimoContatoFim] = useState("");
  const [abaStatus, setAbaStatus] = useState<AbaStatus>("ativo");
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [etapas, setEtapas] = useState<EtapaItem[]>([]);
  const [produtos, setProdutos] = useState<ProdutoItem[]>([]);
  const [usuarios, setUsuarios] = useState<UsuarioItem[]>([]);
  const [comoConheceu, setComoConheceu] = useState<ComoConheceuItem[]>([]);
  const [selected, setSelected] = useState<OportunidadeItem | null>(null);
  const [selectedRetorno, setSelectedRetorno] = useState<OportunidadeItem | null>(null);
  const [isRetornoDialogOpen, setIsRetornoDialogOpen] = useState(false);
  const [showDores, setShowDores] = useState(false);
  const [showComentarios, setShowComentarios] = useState(false);
  const [search, setSearch] = useState("");
  const [form, setForm] = useState({
    opoTitulo: "",
    opoNomeContato: "",
    opoTelefone: "",
    opoSolucao: "",
    opoProId: null as number | null,
    opoEtkId: null as number | null,
    opoUsuResponsavelId: null as number | null,
    opoCcoId: null as number | null,
    opoDataRecebimento: "",
    opoValorOportunidade: null as number | null,
    opoDoresMotivadores: "",
    opoComentarios: "",
  });

  const getTodayDateInput = () => {
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, "0");
    const day = String(now.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
  };

  const loadOportunidades = async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { page, page_size: pageSize, status: "ativos", pipeline: pipelineContext.pipeline };
      params.status_fechamento = abaStatus;
      if (responsavelFiltro !== null) params.responsavel_id = responsavelFiltro;
      if (solucaoFiltro !== null) params.pro_id = solucaoFiltro;
      if (dataUltimoContatoInicio) params.data_ultimo_contato_inicio = dataUltimoContatoInicio;
      if (dataUltimoContatoFim) params.data_ultimo_contato_fim = dataUltimoContatoFim;
      const res = await api.get<ListResponse>("/oportunidades", { params });
      setItems(res.data.items);
      setTotal(res.data.total);
    } finally {
      setLoading(false);
    }
  };

  const loadTabCounts = async () => {
    try {
      const statuses: AbaStatus[] = ["ativo", "ganho", "perdido", "stand-by"];
      const results = await Promise.all(
        statuses.map((s) =>
          api.get<ListResponse>("/oportunidades", {
            params: { status: "ativos", status_fechamento: s, page_size: 1, page: 1, pipeline: pipelineContext.pipeline },
          })
        )
      );
      const counts: Record<string, number> = {};
      statuses.forEach((s, i) => {
        counts[s] = results[i].data.total ?? 0;
      });
      setTabCounts(counts);
    } catch {
      // counts são opcionais
    }
  };

  const loadCombos = async () => {
    try {
      const [etapasRes, produtosRes, usuariosRes, ccoRes] = await Promise.all([
        api.get<{ items: EtapaItem[] }>("/etapas-kanban", {
          params: { page_size: 100, status: "ativos", pipeline: pipelineContext.pipeline },
        }),
        api.get<{ items: ProdutoItem[] }>("/produtos", { params: { page_size: 100, status: "ativos" } }),
        api.get<{ items: Array<{ usuId: number; usuNome: string; usuAvatarUrl?: string | null }> }>("/usuarios", {
          params: { page_size: 100, status: "ativos" },
        }),
        api.get<{ items: ComoConheceuItem[] }>("/como-conheceu", { params: { page_size: 100, status: "ativos" } }),
      ]);
      setEtapas(etapasRes.data.items);
      setProdutos(produtosRes.data.items);
      setUsuarios(
        (usuariosRes.data.items ?? []).map((u) => ({
          usuId: u.usuId,
          usuNome: u.usuNome,
          usuAvatarUrl: u.usuAvatarUrl ?? null,
        })),
      );
      setComoConheceu(ccoRes.data.items);
    } catch {
      // combos opcionais
    }
  };

  useEffect(() => {
    void loadCombos();
    void loadTabCounts();
  }, [pipelineContext.pipeline]);

  useEffect(() => {
    void loadOportunidades();
  }, [page, responsavelFiltro, solucaoFiltro, dataUltimoContatoInicio, dataUltimoContatoFim, abaStatus, pipelineContext.pipeline]);

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    if (params.get("nova") !== "1") return;
    openCreate();
    navigate(pipelineContext.newFromQueryPath, { replace: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.search, navigate, pipelineContext.newFromQueryPath]);

  const openCreate = () => {
    setSelected(null);
    setForm({
      opoTitulo: "",
      opoNomeContato: "",
      opoTelefone: "",
      opoSolucao: "",
      opoProId: null,
      opoEtkId: etapas[0]?.etkId ?? null,
      opoUsuResponsavelId: user?.usuId ?? null,
      opoCcoId: null,
      opoDataRecebimento: getTodayDateInput(),
      opoValorOportunidade: null,
      opoDoresMotivadores: "",
      opoComentarios: "",
    });
    setShowDores(false);
    setShowComentarios(false);
    setIsModalOpen(true);
  };

  const openEdit = (row: OportunidadeItem) => {
    setSelected(row);
    setForm({
      opoTitulo: row.opoTitulo,
      opoNomeContato: row.opoNomeContato ?? "",
      opoTelefone: row.opoTelefone ?? "",
      opoSolucao: row.opoSolucao ?? "",
      opoProId: row.opoProId,
      opoEtkId: row.opoEtkId,
      opoUsuResponsavelId: row.opoUsuResponsavelId,
      opoCcoId: row.opoCcoId,
      opoDataRecebimento: row.opoDataRecebimento ?? "",
      opoValorOportunidade: row.opoValorOportunidade,
      opoDoresMotivadores: row.opoDoresMotivadores ?? "",
      opoComentarios: row.opoComentarios ?? "",
    });
    setShowDores(Boolean(row.opoDoresMotivadores));
    setShowComentarios(Boolean(row.opoComentarios));
    setIsModalOpen(true);
  };

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    const payload = {
      ...form,
      opoProId: form.opoProId ?? null,
      opoEtkId: form.opoEtkId ?? null,
      opoUsuResponsavelId: form.opoUsuResponsavelId ?? null,
      opoCcoId: form.opoCcoId ?? null,
      opoDataRecebimento: form.opoDataRecebimento || null,
      opoValorOportunidade: form.opoValorOportunidade ?? null,
      opoDoresMotivadores: showDores ? form.opoDoresMotivadores : "",
      opoComentarios: showComentarios ? form.opoComentarios : "",
    };
    if (selected) {
      await api.put(`/oportunidades/${selected.opoId}`, payload);
    } else {
      await api.post("/oportunidades", payload);
    }
    setIsModalOpen(false);
    await loadOportunidades();
    void loadTabCounts();
  };

  const abrirRetornoParaAtivo = (row: OportunidadeItem) => {
    setSelectedRetorno(row);
    setIsRetornoDialogOpen(true);
  };

  const confirmarRetornoParaAtivo = async () => {
    if (!selectedRetorno) return;
    await api.patch(`/oportunidades/${selectedRetorno.opoId}/retornar-ativo`);
    setIsRetornoDialogOpen(false);
    setSelectedRetorno(null);
    await loadOportunidades();
    void loadTabCounts();
  };

  const etapaNome = (etkId: number | null) => etapas.find((e) => e.etkId === etkId)?.etkNome ?? "-";
  const produtoNome = (proId: number | null, fallback: string | null) =>
    produtos.find((p) => p.proId === proId)?.proNome ?? fallback ?? "-";
  const usuarioNome = (usuId: number | null) => usuarios.find((u) => u.usuId === usuId)?.usuNome ?? "-";

  const formatDateTime = (value: string | null) => {
    if (!value) return "-";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "-";
    return date.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric" });
  };

  const getAgingClass = (dateStr: string | null): string => {
    if (!dateStr) return "";
    const date = new Date(dateStr);
    if (Number.isNaN(date.getTime())) return "";
    const daysSince = Math.floor((Date.now() - date.getTime()) / (1000 * 60 * 60 * 24));
    if (daysSince > 30) return "date-aging--danger";
    if (daysSince > 15) return "date-aging--warning";
    return "";
  };

  const temperaturaLabel = (value: string | null) => {
    if (!value) return "-";
    const normalized = value.trim().toLowerCase();
    if (normalized === "frio") return "Frio";
    if (normalized === "morno") return "Morno";
    if (normalized === "quente") return "Quente";
    return value;
  };

  const temperaturaClass = (value: string | null) => {
    const normalized = (value ?? "").trim().toLowerCase();
    if (normalized === "frio") return "oportunidade-label oportunidade-label--frio";
    if (normalized === "morno") return "oportunidade-label oportunidade-label--morno";
    if (normalized === "quente") return "oportunidade-label oportunidade-label--quente";
    return "oportunidade-label oportunidade-label--default";
  };

  const renderTempIcon = (temperatura: string | null) => {
    const t = (temperatura ?? "").trim().toLowerCase();
    if (t === "frio") {
      return (
        <svg viewBox="0 0 24 24" aria-hidden>
          <path d="M12 2v20M2 12h20M4.93 4.93l14.14 14.14M19.07 4.93L4.93 19.07" />
        </svg>
      );
    }
    if (t === "quente") {
      return (
        <svg viewBox="0 0 24 24" aria-hidden>
          <path d="M12 22c2.5 0 4-2 4-4 0-3-2.5-4.5-2.5-8C13 8 14 6 14 4c-1 1-2 3-2 5 0-2-1.5-3.5-1.5-5C9 6 8 8 8 10c0 2 2 3 2 5 0 1-.5 2-1 2.5.5-1 .5-2.5-.5-3.5C7.5 16 8 18 8 18c0 2 1.5 4 4 4z" />
        </svg>
      );
    }
    return (
      <svg viewBox="0 0 24 24" aria-hidden>
        <path d="M14 14.76V5a2 2 0 10-4 0v9.76a4 4 0 104 0z" />
      </svg>
    );
  };

  const filteredItems = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!term) return items;
    return items.filter((r) => {
      const cliente = (r.opoEmpresaContato ?? r.opoTitulo ?? "").toLowerCase();
      const contato = (r.opoNomeContato ?? "").toLowerCase();
      const responsavel = usuarioNome(r.opoUsuResponsavelId).toLowerCase();
      return cliente.includes(term) || contato.includes(term) || responsavel.includes(term);
    });
  }, [items, search, usuarios]);

  const columns = useMemo(() => {
    const baseCols = [
      {
        key: "opoEmpresaContato",
        header: "Cliente",
        render: (r: OportunidadeItem) => r.opoEmpresaContato ?? r.opoTitulo,
      },
      {
        key: "opoNomeContato",
        header: "Contato",
        render: (r: OportunidadeItem) => r.opoNomeContato ?? "-",
      },
      {
        key: "opoTemperatura",
        header: "Temp.",
        render: (r: OportunidadeItem) => (
          <span className={temperaturaClass(r.opoTemperatura)} aria-label={temperaturaLabel(r.opoTemperatura)}>
            {renderTempIcon(r.opoTemperatura)}
          </span>
        ),
      },
      {
        key: "opoProId",
        header: "Solução",
        render: (r: OportunidadeItem) => produtoNome(r.opoProId, r.opoSolucao),
      },
    ];

    const responsavelCol = {
      key: "opoUsuResponsavelId",
      header: "Responsável",
      render: (r: OportunidadeItem) => {
        const usuario = usuarios.find((u) => u.usuId === r.opoUsuResponsavelId);
        if (!usuario) return "-";
        return (
          <span className="oportunidades-responsavel-cell">
            <UserAvatar name={usuario.usuNome} avatarUrl={usuario.usuAvatarUrl ?? null} size="sm" />
            <span className="oportunidades-responsavel-nome">{usuario.usuNome}</span>
          </span>
        );
      },
    };

    const ultimoContatoCol = {
      key: "opoDataUltimoContato",
      header: "Último contato",
      render: (r: OportunidadeItem) => (
        <span className={abaStatus === "ativo" ? getAgingClass(r.opoDataUltimoContato) : ""}>
          {formatDateTime(r.opoDataUltimoContato)}
        </span>
      ),
    };

    const açõesCol = {
      key: "opoId",
      header: "Ações",
      render: (r: OportunidadeItem) => (
        <div className="actions">
          <ActionIconButton icon="view" label="Visualizar" onClick={() => navigate(pipelineContext.detailPath(r.opoId))} />
          <ActionIconButton icon="edit" label="Editar" onClick={() => openEdit(r)} />
          {(r.opoStatusFechamento === "perdido" || r.opoStatusFechamento === "stand-by") && (
            <ActionIconButton
              icon="activate"
              label="Retornar para ativo"
              tone="success"
              onClick={() => abrirRetornoParaAtivo(r)}
            />
          )}
        </div>
      ),
    };

    if (abaStatus === "ganho") {
      return [
        ...baseCols,
        {
          key: "opoValorFechado",
          header: "Valor fechado",
          render: (r: OportunidadeItem) =>
            r.opoValorFechado != null
              ? r.opoValorFechado.toLocaleString("pt-BR", { style: "currency", currency: "BRL", minimumFractionDigits: 2 })
              : "-",
        },
        responsavelCol,
        ultimoContatoCol,
        açõesCol,
      ];
    }

    if (abaStatus === "stand-by") {
      return [
        ...baseCols,
        {
          key: "opoDataUltimoContato",
          header: "Data retorno",
          render: (r: OportunidadeItem) => formatDateTime(r.opoDataUltimoContato),
        },
        responsavelCol,
        ultimoContatoCol,
        açõesCol,
      ];
    }

    if (abaStatus === "ativo") {
      return [
        ...baseCols,
        {
          key: "opoEtkId",
          header: "Etapa",
          render: (r: OportunidadeItem) => <span className="status-badge status-badge--open">{etapaNome(r.opoEtkId)}</span>,
        },
        {
          key: "opoValorOportunidade",
          header: "Valor",
          render: (r: OportunidadeItem) =>
            r.opoValorOportunidade != null
              ? r.opoValorOportunidade.toLocaleString("pt-BR", { style: "currency", currency: "BRL", minimumFractionDigits: 0, maximumFractionDigits: 0 })
              : "-",
        },
        responsavelCol,
        ultimoContatoCol,
        açõesCol,
      ];
    }

    // perdido
    return [
      ...baseCols,
      {
        key: "opoEtkId",
        header: "Etapa",
        render: (r: OportunidadeItem) => <span className="status-badge status-badge--open">{etapaNome(r.opoEtkId)}</span>,
      },
      responsavelCol,
      ultimoContatoCol,
      açõesCol,
    ];
  }, [abaStatus, abrirRetornoParaAtivo, navigate, usuarios, produtos, etapas, search, items, pipelineContext]);

  const aplicarFiltros = () => {
    setPage(1);
    setResponsavelFiltro(responsavelFiltroDraft);
    setSolucaoFiltro(solucaoFiltroDraft);
    setDataUltimoContatoInicio(dataUltimoContatoInicioDraft);
    setDataUltimoContatoFim(dataUltimoContatoFimDraft);
  };

  const limparFiltros = () => {
    setPage(1);
    setResponsavelFiltroDraft(null);
    setSolucaoFiltroDraft(null);
    setDataUltimoContatoInicioDraft("");
    setDataUltimoContatoFimDraft("");
    setResponsavelFiltro(null);
    setSolucaoFiltro(null);
    setDataUltimoContatoInicio("");
    setDataUltimoContatoFim("");
  };

  return (
    <Layout>
      <ListingToolbar
        actions={
          <button type="button" className="btn-primary" onClick={openCreate}>
            Nova oportunidade
          </button>
        }
        filters={
          <div className="oportunidades-filtros">
            <div className="search-field-wrapper">
              <svg className="search-field-icon" viewBox="0 0 24 24" aria-hidden>
                <path d="M21 21l-4.35-4.35M17 11A6 6 0 115 11a6 6 0 0112 0z" />
              </svg>
              <input
                type="text"
                placeholder="Buscar por cliente, contato ou responsável"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            <select
              value={responsavelFiltroDraft ?? ""}
              onChange={(e) => setResponsavelFiltroDraft(e.target.value ? Number(e.target.value) : null)}
            >
              <option value="">Responsável</option>
              {usuarios.map((u) => (
                <option key={u.usuId} value={u.usuId}>
                  {u.usuNome}
                </option>
              ))}
            </select>
            <select
              value={solucaoFiltroDraft ?? ""}
              onChange={(e) => setSolucaoFiltroDraft(e.target.value ? Number(e.target.value) : null)}
            >
              <option value="">Solução</option>
              {produtos.map((p) => (
                <option key={p.proId} value={p.proId}>
                  {p.proNome}
                </option>
              ))}
            </select>
            <div className="filter-group">
              <span className="filter-group-label">Último contato</span>
              <div className="filter-group-inputs">
                <input
                  type="date"
                  aria-label="Data de último contato inicial"
                  value={dataUltimoContatoInicioDraft}
                  onChange={(e) => setDataUltimoContatoInicioDraft(e.target.value)}
                />
                <span className="oportunidades-filtros-separador">até</span>
                <input
                  type="date"
                  aria-label="Data de último contato final"
                  value={dataUltimoContatoFimDraft}
                  onChange={(e) => setDataUltimoContatoFimDraft(e.target.value)}
                />
              </div>
            </div>
            <button type="button" className="btn-primary" onClick={aplicarFiltros}>
              Filtrar
            </button>
            <button type="button" onClick={limparFiltros}>
              Limpar
            </button>
          </div>
        }
      />

      <div className="oportunidades-status-tabs" role="tablist" aria-label="Status do fechamento">
        {ABA_CONFIG.map(({ value, label, tabClass }) => (
          <button
            key={value}
            type="button"
            role="tab"
            aria-selected={abaStatus === value}
            className={`oportunidades-status-tab ${tabClass}${abaStatus === value ? " is-active" : ""}`}
            onClick={() => {
              setPage(1);
              setAbaStatus(value);
            }}
          >
            {label}
            {tabCounts[value] !== undefined && (
              <span className="tab-count">{tabCounts[value]}</span>
            )}
          </button>
        ))}
      </div>

      {loading ? (
        <Loader />
      ) : (
        <ListingTableCard
          footer={<PaginationBar page={page} pageSize={pageSize} total={total} onPageChange={(next) => setPage(next)} />}
        >
          <DataTable keyField="opoId" data={filteredItems} columns={columns} />
        </ListingTableCard>
      )}

      <Modal
        isOpen={isModalOpen}
        title={selected ? "Editar oportunidade" : "Nova oportunidade"}
        onClose={() => {
          setIsModalOpen(false);
          setShowDores(false);
          setShowComentarios(false);
        }}
      >
        <form className="form-vertical form-scroll form-opportunity" onSubmit={save}>
          <section className="form-section">
            <h3 className="form-section-title">INFORMAÇÕES PRINCIPAIS</h3>
            <div className="form-grid">
              <label className="form-field form-field--full">
                <span className="form-label">
                  Oportunidade <span className="form-required">*</span>
                </span>
                <input
                  value={form.opoTitulo}
                  onChange={(e) => setForm((f) => ({ ...f, opoTitulo: e.target.value }))}
                  required
                  placeholder="Digite o nome da oportunidade"
                />
              </label>
              <label className="form-field">
                <span className="form-label">Nome contato</span>
                <input
                  value={form.opoNomeContato}
                  onChange={(e) => setForm((f) => ({ ...f, opoNomeContato: e.target.value }))}
                  placeholder="Nome do contato"
                />
              </label>
              <label className="form-field">
                <span className="form-label">Telefone</span>
                <input
                  value={form.opoTelefone}
                  onChange={(e) => setForm((f) => ({ ...f, opoTelefone: e.target.value }))}
                  placeholder="(00) 00000-0000"
                />
              </label>
            </div>
          </section>

          <section className="form-section">
            <h3 className="form-section-title">DETALHES DA OPORTUNIDADE</h3>
            <div className="form-grid">
              <label className="form-field">
                <span className="form-label">Solução / Produto</span>
                <select
                  value={form.opoProId ?? ""}
                  onChange={(e) => setForm((f) => ({ ...f, opoProId: e.target.value ? Number(e.target.value) : null }))}
                >
                  <option value="">Selecione um produto</option>
                  {produtos.map((p) => (
                    <option key={p.proId} value={p.proId}>
                      {p.proNome}
                    </option>
                  ))}
                </select>
              </label>
              <label className="form-field">
                <span className="form-label">Etapa</span>
                <select
                  value={form.opoEtkId ?? ""}
                  onChange={(e) => setForm((f) => ({ ...f, opoEtkId: e.target.value ? Number(e.target.value) : null }))}
                >
                  <option value="">Selecione uma etapa</option>
                  {etapas.map((e) => (
                    <option key={e.etkId} value={e.etkId}>
                      {e.etkNome}
                    </option>
                  ))}
                </select>
              </label>
              <label className="form-field">
                <span className="form-label">Responsável</span>
                <select
                  value={form.opoUsuResponsavelId ?? ""}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, opoUsuResponsavelId: e.target.value ? Number(e.target.value) : null }))
                  }
                >
                  <option value="">Selecione um responsável</option>
                  {usuarios.map((u) => (
                    <option key={u.usuId} value={u.usuId}>
                      {u.usuNome}
                    </option>
                  ))}
                </select>
              </label>
              <label className="form-field">
                <span className="form-label">Como conheceu</span>
                <select
                  value={form.opoCcoId ?? ""}
                  onChange={(e) => setForm((f) => ({ ...f, opoCcoId: e.target.value ? Number(e.target.value) : null }))}
                >
                  <option value="">Selecione uma origem</option>
                  {comoConheceu.map((c) => (
                    <option key={c.ccoId} value={c.ccoId}>
                      {c.ccoNome}
                    </option>
                  ))}
                </select>
              </label>
              <label className="form-field">
                <span className="form-label">Valor oportunidade</span>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  value={form.opoValorOportunidade ?? ""}
                  onChange={(e) =>
                    setForm((f) => ({
                      ...f,
                      opoValorOportunidade: e.target.value ? Number(e.target.value) : null,
                    }))
                  }
                  placeholder="0,00"
                />
              </label>
              <label className="form-field">
                <span className="form-label">Data de recebimento</span>
                <input
                  type="date"
                  value={form.opoDataRecebimento}
                  onChange={(e) => setForm((f) => ({ ...f, opoDataRecebimento: e.target.value }))}
                />
              </label>
            </div>
          </section>

          <section className="form-section">
            <h3 className="form-section-title">INFORMAÇÕES COMPLEMENTARES</h3>
            <div className="form-grid">
              <div className="form-field form-field--full">
                <OptionalTextareaField
                  isOpen={showDores}
                  onToggle={() => setShowDores((v) => !v)}
                  buttonLabel="+ Adicionar dores / motivadores"
                  label="Dores / Motivadores"
                  value={form.opoDoresMotivadores}
                  onChange={(next) => setForm((f) => ({ ...f, opoDoresMotivadores: next }))}
                  placeholder="Descreva as dores e motivadores do cliente"
                />
              </div>
              <div className="form-field form-field--full">
                <OptionalTextareaField
                  isOpen={showComentarios}
                  onToggle={() => setShowComentarios((v) => !v)}
                  buttonLabel="+ Adicionar comentários"
                  label="Comentários"
                  value={form.opoComentarios}
                  onChange={(next) => setForm((f) => ({ ...f, opoComentarios: next }))}
                  placeholder="Adicione observações importantes"
                />
              </div>
            </div>
          </section>
          <div className="modal-actions">
            <button type="button" onClick={() => setIsModalOpen(false)}>
              Cancelar
            </button>
            <button type="submit">Salvar oportunidade</button>
          </div>
        </form>
      </Modal>

      <ConfirmDialog
        isOpen={isRetornoDialogOpen}
        title="Retornar para ativo"
        message={`Deseja retornar a oportunidade "${selectedRetorno?.opoTitulo ?? ""}" para ativo?`}
        onCancel={() => {
          setIsRetornoDialogOpen(false);
          setSelectedRetorno(null);
        }}
        onConfirm={confirmarRetornoParaAtivo}
      />
    </Layout>
  );
};

export default OportunidadesPage;
