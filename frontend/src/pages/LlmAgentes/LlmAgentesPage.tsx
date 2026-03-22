import React, { useEffect, useState } from "react";
import Layout from "../../components/Layout";
import Loader from "../../components/Loader";
import Modal from "../../components/Modal";
import ListingTableCard from "../../components/ListingTableCard";
import { useAuth } from "../../contexts/AuthContext";

interface LlmAgenteItem {
  agnId: number;
  agnCodigo: string;
  agnNome: string;
  agnDescricao: string | null;
  agnSystemPrompt: string;
  agnLlmProvider: string;
  agnLlmModel: string | null;
  agnRespostaJsonEstruturada: boolean;
  agnAvisoEstrutura: string | null;
  aviso_estrutura_exibicao: string | null;
}

interface ListResponse {
  items: LlmAgenteItem[];
  total: number;
}

const LlmAgentesPage: React.FC = () => {
  const { api } = useAuth();
  const [items, setItems] = useState<LlmAgenteItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState<LlmAgenteItem | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    agnSystemPrompt: "",
    agnLlmProvider: "openai",
    agnLlmModel: "",
  });

  const load = async () => {
    setLoading(true);
    try {
      const res = await api.get<ListResponse>("/llm-agentes");
      setItems(res.data.items ?? []);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const openEdit = (row: LlmAgenteItem) => {
    setSelected(row);
    setForm({
      agnSystemPrompt: row.agnSystemPrompt,
      agnLlmProvider: row.agnLlmProvider || "openai",
      agnLlmModel: row.agnLlmModel ?? "",
    });
    setModalOpen(true);
  };

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selected) return;
    setSaving(true);
    try {
      await api.put(`/llm-agentes/${selected.agnId}`, {
        agnSystemPrompt: form.agnSystemPrompt,
        agnLlmProvider: form.agnLlmProvider,
        agnLlmModel: form.agnLlmModel.trim() || null,
      });
      setModalOpen(false);
      await load();
    } finally {
      setSaving(false);
    }
  };

  return (
    <Layout>
      <section className="surface-card details-card" style={{ marginBottom: "1rem" }}>
        <h2 className="section-title">Agentes de IA</h2>
        <p className="muted-text">
          Edite o prompt de sistema, o provider e o modelo usados por cada fluxo. Não é possível criar novos agentes por
          este cadastro — apenas ajustar os registros padrão do sistema.
        </p>
      </section>
      <ListingTableCard>
        {loading ? (
          <Loader />
        ) : (
          <div className="table-responsive">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Nome</th>
                  <th>Código interno</th>
                  <th>Provider</th>
                  <th>Modelo</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {items.map((row) => (
                  <tr key={row.agnId}>
                    <td>
                      <strong>{row.agnNome}</strong>
                      {row.agnDescricao ? (
                        <div className="muted-text" style={{ fontSize: "0.85rem", marginTop: "0.25rem" }}>
                          {row.agnDescricao}
                        </div>
                      ) : null}
                    </td>
                    <td>
                      <code>{row.agnCodigo}</code>
                    </td>
                    <td>{row.agnLlmProvider}</td>
                    <td>{row.agnLlmModel || "(padrão .env)"}</td>
                    <td>
                      <button type="button" className="btn-secondary" onClick={() => openEdit(row)}>
                        Editar
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {items.length === 0 ? <p className="muted-text">Nenhum agente listado.</p> : null}
          </div>
        )}
      </ListingTableCard>

      <Modal
        isOpen={modalOpen}
        title={selected ? `Editar: ${selected.agnNome}` : "Agente"}
        onClose={() => !saving && setModalOpen(false)}
      >
        {selected ? (
          <form className="llm-agente-form" onSubmit={(e) => void save(e)}>
            {selected.agnRespostaJsonEstruturada && selected.aviso_estrutura_exibicao ? (
              <div className="llm-agente-estrutura-banner" role="status">
                <strong>Resposta JSON estruturada</strong>
                <p>{selected.aviso_estrutura_exibicao}</p>
              </div>
            ) : null}

            <label>
              LLM Provider
              <select
                value={form.agnLlmProvider}
                onChange={(e) => setForm((f) => ({ ...f, agnLlmProvider: e.target.value }))}
                disabled={saving}
              >
                <option value="openai">openai</option>
              </select>
              <span className="field-hint">Por enquanto apenas OpenAI está habilitada no backend.</span>
            </label>

            <label>
              Modelo (opcional)
              <input
                value={form.agnLlmModel}
                onChange={(e) => setForm((f) => ({ ...f, agnLlmModel: e.target.value }))}
                placeholder="Ex.: gpt-4o-mini — vazio usa LLM_OPENAI_MODEL do .env"
                disabled={saving}
              />
            </label>

            <label>
              System prompt
              <textarea
                rows={16}
                value={form.agnSystemPrompt}
                onChange={(e) => setForm((f) => ({ ...f, agnSystemPrompt: e.target.value }))}
                disabled={saving}
                className="llm-agente-prompt-textarea"
              />
            </label>

            <div className="modal-actions">
              <button type="button" className="btn-secondary" onClick={() => setModalOpen(false)} disabled={saving}>
                Cancelar
              </button>
              <button type="submit" className="btn-primary" disabled={saving}>
                {saving ? "Salvando…" : "Salvar"}
              </button>
            </div>
          </form>
        ) : null}
      </Modal>
    </Layout>
  );
};

export default LlmAgentesPage;
