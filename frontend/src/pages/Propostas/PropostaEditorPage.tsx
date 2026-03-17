import React, { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import Layout from "../../components/Layout";
import Loader from "../../components/Loader";
import ProposalEditor from "../../components/propostas/ProposalEditor";
import ProposalPublicPage from "../../components/propostas/ProposalPublicPage";
import {
  PropostaEventoItem,
  PropostaItem,
  PropostaTemplateItem,
  PropostaVersaoItem,
} from "../../components/propostas/types";
import { ToastContainer, ToastType } from "../../components/Toast";
import { useAuth } from "../../contexts/AuthContext";
import { getPublicProposalUrl } from "../../utils/api";

interface UsuarioResumo {
  usuId: number;
  usuNome: string;
  usuWhatsapp?: string | null;
}

interface OportunidadeResumo {
  opoId: number;
  opoUsuResponsavelId: number | null;
}

const PropostaEditorPage: React.FC = () => {
  const { prpId } = useParams<{ prpId: string }>();
  const navigate = useNavigate();
  const { api, user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [proposta, setProposta] = useState<PropostaItem | null>(null);
  const [oportunidade, setOportunidade] = useState<OportunidadeResumo | null>(null);
  const [templates, setTemplates] = useState<PropostaTemplateItem[]>([]);
  const [usuarios, setUsuarios] = useState<UsuarioResumo[]>([]);
  const [versoes, setVersoes] = useState<PropostaVersaoItem[]>([]);
  const [eventos, setEventos] = useState<PropostaEventoItem[]>([]);
  const [erroLoad, setErroLoad] = useState<string | null>(null);
  const [toasts, setToasts] = useState<Array<{ id: string; message: string; type?: ToastType }>>([]);

  const addToast = useCallback((message: string, type?: ToastType) => {
    const id = `toast-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    setToasts((prev) => [...prev, { id, message, type }]);
  }, []);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const id = prpId ? Number(prpId) : NaN;

  const load = async () => {
    if (!id || Number.isNaN(id)) return;
    setLoading(true);
    setErroLoad(null);
    try {
      const propostaRes = await api.get<PropostaItem>(`/propostas/${id}`);
      const propostaData = propostaRes.data;
      setProposta(propostaData);

      const [templateRes, usuarioRes, versaoRes, eventoRes, oportunidadeRes] = await Promise.allSettled([
        api.get<{ items: PropostaTemplateItem[] }>("/templates-proposta", { params: { page_size: 200 } }),
        api.get<{ items: UsuarioResumo[] }>("/usuarios", { params: { page_size: 100, status: "ativos" } }),
        api.get<{ items: PropostaVersaoItem[] }>(`/propostas/${id}/versoes`, { params: { page_size: 20 } }),
        api.get<{ items: PropostaEventoItem[] }>(`/propostas/${id}/eventos`, { params: { page_size: 20 } }),
        api.get<OportunidadeResumo>(`/oportunidades/${propostaData.prpOpoId}`),
      ]);
      setTemplates(templateRes.status === "fulfilled" ? templateRes.value.data.items ?? [] : []);
      let usuList: UsuarioResumo[] = usuarioRes.status === "fulfilled" ? usuarioRes.value.data.items ?? [] : [];
      const opoData = oportunidadeRes.status === "fulfilled" ? oportunidadeRes.value.data : null;
      setOportunidade(opoData);
      if (usuList.length === 0 && user) {
        usuList = [{ usuId: user.usuId, usuNome: user.usuNome, usuWhatsapp: user.usuWhatsapp ?? null }];
      }
      const opoRespId = opoData?.opoUsuResponsavelId ?? null;
      if (opoRespId != null && !usuList.some((u) => u.usuId === opoRespId)) {
        usuList = [{ usuId: opoRespId, usuNome: "Responsável da oportunidade", usuWhatsapp: null }, ...usuList];
      }
      setUsuarios(usuList);
      setVersoes(versaoRes.status === "fulfilled" ? versaoRes.value.data.items ?? [] : []);
      setEventos(eventoRes.status === "fulfilled" ? eventoRes.value.data.items ?? [] : []);
    } catch {
      setProposta(null);
      setErroLoad("Não foi possível carregar a proposta selecionada.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, [id]);

  if (!id || Number.isNaN(id)) {
    return (
      <Layout>
        <p>Proposta inválida.</p>
      </Layout>
    );
  }

  if (loading || !proposta) {
    return (
      <Layout>
        {loading ? <Loader /> : <p>Proposta não encontrada.</p>}
        {!loading && erroLoad ? <p>{erroLoad}</p> : null}
      </Layout>
    );
  }

  const save = async (payload: Partial<PropostaItem>) => {
    try {
      await api.put(`/propostas/${id}`, payload);
      await load();
      addToast("Proposta salva com sucesso", "success");
    } catch {
      addToast("Erro ao salvar. Tente novamente.", "error");
    }
  };

  const publish = async () => {
    try {
      await api.patch(`/propostas/${id}/publicar`, { forcar_nova_versao: true });
      await load();
      addToast("Proposta publicada com sucesso", "success");
    } catch {
      addToast("Erro ao publicar. Tente novamente.", "error");
    }
  };

  const saveAsTemplate = async (payload: {
    ptlNome: string;
    ptlTipoSolucao: string | null;
    ptlTipoProposta: "projeto" | "planos" | "hibrida";
    ptlAtivo: boolean;
    ptlPadrao: boolean;
  }) => {
    try {
      await api.post(`/propostas/${id}/salvar-template`, payload);
      addToast("Template salvo com sucesso", "success");
    } catch {
      addToast("Erro ao salvar template. Tente novamente.", "error");
    }
  };

  const copyLink = async () => {
    const link = getPublicProposalUrl(proposta.prpTokenPublico);
    try {
      await navigator.clipboard.writeText(link);
      addToast("Link copiado", "success");
    } catch {
      addToast("Não foi possível copiar o link", "warning");
    }
  };

  const responsavelNome =
    proposta.prpUsuResponsavelId != null
      ? usuarios.find((u) => u.usuId === proposta.prpUsuResponsavelId)?.usuNome ?? "—"
      : "—";

  const templateNome =
    proposta.prpTplId != null
      ? templates.find((t) => t.ptlId === proposta.prpTplId)?.ptlNome ?? "—"
      : "Sem template";

  const tipoLabel =
    proposta.prpTipo === "projeto"
      ? "Projeto"
      : proposta.prpTipo === "planos"
        ? "Planos"
        : proposta.prpTipo === "hibrida"
          ? "Híbrida"
          : String(proposta.prpTipo);

  const statusBadgeClass =
    /rascunho|draft/i.test(proposta.prpStatus)
      ? "status-badge--rascunho"
      : /publicad/i.test(proposta.prpStatus)
        ? "status-badge--publicada"
        : /visualizad/i.test(proposta.prpStatus)
          ? "status-badge--visualizada"
          : /aceit/i.test(proposta.prpStatus)
            ? "status-badge--aceita"
            : /arquivad/i.test(proposta.prpStatus)
              ? "status-badge--arquivada"
              : "status-badge--default";

  return (
    <Layout>
      <div className="page-header page-header--wrap">
        <div className="page-header-main">
          <button type="button" className="btn-link" style={{ padding: 0, marginBottom: "0.25rem" }} onClick={() => navigate(`/oportunidades/${proposta.prpOpoId}`)}>
            ← Voltar para oportunidade
          </button>
          <h2>{proposta.prpTitulo}</h2>
          <p className="muted-text">Editor interno de proposta</p>
        </div>
      </div>

      <div className="proposal-context-bar surface-card">
        <div className="proposal-context-grid">
          <div className="proposal-context-item">
            <span className="proposal-context-label">Proposta</span>
            <span className="proposal-context-value">{proposta.prpTitulo}</span>
          </div>
          <div className="proposal-context-item">
            <span className="proposal-context-label">Cliente / Contato</span>
            <span className="proposal-context-value">{proposta.prpNomeContato || "—"}</span>
          </div>
          <div className="proposal-context-item">
            <span className="proposal-context-label">Responsável</span>
            <span className="proposal-context-value">{responsavelNome}</span>
          </div>
          <div className="proposal-context-item">
            <span className="proposal-context-label">Status</span>
            <span className={`proposal-context-value status-badge ${statusBadgeClass}`}>{proposta.prpStatus}</span>
          </div>
          <div className="proposal-context-item">
            <span className="proposal-context-label">Tipo</span>
            <span className="proposal-context-value">{tipoLabel}</span>
          </div>
          <div className="proposal-context-item">
            <span className="proposal-context-label">Template</span>
            <span className="proposal-context-value">{templateNome}</span>
          </div>
        </div>
      </div>

      <ProposalEditor
        proposta={proposta}
        templates={templates}
        usuarios={usuarios}
        versoes={versoes}
        eventos={eventos}
        responsavelOportunidadeId={oportunidade?.opoUsuResponsavelId ?? null}
        onSave={save}
        onPublish={publish}
        onSaveAsTemplate={saveAsTemplate}
        onCopyLink={copyLink}
      />

      <ToastContainer toasts={toasts} removeToast={removeToast} />
    </Layout>
  );
};

export default PropostaEditorPage;

