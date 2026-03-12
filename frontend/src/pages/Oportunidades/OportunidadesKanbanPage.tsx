import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import Layout from "../../components/Layout";
import Loader from "../../components/Loader";
import Modal from "../../components/Modal";
import OptionalTextareaField from "../../components/OptionalTextareaField";
import ListingToolbar from "../../components/ListingToolbar";
import AvatarSelect from "../../components/AvatarSelect";
import UserAvatar from "../../components/UserAvatar";
import { useAuth } from "../../contexts/AuthContext";

interface OportunidadeItem {
  opoId: number;
  opoTitulo: string;
  opoNomeContato: string | null;
  opoTelefone: string | null;
  opoEmpresaContato: string | null;
  opoProId: number | null;
  opoUsuResponsavelId: number | null;
  opoTemperatura: string | null;
  opoLeadScore: number | null;
  opoDataRecebimento: string | null;
  opoDataUltimoContato: string | null;
  opoValorOportunidade: number | null;
  opoEtkId: number | null;
  opoStatusFechamento: string | null;
}

interface EtapaItem {
  etkId: number;
  etkNome: string;
  etkOrdem: number;
  etkCor: string | null;
}

interface UsuarioItem {
  usuId: number;
  usuNome: string;
  usuAvatarUrl?: string | null;
}

interface ProdutoItem {
  proId: number;
  proNome: string;
  proCor?: string | null;
}

interface OportunidadeListResponse {
  items: OportunidadeItem[];
  total: number;
  page: number;
  page_size: number;
}

interface ComoConheceuItem {
  ccoId: number;
  ccoNome: string;
}

