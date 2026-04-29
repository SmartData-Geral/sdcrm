import React, { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import Layout from "../../components/Layout";
import Loader from "../../components/Loader";
import Modal from "../../components/Modal";
import ConfirmDialog from "../../components/ConfirmDialog";
import OptionalTextareaField from "../../components/OptionalTextareaField";
import ActionIconButton from "../../components/ActionIconButton";
import AvatarSelect from "../../components/AvatarSelect";
import TemperatureSelect from "../../components/TemperatureSelect";
import ReuniaoIaSection from "../../components/oportunidades/ReuniaoIaSection";
import {
  OportunidadeIconButton,
  IcoSave,
  IcoPlus,
  IcoFilePlus,
  IcoX,
  IcoCheck,
  IcoArrowLeft,
  IcoLayers,
  IcoMessage,
  IcoTrending,
  IcoCheckCircle,
  IcoXCircle,
  IcoPause,
  IcoRotateCcw,
  IcoSpinner,
} from "../../components/oportunidades/OportunidadeIconButton";
import { useAuth } from "../../contexts/AuthContext";
import { getPublicProposalUrl } from "../../utils/api";
import { getOportunidadePipelineContext } from "../../utils/oportunidadePipeline";
import { ContratoItem } from "../../components/contratos/wizardTypes";

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
  opoReceitaPontual: boolean;
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

interface PropostaItem {
  prpId: number;
  prpTitulo: string;
  prpTipo: "projeto" | "planos" | "hibrida";
  prpStatus: string;
  prpTokenPublico: string;
  prpVersaoAtual: number | null;
  prpDataCriacao?: string | null;
}

interface PropostaTemplateItem {
  ptlId: number;
  ptlNome: string;
  ptlTipoProposta: "projeto" | "planos" | "hibrida";
  ptlTipoSolucao: string | null;
  ptlAtivo: boolean;
}

type OportunidadeDetailTab = "geral" | "reunioes" | "propostas" | "contrato";

const OportunidadeDetalhePage: React.FC = () => {
  const { opoId } = useParams<{ opoId: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const pipelineContext = useMemo(() => getOportunidadePipelineContext(location.pathname), [location.pathname]);
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
  const [detalheTitulo, setDetalheTitulo] = useState("");
  const [detalheNomeContato, setDetalheNomeContato] = useState("");
  const [detalheTelefone, setDetalheTelefone] = useState("");
  const [detalheProId, setDetalheProId] = useState<number | null>(null);
  const [detalheDataRecebimento, setDetalheDataRecebimento] = useState("");
  const [detalheValorOportunidade, setDetalheValorOportunidade] = useState<number | "">("");
  const [detalheReceitaPontual, setDetalheReceitaPontual] = useState(false);
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
  const [propostas, setPropostas] = useState<PropostaItem[]>([]);
  const [loadingPropostas, setLoadingPropostas] = useState(false);
  const [templates, setTemplates] = useState<PropostaTemplateItem[]>([]);
  const [contrato, setContrato] = useState<ContratoItem | null>(null);
  const [loadingContrato, setLoadingContrato] = useState(false);
  const [isNovaPropostaModalOpen, setIsNovaPropostaModalOpen] = useState(false);
  const [novaPropostaForm, setNovaPropostaForm] = useState({
    prpTitulo: "",
    prpTipo: "projeto" as "projeto" | "planos" | "hibrida",
    prpTplId: "" as number | "",
  });
  const [isSubstituicaoContratoModalOpen, setIsSubstituicaoContratoModalOpen] = useState(false);
  const [substituicaoManterDados, setSubstituicaoManterDados] = useState<"manter" | "zerar" | null>(null);
  const [loadingSubstituicaoContrato, setLoadingSubstituicaoContrato] = useState(false);
  const [detailTab, setDetailTab] = useState<OportunidadeDetailTab>("geral");

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

  const loadPropostas = async () => {
    if (!id || isNaN(id)) return;
    setLoadingPropostas(true);
    try {
      const res = await api.get<{ items: PropostaItem[] }>(`/oportunidades/${id}/propostas`, {
        params: { page_size: 100 },
      });
      setPropostas(res.data.items ?? []);
    } finally {
      setLoadingPropostas(false);
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
      const templatesRes = await api.get<{ items: PropostaTemplateItem[] }>("/templates-proposta", {
        params: { page_size: 200 },
      });
      setTemplates((templatesRes.data.items ?? []).filter((t) => t.ptlAtivo));
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
    if (oportunidade) void loadPropostas();
  }, [oportunidade?.opoId]);

  const loadContrato = async () => {
    if (!id || isNaN(id)) return;
    setLoadingContrato(true);
    try {
      const res = await api.get<ContratoItem>(`/oportunidades/${id}/contrato`);
      setContrato(res.data);
    } catch {
      setContrato(null);
    } finally {
      setLoadingContrato(false);
    }
  };

  const confirmarSubstituicaoContrato = async () => {
    if (!contrato || substituicaoManterDados === null) return;
    setLoadingSubstituicaoContrato(true);
    try {
      const res = await api.patch<ContratoItem>(`/contratos/${contrato.ctrId}/inativar`);
      setContrato(null);
      setIsSubstituicaoContratoModalOpen(false);
      setSubstituicaoManterDados(null);
      navigate(
        pipelineContext.contractNewPath(id),
        substituicaoManterDados === "manter" ? { state: { prefillContrato: res.data } } : undefined
      );
    } catch (e: unknown) {
      const detail = typeof e === "object" && e !== null && "response" in e ? (e as { response?: { data?: { detail?: string } } }).response?.data?.detail : undefined;
      alert(detail ?? "Não foi possível inativar o contrato.");
    } finally {
      setLoadingSubstituicaoContrato(false);
    }
  };

  useEffect(() => {
    if (oportunidade) void loadContrato();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [oportunidade?.opoId]);

  useEffect(() => {
    if (!oportunidade) return;
    setDetalheTitulo(oportunidade.opoTitulo);
    setDores(oportunidade.opoDoresMotivadores ?? "");
    setComentarios(oportunidade.opoComentarios ?? "");
    setDetalheNomeContato(oportunidade.opoNomeContato ?? "");
    setDetalheTelefone(oportunidade.opoTelefone ?? "");
    setDetalheProId(oportunidade.opoProId ?? null);
    setDetalheDataRecebimento(oportunidade.opoDataRecebimento ?? "");
    setDetalheValorOportunidade(oportunidade.opoValorOportunidade ?? "");
    setDetalheReceitaPontual(Boolean(oportunidade.opoReceitaPontual));
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
        opoTitulo: detalheTitulo || oportunidade.opoTitulo,
        opoLeadScore: leadScoreDraft === "" ? null : Number(leadScoreDraft),
        opoReuniaoConfirmada: reuniaoDraft,
        opoPropostaEnviada: propostaDraft,
        opoNomeContato: detalheNomeContato || null,
        opoTelefone: detalheTelefone || null,
        opoProId: detalheProId ?? null,
        opoSolucao: detalheProId ? getNome(produtos, detalheProId) : null,
        opoDataRecebimento: detalheDataRecebimento || null,
        opoValorOportunidade: detalheValorOportunidade === "" ? null : Number(detalheValorOportunidade),
        opoReceitaPontual: detalheReceitaPontual,
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

  const criarProposta = () => {
    setNovaPropostaForm({
      prpTitulo: `Proposta - ${oportunidade.opoTitulo}`,
      prpTipo: "projeto",
      prpTplId: "",
    });
    setIsNovaPropostaModalOpen(true);
  };

  const confirmarCriarProposta = async (e: React.FormEvent) => {
    e.preventDefault();
    const selectedTemplate = templates.find((t) => t.ptlId === novaPropostaForm.prpTplId);
    const payload = {
      prpOpoId: id,
      prpTitulo: novaPropostaForm.prpTitulo,
      prpTipo: selectedTemplate?.ptlTipoProposta ?? novaPropostaForm.prpTipo,
      prpTplId: novaPropostaForm.prpTplId === "" ? null : Number(novaPropostaForm.prpTplId),
      prpNomeContato: oportunidade.opoNomeContato ?? null,
      prpEmailContato: oportunidade.opoEmail ?? null,
      prpWhatsappContato: oportunidade.opoTelefone ?? null,
      prpUsuResponsavelId: oportunidade.opoUsuResponsavelId ?? null,
    };
    const res = await api.post<PropostaItem>("/propostas", payload);
    setIsNovaPropostaModalOpen(false);
    await loadPropostas();
    navigate(`/propostas/${res.data.prpId}/editor`);
  };

  const publicarProposta = async (prpId: number) => {
    await api.patch(`/propostas/${prpId}/publicar`, { forcar_nova_versao: true });
    await loadPropostas();
  };

  const duplicarProposta = async (prpId: number) => {
    await api.patch(`/propostas/${prpId}/duplicar`);
    await loadPropostas();
  };

  const copiarLinkProposta = async (token: string) => {
    const link = getPublicProposalUrl(token);
    await navigator.clipboard.writeText(link);
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
        <button type="button" onClick={() => navigate(pipelineContext.listPath)}>
          Voltar
        </button>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="oportunidade-page">
      <section className={`surface-card oportunidade-context${oportunidade.opoStatusFechamento === "ganho" ? " oportunidade-context--ganho" : oportunidade.opoStatusFechamento === "perdido" ? " oportunidade-context--perdido" : oportunidade.opoStatusFechamento === "stand-by" ? " oportunidade-context--standby" : ""}`}>
        <div className="oportunidade-context-top">
          <div className="oportunidade-breadcrumb">Dashboard &gt; {pipelineContext.sectionLabel} &gt; Oportunidades</div>
          <div className="oportunidade-title-row">
            <div className="oportunidade-title-edit">
              <input
                className="oportunidade-title-input"
                value={detalheTitulo}
                onChange={(e) => setDetalheTitulo(e.target.value)}
                placeholder="Nome da oportunidade"
              />
            </div>
            <div className="page-header-actions page-header-actions--wrap oportunidade-actions">
              {!isFechada && (
                <>
                  <button type="button" className="success oportunidade-header-action" onClick={ganhar}>
                    <span className="oportunidade-header-action__ico" aria-hidden>
                      <IcoCheckCircle />
                    </span>
                    Ganhar
                  </button>
                  <button type="button" className="danger oportunidade-header-action" onClick={perder}>
                    <span className="oportunidade-header-action__ico" aria-hidden>
                      <IcoXCircle />
                    </span>
                    Perder
                  </button>
                  <button type="button" className="warning oportunidade-header-action" onClick={standBy}>
                    <span className="oportunidade-header-action__ico" aria-hidden>
                      <IcoPause />
                    </span>
                    Stand-by
                  </button>
                </>
              )}
              {podeRetornarAtivo && (
                <button type="button" className="btn-primary oportunidade-header-action" onClick={() => setIsRetornoDialogOpen(true)}>
                  <span className="oportunidade-header-action__ico" aria-hidden>
                    <IcoRotateCcw />
                  </span>
                  Retornar para ativo
                </button>
              )}
              <OportunidadeIconButton
                variant="ghost"
                label="Voltar à lista de oportunidades"
                icon={<IcoArrowLeft />}
                onClick={() => navigate(pipelineContext.listPath)}
              />
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
              <span className="context-field-label">Temperatura</span>
              <TemperatureSelect
                value={oportunidade.opoTemperatura ?? ""}
                placeholder="-"
                onChange={async (next) => {
                  await updateAndamento({ opoTemperatura: next });
                }}
              />
            </label>
            <label className="context-item inline-edit-field">
              <span className="context-field-label">Lead score</span>
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
            <span className="context-divider" aria-hidden="true" />
            <button
              type="button"
              className={`context-chip${reuniaoDraft ? " context-chip--active" : ""}`}
              onClick={async () => {
                const next = !reuniaoDraft;
                setReuniaoDraft(next);
                await updateAndamento({ opoReuniaoConfirmada: next });
              }}
              aria-pressed={reuniaoDraft}
            >
              {reuniaoDraft && <span className="context-chip__check"><IcoCheck /></span>}
              Reunião
            </button>
            <button
              type="button"
              className={`context-chip${propostaDraft ? " context-chip--active" : ""}`}
              onClick={async () => {
                const next = !propostaDraft;
                setPropostaDraft(next);
                await updateAndamento({ opoPropostaEnviada: next });
              }}
              aria-pressed={propostaDraft}
            >
              {propostaDraft && <span className="context-chip__check"><IcoCheck /></span>}
              Proposta
            </button>
            {!statusAberto && <span className={`context-item ${statusBadgeClass}`}>{oportunidade.opoStatusFechamento}</span>}
          </div>
        </div>
      </section>

      <div className="oportunidade-detail-tabs-wrap surface-card">
        <nav className="oportunidade-detail-tabs" role="tablist" aria-label="Seções da oportunidade">
          <button
            type="button"
            role="tab"
            id="tab-oportunidade-geral"
            aria-selected={detailTab === "geral"}
            aria-controls="panel-oportunidade-geral"
            className="oportunidade-detail-tab"
            onClick={() => setDetailTab("geral")}
          >
            Geral
          </button>
          <button
            type="button"
            role="tab"
            id="tab-oportunidade-reunioes"
            aria-selected={detailTab === "reunioes"}
            aria-controls="panel-oportunidade-reunioes"
            className="oportunidade-detail-tab"
            onClick={() => setDetailTab("reunioes")}
          >
            Reuniões
          </button>
          <button
            type="button"
            role="tab"
            id="tab-oportunidade-propostas"
            aria-selected={detailTab === "propostas"}
            aria-controls="panel-oportunidade-propostas"
            className="oportunidade-detail-tab"
            onClick={() => setDetailTab("propostas")}
          >
            Propostas
            {propostas.length > 0 ? (
              <span className="oportunidade-detail-tab-badge" aria-hidden>
                {propostas.length}
              </span>
            ) : null}
          </button>
          <button
            type="button"
            role="tab"
            id="tab-oportunidade-contrato"
            aria-selected={detailTab === "contrato"}
            aria-controls="panel-oportunidade-contrato"
            className="oportunidade-detail-tab"
            onClick={() => setDetailTab("contrato")}
          >
            Contrato
            {contrato ? (
              <span className="oportunidade-detail-tab-badge" aria-hidden>
                1
              </span>
            ) : null}
          </button>
        </nav>
      </div>

      <div className="oportunidade-detail-panels">
        {detailTab === "geral" && (
          <div
            id="panel-oportunidade-geral"
            role="tabpanel"
            aria-labelledby="tab-oportunidade-geral"
            className="detail-columns"
          >
            <div className="detail-left">
              <section className="surface-card details-card">
                <h2 className="section-title section-title--panel">Detalhes da oportunidade</h2>
                <div className="oportunidade-detail-field-groups" role="group" aria-label="Campos da oportunidade">
                  <div className="detail-field-group">
                    <h3 className="detail-field-group-title"><span className="field-group-ico"><IcoLayers /></span>Solução e origem</h3>
                    <div className="detail-field-group-grid">
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
                    </div>
                  </div>

                  <div className="detail-field-group">
                    <h3 className="detail-field-group-title"><span className="field-group-ico"><IcoMessage /></span>Contato</h3>
                    <div className="detail-field-group-grid">
                      <div className="info-item">
                        <span className="info-label">Nome</span>
                        <input
                          className="detail-inline-input"
                          value={detalheNomeContato}
                          onChange={(e) => setDetalheNomeContato(e.target.value)}
                          placeholder="Nome do contato"
                        />
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
                    </div>
                  </div>

                  <div className="detail-field-group">
                    <h3 className="detail-field-group-title"><span className="field-group-ico"><IcoTrending /></span>Valor e modelo de receita</h3>
                    <div className="detail-field-group-grid">
                      <div className="info-item">
                        <span className="info-label">Valor da oportunidade</span>
                        <div className="valor-input-wrap">
                          <span className="valor-prefix">R$</span>
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
                      <div className="info-item">
                        <span className="info-label">Tipo de receita</span>
                        <div className="receita-type-toggle">
                          <button
                            type="button"
                            className={`receita-type-btn${!detalheReceitaPontual ? " receita-type-btn--active" : ""}`}
                            onClick={() => setDetalheReceitaPontual(false)}
                          >
                            Recorrente
                            <span className="receita-type-sub">MRR</span>
                          </button>
                          <button
                            type="button"
                            className={`receita-type-btn${detalheReceitaPontual ? " receita-type-btn--active" : ""}`}
                            onClick={() => setDetalheReceitaPontual(true)}
                          >
                            Pontual
                            <span className="receita-type-sub">Único</span>
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="detail-field-group detail-field-group--compact">
                    <h3 className="detail-field-group-title">
                      <span className="field-group-ico">
                        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
                      </span>
                      Entrada no funil
                    </h3>
                    <div className="detail-field-group-grid detail-field-group-grid--single">
                      <div className="info-item">
                        <span className="info-label">Data de recebimento</span>
                        <input
                          type="date"
                          className="detail-inline-input"
                          value={detalheDataRecebimento}
                          onChange={(e) => setDetalheDataRecebimento(e.target.value)}
                        />
                      </div>
                    </div>
                  </div>
                </div>
                <div className="details-expandables">
                  <OptionalTextareaField
                    isOpen={showDores}
                    onToggle={() => setShowDores((v) => !v)}
                    buttonLabel="Adicionar dores / motivadores"
                    label="Dores / Motivadores"
                    value={dores}
                    onChange={setDores}
                    toggleLeadingIcon={
                      <span className="oportunidade-inline-ico">
                        <IcoPlus />
                      </span>
                    }
                  />
                  <OptionalTextareaField
                    isOpen={showComentarios}
                    onToggle={() => setShowComentarios((v) => !v)}
                    buttonLabel="Adicionar comentários"
                    label="Comentários"
                    value={comentarios}
                    onChange={setComentarios}
                    toggleLeadingIcon={
                      <span className="oportunidade-inline-ico">
                        <IcoPlus />
                      </span>
                    }
                  />
                  <div className="details-expandables-actions">
                    <button
                      type="button"
                      className="btn-primary oportunidade-save-btn"
                      onClick={() => void saveComplementares()}
                      disabled={loadingSave}
                    >
                      <span className="oportunidade-save-btn__ico">
                        {loadingSave ? <IcoSpinner /> : <IcoSave />}
                      </span>
                      {loadingSave ? "Salvando..." : "Salvar alterações"}
                    </button>
                  </div>
                </div>
              </section>
            </div>
            <aside className="detail-right oportunidade-history-column">
              <section className="surface-card details-card">
                <h2 className="section-title section-title--panel">Histórico</h2>
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
                    <OportunidadeIconButton type="submit" variant="outline-brand" label="Adicionar ao histórico" icon={<IcoPlus />} />
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
                              <OportunidadeIconButton
                                variant="subtle"
                                label="Cancelar edição do histórico"
                                icon={<IcoX />}
                                onClick={() => setEditingHistoricoId(null)}
                              />
                              <OportunidadeIconButton
                                variant="outline-brand"
                                label="Salvar alterações no histórico"
                                icon={<IcoCheck />}
                                onClick={() => void saveEditHistorico()}
                              />
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
        )}

        {detailTab === "reunioes" && (
          <div
            id="panel-oportunidade-reunioes"
            role="tabpanel"
            aria-labelledby="tab-oportunidade-reunioes"
            className="oportunidade-detail-stack"
          >
            <ReuniaoIaSection opoId={id} onOpportunityRefresh={loadOportunidade} />
          </div>
        )}

        {detailTab === "propostas" && (
          <div
            id="panel-oportunidade-propostas"
            role="tabpanel"
            aria-labelledby="tab-oportunidade-propostas"
            className="oportunidade-detail-stack"
          >
            <section className="surface-card details-card">
              <div className="proposal-section-header">
                <h2 className="section-title section-title--panel">Propostas</h2>
                <OportunidadeIconButton
                  variant="outline-brand"
                  label="Nova proposta"
                  icon={<IcoFilePlus />}
                  onClick={criarProposta}
                />
              </div>
              {loadingPropostas ? (
                <Loader />
              ) : propostas.length === 0 ? (
                <p className="muted-text">Nenhuma proposta cadastrada para esta oportunidade.</p>
              ) : (
                <div className="proposal-table-wrapper">
                  <table className="datatable">
                    <thead>
                      <tr>
                        <th>Título</th>
                        <th>Tipo</th>
                        <th>Status</th>
                        <th>Versão</th>
                        <th>Ações</th>
                      </tr>
                    </thead>
                    <tbody>
                      {propostas.map((p) => (
                        <tr key={p.prpId}>
                          <td>{p.prpTitulo}</td>
                          <td>{p.prpTipo}</td>
                          <td>
                            <span className="status-badge status-badge--open">{p.prpStatus}</span>
                          </td>
                          <td>{p.prpVersaoAtual ?? "-"}</td>
                          <td>
                            <div className="actions">
                              <ActionIconButton icon="edit" label="Editar" onClick={() => navigate(`/propostas/${p.prpId}/editor`)} />
                              <ActionIconButton
                                icon="view"
                                label="Visualizar página pública"
                                onClick={() => window.open(getPublicProposalUrl(p.prpTokenPublico), "_blank")}
                              />
                              <ActionIconButton icon="view" label="Copiar link" onClick={() => copiarLinkProposta(p.prpTokenPublico)} />
                              <ActionIconButton icon="activate" label="Publicar" tone="success" onClick={() => publicarProposta(p.prpId)} />
                              <ActionIconButton icon="edit" label="Duplicar" onClick={() => duplicarProposta(p.prpId)} />
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>
          </div>
        )}
        {detailTab === "contrato" && (
          <div
            id="panel-oportunidade-contrato"
            role="tabpanel"
            aria-labelledby="tab-oportunidade-contrato"
            className="oportunidade-detail-stack"
          >
            <section className="surface-card details-card">
              <div className="proposal-section-header">
                <h2 className="section-title section-title--panel">Contrato</h2>
              </div>

              {loadingContrato ? (
                <Loader />
              ) : contrato ? (
                <div style={{ display: "flex", gap: 12, alignItems: "center", justifyContent: "space-between" }}>
                  <div>
                    <p className="muted-text" style={{ margin: 0 }}>
                      Status: <strong>{contrato.ctrStatus}</strong>
                    </p>
                    <p className="muted-text" style={{ marginTop: 6 }}>
                      Edite valores cadastrais, cláusulas e gere pré-visualização quando precisar. Alterações aparecem na próxima geração de HTML ou PDF.
                    </p>
                  </div>
                  <div style={{ display: "flex", gap: 10, flexWrap: "wrap", justifyContent: "flex-end" }}>
                    <button
                      type="button"
                      disabled={loadingSubstituicaoContrato}
                      title="Inativa este contrato e abre um novo fluxo nesta oportunidade."
                      onClick={() => {
                        setSubstituicaoManterDados(null);
                        setIsSubstituicaoContratoModalOpen(true);
                      }}
                    >
                      Substituir contrato
                    </button>
                    <button type="button" onClick={() => navigate(`/contratos/${contrato.ctrId}/editor?step=2`)}>
                      Dados do contrato
                    </button>
                    <button type="button" onClick={() => navigate(`/contratos/${contrato.ctrId}/editor`)}>
                      Cláusulas
                    </button>
                    <button type="button" className="btn-primary" onClick={() => navigate(`/contratos/${contrato.ctrId}/editor?step=4`)}>
                      Preview / PDF
                    </button>
                  </div>
                </div>
              ) : (
                <div>
                  <p className="muted-text">Nenhum contrato criado para esta oportunidade.</p>
                  <button type="button" className="btn-primary" onClick={() => navigate(pipelineContext.contractNewPath(id))}>
                    Criar contrato
                  </button>
                </div>
              )}
            </section>
          </div>
        )}
      </div>
      </div>
      <Modal
        isOpen={isSubstituicaoContratoModalOpen}
        title="Substituir contrato"
        onClose={() => {
          if (loadingSubstituicaoContrato) return;
          setIsSubstituicaoContratoModalOpen(false);
          setSubstituicaoManterDados(null);
        }}
      >
        <p className="muted-text" style={{ marginTop: 0 }}>
          O contrato atual será <strong>inativado</strong> e deixará de estar vinculado a esta oportunidade. Em seguida você pode registrar um novo contrato.
        </p>
        <fieldset className="form-vertical" style={{ border: "none", margin: "12px 0 0", padding: 0 }}>
          <legend className="section-title">Deseja manter os dados do contrato?</legend>
          <label style={{ display: "flex", gap: 8, alignItems: "flex-start", cursor: "pointer" }}>
            <input
              type="radio"
              name="substituicaoCtrDados"
              checked={substituicaoManterDados === "manter"}
              onChange={() => setSubstituicaoManterDados("manter")}
              style={{ marginTop: 3 }}
            />
            <span>Sim — pré-preencher o novo formulário com contratante, objeto, valores e demais dados atuais (as cláusulas serão recriadas pelo modelo).</span>
          </label>
          <label style={{ display: "flex", gap: 8, alignItems: "flex-start", marginTop: 10, cursor: "pointer" }}>
            <input
              type="radio"
              name="substituicaoCtrDados"
              checked={substituicaoManterDados === "zerar"}
              onChange={() => setSubstituicaoManterDados("zerar")}
              style={{ marginTop: 3 }}
            />
            <span>Não — começar o fluxo novo com formulário limpo.</span>
          </label>
        </fieldset>
        <div className="modal-actions">
          <button type="button" disabled={loadingSubstituicaoContrato} onClick={() => setIsSubstituicaoContratoModalOpen(false)}>
            Cancelar
          </button>
          <button
            type="button"
            className="btn-primary"
            disabled={loadingSubstituicaoContrato || substituicaoManterDados === null}
            onClick={() => void confirmarSubstituicaoContrato()}
          >
            {loadingSubstituicaoContrato ? "Processando..." : "Confirmar"}
          </button>
        </div>
      </Modal>

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
      <Modal isOpen={isNovaPropostaModalOpen} title="Nova proposta" onClose={() => setIsNovaPropostaModalOpen(false)}>
        <form className="form-vertical" onSubmit={confirmarCriarProposta}>
          <label>
            Título
            <input
              value={novaPropostaForm.prpTitulo}
              onChange={(e) => setNovaPropostaForm((prev) => ({ ...prev, prpTitulo: e.target.value }))}
              required
            />
          </label>
          <label>
            Tipo da proposta
            <select
              value={novaPropostaForm.prpTipo}
              onChange={(e) =>
                setNovaPropostaForm((prev) => ({
                  ...prev,
                  prpTipo: e.target.value as "projeto" | "planos" | "hibrida",
                }))
              }
            >
              <option value="projeto">Projeto</option>
              <option value="planos">Planos</option>
              <option value="hibrida">Híbrida</option>
            </select>
          </label>
          <label>
            Iniciar a partir de template (opcional)
            <select
              value={novaPropostaForm.prpTplId}
              onChange={(e) =>
                setNovaPropostaForm((prev) => ({
                  ...prev,
                  prpTplId: e.target.value ? Number(e.target.value) : "",
                }))
              }
            >
              <option value="">Sem template (padrão do sistema)</option>
              {templates.map((t) => (
                <option key={t.ptlId} value={t.ptlId}>
                  {t.ptlNome} ({t.ptlTipoProposta})
                </option>
              ))}
            </select>
          </label>
          {novaPropostaForm.prpTplId !== "" ? (
            <p className="muted-text">A proposta será criada usando o snapshot completo do template selecionado.</p>
          ) : null}
          <div className="modal-actions">
            <button type="button" onClick={() => setIsNovaPropostaModalOpen(false)}>
              Cancelar
            </button>
            <button type="submit" className="btn-primary">
              Criar proposta
            </button>
          </div>
        </form>
      </Modal>
    </Layout>
  );
};

export default OportunidadeDetalhePage;
