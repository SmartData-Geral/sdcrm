import React, { useEffect, useMemo, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import Layout from "../../components/Layout";
import Loader from "../../components/Loader";
import Modal from "../../components/Modal";
import ConfirmDialog from "../../components/ConfirmDialog";
import OptionalTextareaField from "../../components/OptionalTextareaField";
import ActionIconButton from "../../components/ActionIconButton";
import AvatarSelect from "../../components/AvatarSelect";
import TemperatureSelect from "../../components/TemperatureSelect";
import { useAuth } from "../../contexts/AuthContext";

interface OportunidadeDetail {
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
  opoMcaId: number | null;
  opoLeadScore: number | null;
  opoTemperatura: string | null;
  opoReuniaoConfirmada: boolean;
  opoPropostaEnviada: boolean;
  opoDataRecebimento: string | null;
  opoValorOportunidade: number | null;
  opoDataUltimoContato: string | null;
  opoDataFechamento: string | null;
  opoFechadoRecorrencia: number | null;
  opoValorFechado: number | null;
  opoStatusFechamento: string | null;
  opoDoresMotivadores: string | null;
  opoComentarios: string | null;
  opoAtivo: boolean;
}

interface HistoricoItem {
  ophId: number;
  ophOpoId: number;
  ophUsuId: number | null;
  ophDataRegistro: string;
  ophConteudo: string | null;
  ophAtivo: boolean;
}

interface NamedItem {
  id: number;
  nome: string;
  avatarUrl?: string | null;
}

interface MotivoCancelamentoOption {
  mcaId: number;
  mcaNome: string;
}

const OportunidadeDetalhePage: React.FC = () => {
  const { opoId } = useParams<{ opoId: string }>();
  const navigate = useNavigate();
  const { api } = useAuth();
  const [oportunidade, setOportunidade] = useState<OportunidadeDetail | null>(null);
  const [historicos, setHistoricos] = useState<HistoricoItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingHist, setLoadingHist] = useState(false);
  const [loadingSave, setLoadingSave] = useState(false);
  const [showDores, setShowDores] = useState(false);
  const [showComentarios, setShowComentarios] = useState(false);
  const [leadScoreDraft, setLeadScoreDraft] = useState<number | "">("");
  const [reuniaoDraft, setReuniaoDraft] = useState(false);
  const [propostaDraft, setPropostaDraft] = useState(false);
  const [dores, setDores] = useState("");
  const [comentarios, setComentarios] = useState("");
  const [detalheNomeContato, setDetalheNomeContato] = useState("");
  const [detalheTelefone, setDetalheTelefone] = useState("");
  const [detalheProId, setDetalheProId] = useState<number | null>(null);
  const [detalheDataRecebimento, setDetalheDataRecebimento] = useState("");
  const [detalheValorOportunidade, setDetalheValorOportunidade] = useState<number | "">("");
  const [detalheCcoId, setDetalheCcoId] = useState<number | null>(null);
  const [produtos, setProdutos] = useState<NamedItem[]>([]);
  const [usuarios, setUsuarios] = useState<NamedItem[]>([]);
  const [comoConheceu, setComoConheceu] = useState<NamedItem[]>([]);
  const [motivosPerda, setMotivosPerda] = useState<MotivoCancelamentoOption[]>([]);
  const [isPerderModalOpen, setIsPerderModalOpen] = useState(false);
  const [motivoPerdaId, setMotivoPerdaId] = useState<number | "">("");
  const [loadingPerder, setLoadingPerder] = useState(false);
  const [isStandByModalOpen, setIsStandByModalOpen] = useState(false);
  const [standByDataRetorno, setStandByDataRetorno] = useState("");
  const [loadingStandBy, setLoadingStandBy] = useState(false);
  const [isRetornoDialogOpen, setIsRetornoDialogOpen] = useState(false);
  const [isGanharModalOpen, setIsGanharModalOpen] = useState(false);
  const [ganharData, setGanharData] = useState(() => new Date().toISOString().slice(0, 10));
  const [ganharTipo, setGanharTipo] = useState<0 | 1>(0);
  const [ganharValor, setGanharValor] = useState<number | "">("");
  const [dataHistorico, setDataHistorico] = useState(() => new Date().toISOString().slice(0, 10));
  const [novoHistorico, setNovoHistorico] = useState("");
  const [editingHistoricoId, setEditingHistoricoId] = useState<number | null>(null);
  const [editingHistoricoTexto, setEditingHistoricoTexto] = useState("");

  const id = opoId ? parseInt(opoId, 10) : NaN;
  const isFechada = oportunidade?.opoStatusFechamento && ["ganho", "perdido", "stand-by"].includes(oportunidade.opoStatusFechamento);

  const loadOportunidade = async () => {
    if (!id || isNaN(id)) return;
    setLoading(true);
    try {
      const res = await api.get<OportunidadeDetail>(`/oportunidades/${id}`);
      setOportunidade(res.data);
    } catch {
      setOportunidade(null);
    } finally {
      setLoading(false);
    }
  };

  const loadHistoricos = async () => {
    if (!id || isNaN(id)) return;
    setLoadingHist(true);
    try {
      const res = await api.get<{ items: HistoricoItem[] }>(`/oportunidades/${id}/historicos`, {
        params: { page_size: 50 },
      });
      setHistoricos(res.data.items);
    } finally {
      setLoadingHist(false);
    }
  };

  const loadCombos = async () => {
    try {
      const [produtosRes, usuariosRes, ccoRes, motivosRes] = await Promise.all([
        api.get<{ items: Array<{ proId: number; proNome: string }> }>("/produtos", { params: { page_size: 100 } }),
        api.get<{ items: Array<{ usuId: number; usuNome: string; usuAvatarUrl?: string | null }> }>("/usuarios", { params: { page_size: 100 } }),
        api.get<{ items: Array<{ ccoId: number; ccoNome: string }> }>("/como-conheceu", { params: { page_size: 100 } }),
        api.get<{ items: MotivoCancelamentoOption[] }>("/motivos-cancelamento", { params: { page_size: 100, status: "ativos" } }),
      ]);
      setProdutos((produtosRes.data.items ?? []).map((i) => ({ id: i.proId, nome: i.proNome })));
      setUsuarios((usuariosRes.data.items ?? []).map((i) => ({ id: i.usuId, nome: i.usuNome, avatarUrl: i.usuAvatarUrl ?? null })));
      setComoConheceu((ccoRes.data.items ?? []).map((i) => ({ id: i.ccoId, nome: i.ccoNome })));
      setMotivosPerda(motivosRes.data.items ?? []);
    } catch {
      // combos opcionais
    }
  };

  const getNome = (list: NamedItem[], currentId: number | null) => list.find((i) => i.id === currentId)?.nome ?? "-";

  useEffect(() => {
    void loadOportunidade();
  }, [id]);

  useEffect(() => {
    if (oportunidade) void loadHistoricos();
  }, [oportunidade?.opoId]);

  useEffect(() => {
    if (!oportunidade) return;
    setDores(oportunidade.opoDoresMotivadores ?? "");
    setComentarios(oportunidade.opoComentarios ?? "");
    setDetalheNomeContato(oportunidade.opoNomeContato ?? "");
    setDetalheTelefone(oportunidade.opoTelefone ?? "");
    setDetalheProId(oportunidade.opoProId ?? null);
    setDetalheDataRecebimento(oportunidade.opoDataRecebimento ?? "");
    setDetalheValorOportunidade(oportunidade.opoValorOportunidade ?? "");
    setDetalheCcoId(oportunidade.opoCcoId ?? null);
    setLeadScoreDraft(oportunidade.opoLeadScore ?? "");
    setReuniaoDraft(oportunidade.opoReuniaoConfirmada);
    setPropostaDraft(oportunidade.opoPropostaEnviada);
    setShowDores(Boolean(oportunidade.opoDoresMotivadores));
    setShowComentarios(Boolean(oportunidade.opoComentarios));
    setMotivoPerdaId(oportunidade.opoMcaId ?? "");
    setGanharData(new Date().toISOString().slice(0, 10));
    setGanharTipo((oportunidade.opoFechadoRecorrencia as 0 | 1 | null) ?? 0);
    setGanharValor(
      oportunidade.opoValorFechado ??
        oportunidade.opoValorOportunidade ??
        ""
    );
    void loadCombos();
  }, [oportunidade?.opoId]);

  const ganhar = () => {
    setIsGanharModalOpen(true);
  };

  const confirmarGanhar = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ganharData || ganharValor === "") return;
    await api.patch(`/oportunidades/${id}/ganhar`, {
      opoDataFechamento: ganharData,
      opoFechadoRecorrencia: ganharTipo,
      opoValorFechado: Number(ganharValor),
    });
    setIsGanharModalOpen(false);
    await loadOportunidade();
  };

  const perder = async () => {
    setIsPerderModalOpen(true);
  };

  const confirmarPerda = async (e: React.FormEvent) => {
    e.preventDefault();
    if (motivoPerdaId === "") return;
    setLoadingPerder(true);
    try {
      await api.put(`/oportunidades/${id}`, { opoMcaId: Number(motivoPerdaId) });
      await api.patch(`/oportunidades/${id}/perder`);
      setIsPerderModalOpen(false);
      await loadOportunidade();
    } finally {
      setLoadingPerder(false);
    }
  };

  const standBy = async () => {
    setStandByDataRetorno(new Date().toISOString().slice(0, 10));
    setIsStandByModalOpen(true);
  };

  const confirmarStandBy = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!standByDataRetorno) return;
    setLoadingStandBy(true);
    try {
      await api.patch(`/oportunidades/${id}/stand-by`, {
        opoDataUltimoContato: standByDataRetorno,
      });
      setIsStandByModalOpen(false);
      await loadOportunidade();
    } finally {
      setLoadingStandBy(false);
    }
  };

  const confirmarRetornoParaAtivo = async () => {
    await api.patch(`/oportunidades/${id}/retornar-ativo`);
    setIsRetornoDialogOpen(false);
    await loadOportunidade();
  };

  const addHistorico = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!novoHistorico.trim()) return;
    await api.post(`/oportunidades/${id}/historicos`, {
      ophConteudo: novoHistorico.trim(),
      ophDataRegistro: `${dataHistorico}T12:00:00`,
    });
    setNovoHistorico("");
    setDataHistorico(new Date().toISOString().slice(0, 10));
    await loadHistoricos();
  };

  const updateAndamento = async (changes: {
    opoLeadScore?: number | null;
    opoReuniaoConfirmada?: boolean;
    opoPropostaEnviada?: boolean;
    opoUsuResponsavelId?: number | null;
    opoTemperatura?: string | null;
  }) => {
    await api.put(`/oportunidades/${id}`, changes);
    await loadOportunidade();
  };

  const saveComplementares = async () => {
    if (!oportunidade) return;
    setLoadingSave(true);
    try {
      await api.put(`/oportunidades/${id}`, {
        opoLeadScore: leadScoreDraft === "" ? null : Number(leadScoreDraft),
        opoReuniaoConfirmada: reuniaoDraft,
        opoPropostaEnviada: propostaDraft,
        opoNomeContato: detalheNomeContato || null,
        opoTelefone: detalheTelefone || null,
        opoProId: detalheProId ?? null,
        opoSolucao: detalheProId ? getNome(produtos, detalheProId) : null,
        opoDataRecebimento: detalheDataRecebimento || null,
        opoValorOportunidade: detalheValorOportunidade === "" ? null : Number(detalheValorOportunidade),
        opoCcoId: detalheCcoId ?? null,
        opoDoresMotivadores: showDores ? dores : null,
        opoComentarios: showComentarios ? comentarios : null,
      });
      await loadOportunidade();
    } finally {
      setLoadingSave(false);
    }
  };

  const startEditHistorico = (h: HistoricoItem) => {
    setEditingHistoricoId(h.ophId);
    setEditingHistoricoTexto(h.ophConteudo ?? "");
  };

  const saveEditHistorico = async () => {
    if (!editingHistoricoId) return;
    await api.put(`/historicos-oportunidade/${editingHistoricoId}`, {
      ophConteudo: editingHistoricoTexto,
    });
    setEditingHistoricoId(null);
    setEditingHistoricoTexto("");
    await loadHistoricos();
  };

  const statusBadgeClass = useMemo(() => {
    if (!oportunidade?.opoStatusFechamento) return "status-badge status-badge--open";
    if (oportunidade.opoStatusFechamento === "ganho") return "status-badge status-badge--active";
    return "status-badge status-badge--inactive";
  }, [oportunidade?.opoStatusFechamento]);

  const statusAberto = !oportunidade?.opoStatusFechamento || oportunidade.opoStatusFechamento === "aberto";
  const podeRetornarAtivo =
    oportunidade?.opoStatusFechamento === "perdido" || oportunidade?.opoStatusFechamento === "stand-by";

  if (loading || !id) {
    return (
      <Layout>
        {loading ? <Loader /> : <p>Oportunidade não encontrada.</p>}
      </Layout>
    );
  }

  if (!oportunidade) {
    return (
      <Layout>
        <p>Oportunidade não encontrada.</p>
        <button type="button" onClick={() => navigate("/oportunidades")}>
          Voltar
        </button>
      </Layout>
    );
  }

  return (
    <Layout>
      <section className="surface-card oportunidade-context">
        <div className="oportunidade-context-top">
          <div className="oportunidade-breadcrumb">Dashboard &gt; CRM &gt; Oportunidades</div>
          <div className="oportunidade-title-row">
            <h1>{oportunidade.opoTitulo}</h1>
            <div className="page-header-actions page-header-actions--wrap oportunidade-actions">
              {!isFechada && (
                <>
                  <button type="button" className="success" onClick={ganhar}>
                    Ganhar
                  </button>
                  <button type="button" className="danger" onClick={perder}>
                    Perder
                  </button>
                  <button type="button" className="warning" onClick={standBy}>
                    Stand-by
                  </button>
                </>
              )}
              {podeRetornarAtivo && (
                <button type="button" className="btn-primary" onClick={() => setIsRetornoDialogOpen(true)}>
                  Retornar para ativo
                </button>
              )}
              <button type="button" onClick={() => navigate("/oportunidades")}>
                Voltar
              </button>
            </div>
          </div>
          <div className="oportunidade-context-line">
            <label className="context-item context-item--responsavel inline-edit-field">
              <AvatarSelect
                options={usuarios}
                value={oportunidade.opoUsuResponsavelId ?? null}
                placeholder="Responsável"
                onChange={async (next) => {
                  await updateAndamento({ opoUsuResponsavelId: next });
                }}
              />
            </label>
            <label className="context-item inline-edit-field">
              <span>Temperatura:</span>
              <TemperatureSelect
                value={oportunidade.opoTemperatura ?? ""}
                placeholder="-"
                onChange={async (next) => {
                  await updateAndamento({ opoTemperatura: next });
                }}
              />
            </label>
            <label className="context-item inline-edit-field">
              <span>Lead Score:</span>
              <select
                value={leadScoreDraft}
                onChange={async (e) => {
                  const next = e.target.value ? Number(e.target.value) : "";
                  setLeadScoreDraft(next);
                  await updateAndamento({ opoLeadScore: next === "" ? null : Number(next) });
                }}
              >
                <option value="">-</option>
                {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((v) => (
                  <option key={v} value={v}>
                    {v}
                  </option>
                ))}
              </select>
            </label>
            <label className="context-item inline-toggle">
              <span>Reunião</span>
              <input
                type="checkbox"
                checked={reuniaoDraft}
                onChange={async (e) => {
                  const checked = e.target.checked;
                  setReuniaoDraft(checked);
                  await updateAndamento({ opoReuniaoConfirmada: checked });
                }}
              />
            </label>
            <label className="context-item inline-toggle">
              <span>Proposta</span>
              <input
                type="checkbox"
                checked={propostaDraft}
                onChange={async (e) => {
                  const checked = e.target.checked;
                  setPropostaDraft(checked);
                  await updateAndamento({ opoPropostaEnviada: checked });
                }}
              />
            </label>
            {!statusAberto && <span className={`context-item ${statusBadgeClass}`}>{oportunidade.opoStatusFechamento}</span>}
          </div>
        </div>
      </section>

      <div className="detail-columns">
        <div className="detail-left">
          <section className="surface-card details-card">
            <h2 className="section-title">Detalhes da oportunidade</h2>
            <div className="info-grid">
              <div className="info-item">
                <span className="info-label">Solução</span>
                <select
                  className="detail-inline-input"
                  value={detalheProId ?? ""}
                  onChange={(e) => setDetalheProId(e.target.value ? Number(e.target.value) : null)}
                >
                  <option value="">Selecione</option>
                  {produtos.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.nome}
                    </option>
                  ))}
                </select>
              </div>
              <div className="info-item">
                <span className="info-label">Nome contato</span>
                <input
                  className="detail-inline-input"
                  value={detalheNomeContato}
                  onChange={(e) => setDetalheNomeContato(e.target.value)}
                  placeholder="Nome do contato"
                />
              </div>
              <div className="info-item">
                <span className="info-label">Como conheceu</span>
                <select
                  className="detail-inline-input"
                  value={detalheCcoId ?? ""}
                  onChange={(e) => setDetalheCcoId(e.target.value ? Number(e.target.value) : null)}
                >
                  <option value="">Selecione</option>
                  {comoConheceu.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.nome}
                    </option>
                  ))}
                </select>
              </div>
              <div className="info-item">
                <span className="info-label">Telefone</span>
                <input
                  className="detail-inline-input"
                  value={detalheTelefone}
                  onChange={(e) => setDetalheTelefone(e.target.value)}
                  placeholder="(00) 00000-0000"
                />
              </div>
              <div className="info-item">
                <span className="info-label">Data de recebimento</span>
                <input
                  type="date"
                  className="detail-inline-input"
                  value={detalheDataRecebimento}
                  onChange={(e) => setDetalheDataRecebimento(e.target.value)}
                />
              </div>
              <div className="info-item">
                <span className="info-label">Valor oportunidade</span>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  className="detail-inline-input"
                  value={detalheValorOportunidade}
                  onChange={(e) => setDetalheValorOportunidade(e.target.value ? Number(e.target.value) : "")}
                  placeholder="0,00"
                />
              </div>
            </div>
            <div className="details-expandables">
              <OptionalTextareaField
                isOpen={showDores}
                onToggle={() => setShowDores((v) => !v)}
                buttonLabel="Clique para adicionar dores / motivadores"
                label="Dores / Motivadores"
                value={dores}
                onChange={setDores}
              />
              <OptionalTextareaField
                isOpen={showComentarios}
                onToggle={() => setShowComentarios((v) => !v)}
                buttonLabel="Clique para adicionar comentários"
                label="Comentários"
                value={comentarios}
                onChange={setComentarios}
              />
              <div className="details-expandables-actions">
                <button type="button" className="btn-primary" onClick={saveComplementares} disabled={loadingSave}>
                  {loadingSave ? "Salvando..." : "Salvar alterações"}
                </button>
              </div>
            </div>
          </section>
        </div>

        <aside className="detail-right">
          <section className="surface-card details-card">
            <h2 className="section-title">Histórico</h2>
            <form className="history-add-form" onSubmit={addHistorico}>
              <label className="form-field">
                <span className="form-label">Data do registro</span>
                <input type="date" value={dataHistorico} onChange={(e) => setDataHistorico(e.target.value)} />
              </label>
              <label className="form-field form-field--full">
                <span className="form-label">Conteúdo</span>
                <textarea
                  value={novoHistorico}
                  onChange={(e) => setNovoHistorico(e.target.value)}
                  rows={3}
                  required
                  placeholder="Registre o que aconteceu..."
                />
              </label>
              <div className="history-add-actions">
                <button type="submit" className="btn-primary">
                  Adicionar histórico
                </button>
              </div>
            </form>

            {loadingHist ? (
              <Loader />
            ) : historicos.length === 0 ? (
              <p className="muted-text">Nenhum registro de histórico.</p>
            ) : (
              <ul className="history-list timeline-list">
                {historicos.map((h) => (
                  <li key={h.ophId} className="history-item timeline-item">
                    <div className="history-item-top">
                      <div className="history-meta-inline">
                        <span className="history-date">{new Date(h.ophDataRegistro).toLocaleString("pt-BR")}</span>
                        <span className="history-author">Por: {h.ophUsuId ? getNome(usuarios, h.ophUsuId) : "Sistema"}</span>
                      </div>
                      {editingHistoricoId !== h.ophId && (
                        <div className="history-item-actions history-item-actions--top">
                          <ActionIconButton icon="edit" label="Editar histórico" onClick={() => startEditHistorico(h)} />
                        </div>
                      )}
                    </div>
                    {editingHistoricoId === h.ophId ? (
                      <>
                        <textarea
                          value={editingHistoricoTexto}
                          onChange={(e) => setEditingHistoricoTexto(e.target.value)}
                          rows={3}
                        />
                        <div className="history-item-actions">
                          <button type="button" onClick={() => setEditingHistoricoId(null)}>
                            Cancelar
                          </button>
                          <button type="button" className="btn-primary" onClick={saveEditHistorico}>
                            Salvar
                          </button>
                        </div>
                      </>
                    ) : (
                      <div className="pre-wrap">{h.ophConteudo ?? "-"}</div>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </section>
        </aside>
      </div>
      <Modal isOpen={isPerderModalOpen} title="Marcar como perdida" onClose={() => setIsPerderModalOpen(false)}>
        <form className="form-vertical" onSubmit={confirmarPerda}>
          <label>
            Motivo de perda
            <select value={motivoPerdaId} onChange={(e) => setMotivoPerdaId(e.target.value ? Number(e.target.value) : "")} required>
              <option value="">Selecione</option>
              {motivosPerda.map((motivo) => (
                <option key={motivo.mcaId} value={motivo.mcaId}>
                  {motivo.mcaNome}
                </option>
              ))}
            </select>
          </label>
          <div className="modal-actions">
            <button type="button" onClick={() => setIsPerderModalOpen(false)} disabled={loadingPerder}>
              Cancelar
            </button>
            <button type="submit" className="danger" disabled={loadingPerder || motivoPerdaId === ""}>
              {loadingPerder ? "Salvando..." : "Confirmar perda"}
            </button>
          </div>
        </form>
      </Modal>
      <Modal isOpen={isStandByModalOpen} title="Colocar em stand-by" onClose={() => setIsStandByModalOpen(false)}>
        <form className="form-vertical" onSubmit={confirmarStandBy}>
          <label>
            Data de retorno
            <input
              type="date"
              value={standByDataRetorno}
              onChange={(e) => setStandByDataRetorno(e.target.value)}
              min={new Date().toISOString().slice(0, 10)}
              required
            />
          </label>
          <div className="modal-actions">
            <button type="button" onClick={() => setIsStandByModalOpen(false)} disabled={loadingStandBy}>
              Cancelar
            </button>
            <button type="submit" className="warning" disabled={loadingStandBy || !standByDataRetorno}>
              {loadingStandBy ? "Salvando..." : "Confirmar stand-by"}
            </button>
          </div>
        </form>
      </Modal>
      <Modal isOpen={isGanharModalOpen} title="Marcar como ganha" onClose={() => setIsGanharModalOpen(false)}>
        <form className="form-vertical" onSubmit={confirmarGanhar}>
          <label>
            Data
            <input
              type="date"
              value={ganharData}
              onChange={(e) => setGanharData(e.target.value)}
              required
            />
          </label>
          <label>
            Tipo
            <select
              value={ganharTipo}
              onChange={(e) => setGanharTipo(Number(e.target.value) as 0 | 1)}
            >
              <option value={0}>Recorrência</option>
              <option value={1}>Projeto</option>
            </select>
          </label>
          <label>
            Valor fechado
            <input
              type="number"
              step="0.01"
              min="0"
              value={ganharValor}
              onChange={(e) => setGanharValor(e.target.value ? Number(e.target.value) : "")}
              required
            />
          </label>
          <div className="modal-actions">
            <button type="button" onClick={() => setIsGanharModalOpen(false)}>
              Cancelar
            </button>
            <button type="submit" className="success" disabled={ganharValor === ""}>
              Confirmar ganho
            </button>
          </div>
        </form>
      </Modal>
      <ConfirmDialog
        isOpen={isRetornoDialogOpen}
        title="Retornar para ativo"
        message={`Deseja retornar a oportunidade "${oportunidade.opoTitulo}" para ativo?`}
        onCancel={() => setIsRetornoDialogOpen(false)}
        onConfirm={confirmarRetornoParaAtivo}
      />
    </Layout>
  );
};

export default OportunidadeDetalhePage;