const OportunidadesKanbanPage: React.FC = () => {
  const { api, user } = useAuth();
  const navigate = useNavigate();
  const [etapas, setEtapas] = useState<EtapaItem[]>([]);
  const [usuarios, setUsuarios] = useState<UsuarioItem[]>([]);
  const [produtos, setProdutos] = useState<ProdutoItem[]>([]);
  const [comoConheceu, setComoConheceu] = useState<ComoConheceuItem[]>([]);
  const [oportunidades, setOportunidades] = useState<OportunidadeItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [movingId, setMovingId] = useState<number | null>(null);
  const [draggingId, setDraggingId] = useState<number | null>(null);
  const [dragOverEtkId, setDragOverEtkId] = useState<number | null>(null);
  const [search, setSearch] = useState("");
  const [responsavelFiltro, setResponsavelFiltro] = useState<number | null>(null);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isSavingCreate, setIsSavingCreate] = useState(false);
  const [showDores, setShowDores] = useState(false);
  const [showComentarios, setShowComentarios] = useState(false);
  const [createForm, setCreateForm] = useState({
    opoTitulo: "",
    opoNomeContato: "",
    opoTelefone: "",
    opoProId: null as number | null,
    opoUsuResponsavelId: null as number | null,
    opoCcoId: null as number | null,
    opoDataRecebimento: "",
    opoEtkId: null as number | null,
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

  const loadAllOportunidades = useCallback(async (): Promise<OportunidadeItem[]> => {
    const pageSize = 100;
    let page = 1;
    let total = 0;
    const all: OportunidadeItem[] = [];

    do {
      const res = await api.get<OportunidadeListResponse>("/oportunidades", {
        params: { status: "ativos", page_size: pageSize, page },
      });
      const items = res.data.items ?? [];
      total = res.data.total ?? items.length;
      all.push(...items);
      page += 1;
      if (items.length === 0) break;
    } while (all.length < total);

    return all;
  }, [api]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [etapasRes, usuariosRes, produtosRes, ccoRes, opoItems] = await Promise.all([
        api.get<{ items: EtapaItem[] }>("/etapas-kanban", {
          params: { status: "ativos", page_size: 100 },
        }),
        api.get<{ items: UsuarioItem[] }>("/usuarios", {
          params: { status: "ativos", page_size: 100 },
        }),
        api.get<{ items: ProdutoItem[] }>("/produtos", {
          params: { status: "ativos", page_size: 100 },
        }),
        api.get<{ items: ComoConheceuItem[] }>("/como-conheceu", {
          params: { status: "ativos", page_size: 100 },
        }),
        loadAllOportunidades(),
      ]);
      const etList = (etapasRes.data.items ?? []).sort((a, b) => a.etkOrdem - b.etkOrdem);
      const usuList = (usuariosRes.data.items ?? []).sort((a, b) => a.usuNome.localeCompare(b.usuNome));
      const proList = (produtosRes.data.items ?? []).sort((a, b) => a.proNome.localeCompare(b.proNome));
      const ccoList = (ccoRes.data.items ?? []).sort((a, b) => a.ccoNome.localeCompare(b.ccoNome));
      setEtapas(etList);
      setUsuarios(usuList);
      setProdutos(proList);
      setComoConheceu(ccoList);
      setOportunidades(opoItems);
    } finally {
      setLoading(false);
    }
  }, [api, loadAllOportunidades]);

  useEffect(() => {
    void load();
  }, [load]);

  const moveToEtapa = async (opoId: number, opoEtkId: number) => {
    let rollback: OportunidadeItem[] = [];
    setMovingId(opoId);
    setOportunidades((prev) => {
      rollback = prev;
      return prev.map((item) => (item.opoId === opoId ? { ...item, opoEtkId } : item));
    });
    try {
      await api.patch(`/oportunidades/${opoId}/mover-etapa`, { opoEtkId });
    } catch (error) {
      setOportunidades(rollback);
      throw error;
    } finally {
      setMovingId(null);
      setDraggingId(null);
      setDragOverEtkId(null);
    }
  };

  const handleDropOnColumn = async (targetEtkId: number, rawId: string) => {
    const opoId = Number(rawId);
    if (!opoId) return;
    const current = oportunidades.find((o) => o.opoId === opoId);
    if (!current || current.opoEtkId === targetEtkId) {
      setDragOverEtkId(null);
      return;
    }
    await moveToEtapa(opoId, targetEtkId);
  };

  const fechada = (o: OportunidadeItem) =>
    o.opoStatusFechamento === "ganho" || o.opoStatusFechamento === "perdido" || o.opoStatusFechamento === "stand-by";

  const oportunidadesVisiveis = useMemo(() => {
    return oportunidades
      .filter((o) => !fechada(o))
      .filter((o) => {
        const termo = search.trim().toLowerCase();
        if (!termo) return true;
        const titulo = o.opoTitulo.toLowerCase();
        const contato = (o.opoNomeContato ?? "").toLowerCase();
        const empresa = (o.opoEmpresaContato ?? "").toLowerCase();
        return titulo.includes(termo) || contato.includes(termo) || empresa.includes(termo);
      })
      .filter((o) => (responsavelFiltro != null ? (o.opoUsuResponsavelId ?? null) === responsavelFiltro : true));
  }, [oportunidades, search, responsavelFiltro]);

  const byEtapa = (etkId: number | null) =>
    oportunidadesVisiveis.filter((o) => (o.opoEtkId ?? null) === etkId);

  const valorByEtapa = (etkId: number | null) =>
    byEtapa(etkId).reduce((acc, o) => acc + (o.opoValorOportunidade ?? 0), 0);

  const totalValor = useMemo(
    () => oportunidadesVisiveis.reduce((acc, o) => acc + (o.opoValorOportunidade ?? 0), 0),
    [oportunidadesVisiveis]
  );

  const draggingOportunidade = useMemo(
    () => oportunidades.find((o) => o.opoId === draggingId) ?? null,
    [oportunidades, draggingId]
  );

  const usuariosById = useMemo(() => {
    const map = new Map<number, UsuarioItem>();
    usuarios.forEach((u) => map.set(u.usuId, u));
    return map;
  }, [usuarios]);

  const produtosById = useMemo(() => {
    const map = new Map<number, ProdutoItem>();
    produtos.forEach((p) => map.set(p.proId, p));
    return map;
  }, [produtos]);

  const parseDate = (value: string | null) => {
    if (!value) return null;
    const onlyDateMatch = value.match(/^(\d{4})-(\d{2})-(\d{2})$/);
    if (onlyDateMatch) {
      const year = Number(onlyDateMatch[1]);
      const month = Number(onlyDateMatch[2]);
      const day = Number(onlyDateMatch[3]);
      const date = new Date(year, month - 1, day);
      if (Number.isNaN(date.getTime())) return null;
      return date;
    }
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return null;
    return date;
  };

  const formatDate = (date: Date | null) => {
    if (!date) return "-";
    return date.toLocaleDateString("pt-BR", {
      day: "2-digit",
      month: "2-digit",
      year: "2-digit",
    });
  };

  const getMaiorDataCard = (oportunidade: OportunidadeItem) => {
    const dataRecebimento = parseDate(oportunidade.opoDataRecebimento);
    const dataUltimoContato = parseDate(oportunidade.opoDataUltimoContato);
    if (!dataRecebimento) return dataUltimoContato;
    if (!dataUltimoContato) return dataRecebimento;
    return dataUltimoContato > dataRecebimento ? dataUltimoContato : dataRecebimento;
  };

  const getTemperaturaLabel = (temperatura: string | null) => {
    if (!temperatura) return "Sem temperatura";
    const value = temperatura.trim().toLowerCase();
    if (value === "frio") return "Frio";
    if (value === "morno") return "Morno";
    if (value === "quente") return "Quente";
    return temperatura;
  };

  const renderCard = (opo: OportunidadeItem) => {
    const responsavel = opo.opoUsuResponsavelId != null ? usuariosById.get(opo.opoUsuResponsavelId) : undefined;
    const produto = opo.opoProId != null ? produtosById.get(opo.opoProId) : undefined;
    const temperatura = opo.opoTemperatura?.trim().toLowerCase();

    return (
      <div
        key={opo.opoId}
        className={`kanban-card${movingId === opo.opoId ? " is-moving" : ""}`}
        draggable
        onDragStart={(e) => {
          setDraggingId(opo.opoId);
          e.dataTransfer.setData("text/plain", String(opo.opoId));
          e.dataTransfer.effectAllowed = "move";
          const source = e.currentTarget as HTMLDivElement;
          const ghost = source.cloneNode(true) as HTMLDivElement;
          ghost.classList.add("kanban-drag-ghost");
          ghost.style.width = `${source.offsetWidth}px`;
          document.body.appendChild(ghost);
          e.dataTransfer.setDragImage(ghost, 20, 20);
          window.setTimeout(() => ghost.remove(), 0);
        }}
        onDragEnd={() => {
          setDraggingId(null);
          setDragOverEtkId(null);
        }}
      >
        <div className="kanban-card-header">
          <button
            type="button"
            className="kanban-card-title"
            onClick={() => navigate(`/oportunidades/${opo.opoId}`)}
          >
            {opo.opoTitulo}
          </button>
          <div className="kanban-card-badges">
            {opo.opoLeadScore != null && <span className="kanban-card-lead">{opo.opoLeadScore}</span>}
            <span
              className={`kanban-card-temp-icon${temperatura ? ` kanban-card-temp-icon--${temperatura}` : ""}`}
              title={`Temperatura: ${getTemperaturaLabel(opo.opoTemperatura)}`}
              aria-label={`Temperatura: ${getTemperaturaLabel(opo.opoTemperatura)}`}
            >
              <svg viewBox="0 0 24 24" aria-hidden>
                <path d="M14 14.76V5a2 2 0 10-4 0v9.76a4 4 0 104 0z" />
              </svg>
            </span>
          </div>
        </div>

        <div className="kanban-card-responsavel">
          {responsavel ? (
            <UserAvatar name={responsavel.usuNome} avatarUrl={responsavel.usuAvatarUrl ?? null} size="sm" />
          ) : (
            <span className="kanban-card-avatar-empty" title="Sem responsável" aria-label="Sem responsável" />
          )}
          <span
            className="kanban-card-product-badge"
            style={
              produto?.proCor
                ? ({
                    backgroundColor: `${produto.proCor}22`,
                    borderColor: `${produto.proCor}55`,
                    color: produto.proCor,
                  } as React.CSSProperties)
                : undefined
            }
          >
            {produto?.proNome ?? "Não informado"}
          </span>
          {opo.opoValorOportunidade != null && (
            <span className="kanban-card-value-badge">
              {opo.opoValorOportunidade.toLocaleString("pt-BR", {
                style: "currency",
                currency: "BRL",
                minimumFractionDigits: 0,
                maximumFractionDigits: 0,
              })}
            </span>
          )}
        </div>

        <div className="kanban-card-meta">
          <span className="kanban-card-meta-icon" aria-hidden>
            <svg viewBox="0 0 24 24">
              <path d="M12 8v5l3 2M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </span>
          <span>{formatDate(getMaiorDataCard(opo))}</span>
        </div>
      </div>
    );
  };

  const openCreate = () => {
    setCreateForm({
      opoTitulo: "",
      opoNomeContato: "",
      opoTelefone: "",
      opoProId: null,
      opoUsuResponsavelId: user?.usuId ?? null,
      opoCcoId: null,
      opoDataRecebimento: getTodayDateInput(),
      opoEtkId: etapas[0]?.etkId ?? null,
      opoValorOportunidade: null,
      opoDoresMotivadores: "",
      opoComentarios: "",
    });
    setShowDores(false);
    setShowComentarios(false);
    setIsCreateOpen(true);
  };

  const saveCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSavingCreate(true);
    try {
      await api.post("/oportunidades", {
        opoTitulo: createForm.opoTitulo,
        opoNomeContato: createForm.opoNomeContato || null,
        opoTelefone: createForm.opoTelefone || null,
        opoProId: createForm.opoProId ?? null,
        opoUsuResponsavelId: createForm.opoUsuResponsavelId ?? null,
        opoCcoId: createForm.opoCcoId ?? null,
        opoDataRecebimento: createForm.opoDataRecebimento || null,
        opoEtkId: createForm.opoEtkId ?? null,
        opoValorOportunidade: createForm.opoValorOportunidade ?? null,
        opoDoresMotivadores: showDores ? createForm.opoDoresMotivadores : "",
        opoComentarios: showComentarios ? createForm.opoComentarios : "",
      });
      setIsCreateOpen(false);
      await load();
    } finally {
      setIsSavingCreate(false);
    }
  };

  if (loading) {
    return (
      <Layout>
        <Loader />
      </Layout>
    );
  }

  return (
    <Layout>
      <ListingToolbar
        singleRow
        actions={
          <>
            <button type="button" className="icon-btn" aria-label="Ver em tabela" title="Ver em tabela" onClick={() => navigate("/oportunidades")}>
              <svg viewBox="0 0 24 24" aria-hidden>
                <path d="M3 4h18v16H3zM3 10h18M9 4v16M15 4v16" />
              </svg>
            </button>
            <button
              type="button"
              className="icon-btn"
              aria-label="Nova oportunidade"
              title="Nova oportunidade"
              onClick={openCreate}
            >
              <svg viewBox="0 0 24 24" aria-hidden>
                <path d="M12 5v14M5 12h14" />
              </svg>
            </button>
          </>
        }
        filters={
          <>
            <input
              type="text"
              placeholder="Buscar oportunidade, contato ou empresa"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <div className="kanban-responsavel-filter">
              <AvatarSelect
                options={usuarios.map((u) => ({ id: u.usuId, nome: u.usuNome, avatarUrl: u.usuAvatarUrl ?? null }))}
                value={responsavelFiltro}
                placeholder="Todos"
                onChange={setResponsavelFiltro}
              />
            </div>
          </>
        }
      />

      <div className="kanban-summary">
        <span className="kanban-summary-item">Oportunidades: {oportunidadesVisiveis.length}</span>
        <span className="kanban-summary-item">
          Valor total:{" "}
          {totalValor.toLocaleString("pt-BR", { style: "currency", currency: "BRL", minimumFractionDigits: 2 })}
        </span>
      </div>

      <div className="kanban-board">
        {etapas.map((etapa) => (
          <div
            key={etapa.etkId}
            className={`kanban-column${dragOverEtkId === etapa.etkId ? " is-drop-target" : ""}`}
            style={{
              "--kanban-column-color": etapa.etkCor ?? "var(--line)",
            } as React.CSSProperties}
            onDragOver={(e) => {
              e.preventDefault();
              setDragOverEtkId(etapa.etkId);
            }}
            onDragLeave={() => {
              if (dragOverEtkId === etapa.etkId) setDragOverEtkId(null);
            }}
            onDrop={async (e) => {
              e.preventDefault();
              const draggedId = e.dataTransfer.getData("text/plain");
              await handleDropOnColumn(etapa.etkId, draggedId);
            }}
          >
            <div className="kanban-column-header">
              <span className="kanban-column-title">{etapa.etkNome}</span>
              <div className="kanban-column-metrics">
                <span className="kanban-column-count">{byEtapa(etapa.etkId).length}</span>
                <span className="kanban-column-total">
                  {valorByEtapa(etapa.etkId).toLocaleString("pt-BR", {
                    style: "currency",
                    currency: "BRL",
                    minimumFractionDigits: 0,
                    maximumFractionDigits: 0,
                  })}
                </span>
              </div>
            </div>
            <div className="kanban-column-cards">
              {draggingOportunidade &&
                dragOverEtkId === etapa.etkId &&
                (draggingOportunidade.opoEtkId ?? null) !== etapa.etkId && (
                  <div className="kanban-card kanban-card-ghost" aria-hidden>
                    <div className="kanban-card-header">
                      <span className="kanban-card-title">{draggingOportunidade.opoTitulo}</span>
                    </div>
                    <div className="kanban-card-meta">Solte aqui para mover</div>
                  </div>
                )}
              {byEtapa(etapa.etkId).map((opo) => renderCard(opo))}
            </div>
          </div>
        ))}
        {/* Coluna "Sem etapa" para oportunidades com opoEtkId null */}
        {byEtapa(null).length > 0 && (
          <div className="kanban-column kanban-column--neutral">
            <div className="kanban-column-header">
              <span className="kanban-column-title">Sem etapa</span>
              <div className="kanban-column-metrics">
                <span className="kanban-column-count">{byEtapa(null).length}</span>
                <span className="kanban-column-total">
                  {valorByEtapa(null).toLocaleString("pt-BR", {
                    style: "currency",
                    currency: "BRL",
                    minimumFractionDigits: 0,
                    maximumFractionDigits: 0,
                  })}
                </span>
              </div>
            </div>
            <div className="kanban-column-cards">
              {byEtapa(null).map((opo) => renderCard(opo))}
            </div>
          </div>
        )}
      </div>

      <Modal isOpen={isCreateOpen} title="Nova oportunidade" onClose={() => setIsCreateOpen(false)}>
        <form className="form-vertical form-scroll form-opportunity" onSubmit={saveCreate}>
          <section className="form-section">
            <h3 className="form-section-title">INFORMAÇÕES PRINCIPAIS</h3>
            <div className="form-grid">
              <label className="form-field form-field--full">
                <span className="form-label">
                  Oportunidade <span className="form-required">*</span>
                </span>
                <input
                  value={createForm.opoTitulo}
                  onChange={(e) => setCreateForm((f) => ({ ...f, opoTitulo: e.target.value }))}
                  required
                  placeholder="Digite o nome da oportunidade"
                />
              </label>
              <label className="form-field">
                <span className="form-label">Nome contato</span>
                <input
                  value={createForm.opoNomeContato}
                  onChange={(e) => setCreateForm((f) => ({ ...f, opoNomeContato: e.target.value }))}
                  placeholder="Nome do contato"
                />
              </label>
              <label className="form-field">
                <span className="form-label">Telefone</span>
                <input
                  value={createForm.opoTelefone}
                  onChange={(e) => setCreateForm((f) => ({ ...f, opoTelefone: e.target.value }))}
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
                  value={createForm.opoProId ?? ""}
                  onChange={(e) => setCreateForm((f) => ({ ...f, opoProId: e.target.value ? Number(e.target.value) : null }))}
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
                  value={createForm.opoEtkId ?? ""}
                  onChange={(e) => setCreateForm((f) => ({ ...f, opoEtkId: e.target.value ? Number(e.target.value) : null }))}
                >
                  <option value="">Selecione uma etapa</option>
                  {etapas.map((etapa) => (
                    <option key={etapa.etkId} value={etapa.etkId}>
                      {etapa.etkNome}
                    </option>
                  ))}
                </select>
              </label>
              <label className="form-field">
                <span className="form-label">Responsável</span>
                <select
                  value={createForm.opoUsuResponsavelId ?? ""}
                  onChange={(e) =>
                    setCreateForm((f) => ({ ...f, opoUsuResponsavelId: e.target.value ? Number(e.target.value) : null }))
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
                  value={createForm.opoCcoId ?? ""}
                  onChange={(e) => setCreateForm((f) => ({ ...f, opoCcoId: e.target.value ? Number(e.target.value) : null }))}
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
                  value={createForm.opoValorOportunidade ?? ""}
                  onChange={(e) =>
                    setCreateForm((f) => ({
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
                  value={createForm.opoDataRecebimento}
                  onChange={(e) => setCreateForm((f) => ({ ...f, opoDataRecebimento: e.target.value }))}
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
                  value={createForm.opoDoresMotivadores}
                  onChange={(next) => setCreateForm((f) => ({ ...f, opoDoresMotivadores: next }))}
                  placeholder="Descreva as dores e motivadores do cliente"
                />
              </div>
              <div className="form-field form-field--full">
                <OptionalTextareaField
                  isOpen={showComentarios}
                  onToggle={() => setShowComentarios((v) => !v)}
                  buttonLabel="+ Adicionar comentários"
                  label="Comentários"
                  value={createForm.opoComentarios}
                  onChange={(next) => setCreateForm((f) => ({ ...f, opoComentarios: next }))}
                  placeholder="Adicione observações importantes"
                />
              </div>
            </div>
          </section>
          <div className="modal-actions">
            <button type="button" onClick={() => setIsCreateOpen(false)} disabled={isSavingCreate}>
              Cancelar
            </button>
            <button type="submit" disabled={isSavingCreate}>
              {isSavingCreate ? "Salvando..." : "Salvar"}
            </button>
          </div>
        </form>
      </Modal>
    </Layout>
  );
};

export default OportunidadesKanbanPage;
