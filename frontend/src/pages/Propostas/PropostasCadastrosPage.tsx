import React, { useEffect, useState } from "react";
import Layout from "../../components/Layout";
import Loader from "../../components/Loader";
import Modal from "../../components/Modal";
import ActionIconButton from "../../components/ActionIconButton";
import ListingToolbar from "../../components/ListingToolbar";
import ListingTableCard from "../../components/ListingTableCard";
import { DataTable } from "../../components/DataTable";
import { useAuth } from "../../contexts/AuthContext";
import { PropostaBlocoPadraoItem, PropostaTemplateItem, TipoProposta } from "../../components/propostas/types";

interface TemplateListResponse {
  items: PropostaTemplateItem[];
}

interface BlocoPadraoListResponse {
  items: PropostaBlocoPadraoItem[];
}

type AbaCadastro = "templates" | "blocos";

const PropostasCadastrosPage: React.FC = () => {
  const { api } = useAuth();
  const [aba, setAba] = useState<AbaCadastro>("templates");
  const [loading, setLoading] = useState(false);
  const [templates, setTemplates] = useState<PropostaTemplateItem[]>([]);
  const [blocosPadrao, setBlocosPadrao] = useState<PropostaBlocoPadraoItem[]>([]);
  const [isTemplateModalOpen, setIsTemplateModalOpen] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState<PropostaTemplateItem | null>(null);
  const [templateForm, setTemplateForm] = useState({
    ptlNome: "",
    ptlTipoSolucao: "",
    ptlTipoProposta: "projeto" as TipoProposta,
    ptlPadrao: false,
  });
  const [isBlocoModalOpen, setIsBlocoModalOpen] = useState(false);
  const [selectedBloco, setSelectedBloco] = useState<PropostaBlocoPadraoItem | null>(null);
  const [blocoForm, setBlocoForm] = useState({
    pbpPtlId: "" as number | "",
    pbpTipo: "hero",
    pbpTitulo: "",
    pbpSubtitulo: "",
    pbpOrdem: 0,
    pbpVisivel: true,
    pbpDadosJsonTexto: "{}",
  });

  const load = async () => {
    setLoading(true);
    try {
      const [templateRes, blocoRes] = await Promise.all([
        api.get<TemplateListResponse>("/templates-proposta", { params: { page_size: 200 } }),
        api.get<BlocoPadraoListResponse>("/cadastros-proposta/blocos-padrao", { params: { page_size: 300 } }),
      ]);
      setTemplates(templateRes.data.items ?? []);
      setBlocosPadrao(blocoRes.data.items ?? []);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const openCreateTemplate = () => {
    setSelectedTemplate(null);
    setTemplateForm({
      ptlNome: "",
      ptlTipoSolucao: "",
      ptlTipoProposta: "projeto",
      ptlPadrao: false,
    });
    setIsTemplateModalOpen(true);
  };

  const openEditTemplate = (item: PropostaTemplateItem) => {
    setSelectedTemplate(item);
    setTemplateForm({
      ptlNome: item.ptlNome,
      ptlTipoSolucao: item.ptlTipoSolucao ?? "",
      ptlTipoProposta: item.ptlTipoProposta,
      ptlPadrao: item.ptlPadrao,
    });
    setIsTemplateModalOpen(true);
  };

  const saveTemplate = async (e: React.FormEvent) => {
    e.preventDefault();
    const payload = {
      ptlNome: templateForm.ptlNome,
      ptlTipoSolucao: templateForm.ptlTipoSolucao || null,
      ptlTipoProposta: templateForm.ptlTipoProposta,
      ptlPadrao: templateForm.ptlPadrao,
    };
    if (selectedTemplate) {
      await api.put(`/templates-proposta/${selectedTemplate.ptlId}`, payload);
    } else {
      await api.post("/templates-proposta", payload);
    }
    setIsTemplateModalOpen(false);
    await load();
  };

  const toggleTemplateAtivo = async (item: PropostaTemplateItem) => {
    if (item.ptlAtivo) {
      await api.patch(`/templates-proposta/${item.ptlId}/inativar`);
    } else {
      await api.patch(`/templates-proposta/${item.ptlId}/ativar`);
    }
    await load();
  };

  const openCreateBloco = () => {
    setSelectedBloco(null);
    setBlocoForm({
      pbpPtlId: "",
      pbpTipo: "hero",
      pbpTitulo: "",
      pbpSubtitulo: "",
      pbpOrdem: 0,
      pbpVisivel: true,
      pbpDadosJsonTexto: "{}",
    });
    setIsBlocoModalOpen(true);
  };

  const openEditBloco = (item: PropostaBlocoPadraoItem) => {
    setSelectedBloco(item);
    setBlocoForm({
      pbpPtlId: item.pbpPtlId ?? "",
      pbpTipo: item.pbpTipo,
      pbpTitulo: item.pbpTitulo ?? "",
      pbpSubtitulo: item.pbpSubtitulo ?? "",
      pbpOrdem: item.pbpOrdem,
      pbpVisivel: item.pbpVisivel,
      pbpDadosJsonTexto: JSON.stringify(item.pbpDadosJson ?? {}, null, 2),
    });
    setIsBlocoModalOpen(true);
  };

  const saveBloco = async (e: React.FormEvent) => {
    e.preventDefault();
    let dadosJson: Record<string, unknown> | null = null;
    try {
      dadosJson = blocoForm.pbpDadosJsonTexto.trim() ? JSON.parse(blocoForm.pbpDadosJsonTexto) : null;
    } catch {
      alert("JSON inválido em Dados do bloco.");
      return;
    }
    const payload = {
      pbpPtlId: blocoForm.pbpPtlId === "" ? null : blocoForm.pbpPtlId,
      pbpTipo: blocoForm.pbpTipo,
      pbpTitulo: blocoForm.pbpTitulo || null,
      pbpSubtitulo: blocoForm.pbpSubtitulo || null,
      pbpOrdem: Number(blocoForm.pbpOrdem),
      pbpVisivel: blocoForm.pbpVisivel,
      pbpDadosJson: dadosJson,
    };
    if (selectedBloco) {
      await api.put(`/cadastros-proposta/blocos-padrao/${selectedBloco.pbpId}`, payload);
    } else {
      await api.post("/cadastros-proposta/blocos-padrao", payload);
    }
    setIsBlocoModalOpen(false);
    await load();
  };

  const toggleBlocoAtivo = async (item: PropostaBlocoPadraoItem) => {
    if (item.pbpAtivo) {
      await api.patch(`/cadastros-proposta/blocos-padrao/${item.pbpId}/inativar`);
    } else {
      await api.patch(`/cadastros-proposta/blocos-padrao/${item.pbpId}/ativar`);
    }
    await load();
  };

  return (
    <Layout>
      <div className="oportunidades-status-tabs" role="tablist" aria-label="Cadastros de propostas">
        <button type="button" role="tab" className={`oportunidades-status-tab ${aba === "templates" ? "is-active" : ""}`} onClick={() => setAba("templates")}>
          Templates
        </button>
        <button type="button" role="tab" className={`oportunidades-status-tab ${aba === "blocos" ? "is-active" : ""}`} onClick={() => setAba("blocos")}>
          Blocos padrão
        </button>
      </div>

      <ListingToolbar
        actions={
          aba === "templates" ? (
            <button type="button" className="btn-primary" onClick={openCreateTemplate}>
              Novo template de proposta
            </button>
          ) : (
            <button type="button" className="btn-primary" onClick={openCreateBloco}>
              Novo bloco padrão
            </button>
          )
        }
        filters={
          <p className="muted-text">
            {aba === "templates"
              ? "Cadastros base de templates da proposta (tipo/solução)."
              : "Cadastros base de blocos padrão para iniciar novas propostas."}
          </p>
        }
      />

      {loading ? (
        <Loader />
      ) : (
        <ListingTableCard>
          {aba === "templates" ? (
            <DataTable
              keyField="ptlId"
              data={templates}
              columns={[
                { key: "ptlNome", header: "Nome" },
                { key: "ptlTipoSolucao", header: "Tipo solução", render: (r) => r.ptlTipoSolucao ?? "-" },
                { key: "ptlTipoProposta", header: "Tipo proposta" },
                { key: "ptlPadrao", header: "Padrão", render: (r) => (r.ptlPadrao ? "Sim" : "Não") },
                {
                  key: "ptlAtivo",
                  header: "Status",
                  render: (r) => (
                    <span className={`status-badge ${r.ptlAtivo ? "status-badge--active" : "status-badge--inactive"}`}>
                      {r.ptlAtivo ? "Ativo" : "Inativo"}
                    </span>
                  ),
                },
                {
                  key: "ptlId",
                  header: "Ações",
                  render: (r) => (
                    <div className="actions">
                      <ActionIconButton icon="edit" label="Editar" onClick={() => openEditTemplate(r)} />
                      <ActionIconButton
                        icon={r.ptlAtivo ? "deactivate" : "activate"}
                        label={r.ptlAtivo ? "Inativar" : "Ativar"}
                        onClick={() => toggleTemplateAtivo(r)}
                      />
                    </div>
                  ),
                },
              ]}
            />
          ) : (
            <DataTable
              keyField="pbpId"
              data={blocosPadrao}
              columns={[
                { key: "pbpTipo", header: "Tipo bloco" },
                { key: "pbpTitulo", header: "Título", render: (r) => r.pbpTitulo ?? "-" },
                { key: "pbpPtlId", header: "Template", render: (r) => (r.pbpPtlId ? String(r.pbpPtlId) : "Global") },
                { key: "pbpOrdem", header: "Ordem" },
                {
                  key: "pbpAtivo",
                  header: "Status",
                  render: (r) => (
                    <span className={`status-badge ${r.pbpAtivo ? "status-badge--active" : "status-badge--inactive"}`}>
                      {r.pbpAtivo ? "Ativo" : "Inativo"}
                    </span>
                  ),
                },
                {
                  key: "pbpId",
                  header: "Ações",
                  render: (r) => (
                    <div className="actions">
                      <ActionIconButton icon="edit" label="Editar" onClick={() => openEditBloco(r)} />
                      <ActionIconButton
                        icon={r.pbpAtivo ? "deactivate" : "activate"}
                        label={r.pbpAtivo ? "Inativar" : "Ativar"}
                        onClick={() => toggleBlocoAtivo(r)}
                      />
                    </div>
                  ),
                },
              ]}
            />
          )}
        </ListingTableCard>
      )}

      <Modal
        isOpen={isTemplateModalOpen}
        title={selectedTemplate ? "Editar template de proposta" : "Novo template de proposta"}
        onClose={() => setIsTemplateModalOpen(false)}
      >
        <form className="form-vertical" onSubmit={saveTemplate}>
          <label>
            Nome
            <input value={templateForm.ptlNome} onChange={(e) => setTemplateForm((f) => ({ ...f, ptlNome: e.target.value }))} required />
          </label>
          <label>
            Tipo de solução
            <input
              value={templateForm.ptlTipoSolucao}
              onChange={(e) => setTemplateForm((f) => ({ ...f, ptlTipoSolucao: e.target.value }))}
              placeholder="Ex.: BI, Sistema, IA"
            />
          </label>
          <label>
            Tipo de proposta
            <select
              value={templateForm.ptlTipoProposta}
              onChange={(e) => setTemplateForm((f) => ({ ...f, ptlTipoProposta: e.target.value as TipoProposta }))}
            >
              <option value="projeto">Projeto</option>
              <option value="planos">Planos</option>
              <option value="hibrida">Híbrida</option>
            </select>
          </label>
          <label className="checkbox-inline">
            <input
              type="checkbox"
              checked={templateForm.ptlPadrao}
              onChange={(e) => setTemplateForm((f) => ({ ...f, ptlPadrao: e.target.checked }))}
            />
            Template padrão
          </label>
          <div className="modal-actions">
            <button type="button" onClick={() => setIsTemplateModalOpen(false)}>
              Cancelar
            </button>
            <button type="submit" className="btn-primary">
              Salvar
            </button>
          </div>
        </form>
      </Modal>

      <Modal
        isOpen={isBlocoModalOpen}
        title={selectedBloco ? "Editar bloco padrão" : "Novo bloco padrão"}
        onClose={() => setIsBlocoModalOpen(false)}
      >
        <form className="form-vertical" onSubmit={saveBloco}>
          <label>
            Tipo do bloco
            <input value={blocoForm.pbpTipo} onChange={(e) => setBlocoForm((f) => ({ ...f, pbpTipo: e.target.value }))} required />
          </label>
          <label>
            Título
            <input value={blocoForm.pbpTitulo} onChange={(e) => setBlocoForm((f) => ({ ...f, pbpTitulo: e.target.value }))} />
          </label>
          <label>
            Subtítulo
            <input value={blocoForm.pbpSubtitulo} onChange={(e) => setBlocoForm((f) => ({ ...f, pbpSubtitulo: e.target.value }))} />
          </label>
          <label>
            Template vinculado (opcional)
            <select
              value={blocoForm.pbpPtlId}
              onChange={(e) => setBlocoForm((f) => ({ ...f, pbpPtlId: e.target.value ? Number(e.target.value) : "" }))}
            >
              <option value="">Global (todos)</option>
              {templates.map((t) => (
                <option key={t.ptlId} value={t.ptlId}>
                  #{t.ptlId} - {t.ptlNome}
                </option>
              ))}
            </select>
          </label>
          <label>
            Ordem
            <input
              type="number"
              value={blocoForm.pbpOrdem}
              onChange={(e) => setBlocoForm((f) => ({ ...f, pbpOrdem: Number(e.target.value || 0) }))}
            />
          </label>
          <label className="checkbox-inline">
            <input
              type="checkbox"
              checked={blocoForm.pbpVisivel}
              onChange={(e) => setBlocoForm((f) => ({ ...f, pbpVisivel: e.target.checked }))}
            />
            Visível por padrão
          </label>
          <label>
            Dados do bloco (JSON)
            <textarea
              rows={8}
              value={blocoForm.pbpDadosJsonTexto}
              onChange={(e) => setBlocoForm((f) => ({ ...f, pbpDadosJsonTexto: e.target.value }))}
            />
          </label>
          <div className="modal-actions">
            <button type="button" onClick={() => setIsBlocoModalOpen(false)}>
              Cancelar
            </button>
            <button type="submit" className="btn-primary">
              Salvar
            </button>
          </div>
        </form>
      </Modal>
    </Layout>
  );
};

export default PropostasCadastrosPage;

