import React, { useEffect, useState } from "react";
import Layout from "../../components/Layout";
import Loader from "../../components/Loader";
import Modal from "../../components/Modal";
import ActionIconButton from "../../components/ActionIconButton";
import ListingToolbar from "../../components/ListingToolbar";
import ListingTableCard from "../../components/ListingTableCard";
import { DataTable } from "../../components/DataTable";
import { useAuth } from "../../contexts/AuthContext";
import { PropostaTemplateItem, TipoProposta } from "../../components/propostas/types";

interface TemplateListResponse {
  items: PropostaTemplateItem[];
}

const PropostasCadastrosPage: React.FC = () => {
  const { api } = useAuth();
  const [loading, setLoading] = useState(false);
  const [templates, setTemplates] = useState<PropostaTemplateItem[]>([]);
  const [isTemplateModalOpen, setIsTemplateModalOpen] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState<PropostaTemplateItem | null>(null);
  const [templateForm, setTemplateForm] = useState({
    ptlNome: "",
    ptlTipoSolucao: "",
    ptlTipoProposta: "projeto" as TipoProposta,
    ptlAtivo: true,
    ptlPadrao: false,
  });

  const load = async () => {
    setLoading(true);
    try {
      const templateRes = await api.get<TemplateListResponse>("/templates-proposta", { params: { page_size: 200 } });
      setTemplates(templateRes.data.items ?? []);
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
      ptlAtivo: true,
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
      ptlAtivo: item.ptlAtivo,
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
      ptlAtivo: templateForm.ptlAtivo,
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

  return (
    <Layout>
      <ListingToolbar
        actions={
          <button type="button" className="btn-primary" onClick={openCreateTemplate}>
            Novo template de proposta
          </button>
        }
        filters={
          <p className="muted-text">Templates baseados em snapshot de proposta modelo.</p>
        }
      />

      {loading ? (
        <Loader />
      ) : (
        <ListingTableCard>
          <DataTable
            keyField="ptlId"
            data={templates}
            columns={[
              { key: "ptlNome", header: "Nome" },
              { key: "ptlTipoSolucao", header: "Produto / Solução", render: (r) => r.ptlTipoSolucao ?? "-" },
              { key: "ptlTipoProposta", header: "Tipo proposta" },
              { key: "ptlPrpOrigemId", header: "Origem", render: (r) => (r.ptlPrpOrigemId ? `#${r.ptlPrpOrigemId}` : "-") },
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
                key: "ptlDataCriacao",
                header: "Data",
                render: (r) => {
                  const raw = r.ptlDataCriacao;
                  if (!raw) return "-";
                  return new Date(raw).toLocaleDateString("pt-BR");
                },
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
              checked={templateForm.ptlAtivo}
              onChange={(e) => setTemplateForm((f) => ({ ...f, ptlAtivo: e.target.checked }))}
            />
            Ativo
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
    </Layout>
  );
};

export default PropostasCadastrosPage;

