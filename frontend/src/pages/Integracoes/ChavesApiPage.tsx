import React, { useEffect, useState } from "react";
import ConfirmDialog from "../../components/ConfirmDialog";
import Layout from "../../components/Layout";
import ListingTableCard from "../../components/ListingTableCard";
import Loader from "../../components/Loader";
import Modal from "../../components/Modal";
import RevealSecretModal from "../../components/RevealSecretModal";
import { useAuth } from "../../contexts/AuthContext";

interface Chave {
  ichId: number;
  ichNome: string;
  ichDescricao: string | null;
  ichPrefixo: string;
  ichEscopos: string;
  ichUltimoUsoEm: string | null;
  ichRevogadaEm: string | null;
  ichAtivo: boolean;
  ichDataCriacao: string;
}

const dataHora = (valor: string | null) => (valor ? new Date(valor).toLocaleString("pt-BR") : "—");

const ChavesApiPage: React.FC = () => {
  const { api } = useAuth();
  const [items, setItems] = useState<Chave[]>([]);
  const [escoposDisponiveis, setEscoposDisponiveis] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [salvando, setSalvando] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [novaChave, setNovaChave] = useState<string | null>(null);
  const [revogar, setRevogar] = useState<Chave | null>(null);
  const [form, setForm] = useState({ nome: "", descricao: "", escopos: ["leads:write"] });

  const carregar = async () => {
    setLoading(true);
    try {
      const [lista, catalogo] = await Promise.all([
        api.get<{ items: Chave[] }>("/integracao-chaves"),
        api.get<{ escopos: string[] }>("/integracao-chaves/escopos"),
      ]);
      setItems(lista.data.items ?? []);
      setEscoposDisponiveis(catalogo.data.escopos ?? []);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void carregar();
  }, []);

  const criar = async (e: React.FormEvent) => {
    e.preventDefault();
    setSalvando(true);
    setErro(null);
    try {
      const res = await api.post<{ apiKey: string }>("/integracao-chaves", {
        ichNome: form.nome,
        ichDescricao: form.descricao || null,
        escopos: form.escopos,
      });
      setModalOpen(false);
      setForm({ nome: "", descricao: "", escopos: ["leads:write"] });
      setNovaChave(res.data.apiKey);
      await carregar();
    } catch (err: any) {
      setErro(err?.response?.data?.detail ?? "Não foi possível criar a chave.");
    } finally {
      setSalvando(false);
    }
  };

  const confirmarRevogacao = async () => {
    if (!revogar) return;
    await api.post(`/integracao-chaves/${revogar.ichId}/revogar`);
    setRevogar(null);
    await carregar();
  };

  const alternarEscopo = (escopo: string) =>
    setForm((f) => ({
      ...f,
      escopos: f.escopos.includes(escopo)
        ? f.escopos.filter((item) => item !== escopo)
        : [...f.escopos, escopo],
    }));

  return (
    <Layout>
      <section className="surface-card details-card integracao-header">
        <div>
          <h2 className="section-title">Chaves de API</h2>
          <p className="muted-text">
            Uma chave por integração, vinculada a esta empresa. O valor completo aparece uma única vez, na
            criação — o sistema guarda apenas um hash. A revogação tem efeito imediato.
          </p>
        </div>
        <button type="button" className="primary" onClick={() => setModalOpen(true)}>
          Nova chave
        </button>
      </section>

      <ListingTableCard>
        {loading ? (
          <Loader />
        ) : items.length === 0 ? (
          <div className="datatable-empty">
            Nenhuma chave criada ainda. Crie uma para conectar o Zapier ao CRM.
          </div>
        ) : (
          <table className="datatable">
            <thead>
              <tr>
                <th>Integração</th>
                <th>Prefixo</th>
                <th>Escopos</th>
                <th>Último uso</th>
                <th>Status</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {items.map((row) => (
                <tr key={row.ichId}>
                  <td>
                    <strong>{row.ichNome}</strong>
                    {row.ichDescricao ? (
                      <div className="muted-text integracao-subtexto">{row.ichDescricao}</div>
                    ) : null}
                  </td>
                  <td>
                    <code>{row.ichPrefixo}…</code>
                  </td>
                  <td>
                    {row.ichEscopos.split(",").map((escopo) => (
                      <code key={escopo} className="integracao-escopo">
                        {escopo}
                      </code>
                    ))}
                  </td>
                  <td>{dataHora(row.ichUltimoUsoEm)}</td>
                  <td>
                    {row.ichRevogadaEm ? (
                      <span className="integracao-badge integracao-badge--danger">Revogada</span>
                    ) : row.ichAtivo ? (
                      <span className="integracao-badge integracao-badge--ok">Ativa</span>
                    ) : (
                      <span className="integracao-badge">Inativa</span>
                    )}
                  </td>
                  <td>
                    {row.ichAtivo ? (
                      <button type="button" className="danger" onClick={() => setRevogar(row)}>
                        Revogar
                      </button>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </ListingTableCard>

      <Modal isOpen={modalOpen} title="Nova chave de API" onClose={() => !salvando && setModalOpen(false)}>
        <form onSubmit={(e) => void criar(e)}>
          {erro ? (
            <div className="integracao-erro" role="alert">
              {erro}
            </div>
          ) : null}
          <label>
            Nome da integração
            <input
              value={form.nome}
              onChange={(e) => setForm((f) => ({ ...f, nome: e.target.value }))}
              placeholder="Ex.: Zapier — Planilha de Leads"
              required
              minLength={2}
              disabled={salvando}
            />
          </label>
          <label>
            Descrição (opcional)
            <input
              value={form.descricao}
              onChange={(e) => setForm((f) => ({ ...f, descricao: e.target.value }))}
              disabled={salvando}
            />
          </label>
          <fieldset className="integracao-escopos">
            <legend>Escopos</legend>
            {escoposDisponiveis.map((escopo) => (
              <label key={escopo} className="checkbox-inline">
                <input
                  type="checkbox"
                  checked={form.escopos.includes(escopo)}
                  onChange={() => alternarEscopo(escopo)}
                  disabled={salvando}
                />
                <code>{escopo}</code>
              </label>
            ))}
            <span className="field-hint">
              Para o Zap de entrada de leads, <code>leads:write</code> basta.
            </span>
          </fieldset>
          <div className="modal-actions">
            <button type="button" onClick={() => setModalOpen(false)} disabled={salvando}>
              Cancelar
            </button>
            <button type="submit" className="primary" disabled={salvando || !form.nome.trim()}>
              {salvando ? "Criando…" : "Criar chave"}
            </button>
          </div>
        </form>
      </Modal>

      <RevealSecretModal
        isOpen={Boolean(novaChave)}
        title="Chave de API criada"
        secret={novaChave ?? ""}
        description="Cole esta chave no header X-API-Key do Zapier. O sistema guarda apenas um hash — se você perder o valor, será preciso revogar e emitir outra."
        onClose={() => setNovaChave(null)}
      />

      <ConfirmDialog
        isOpen={Boolean(revogar)}
        title="Revogar chave"
        message={`A integração "${revogar?.ichNome ?? ""}" deixará de funcionar imediatamente. Esta ação não pode ser desfeita.`}
        onConfirm={() => void confirmarRevogacao()}
        onCancel={() => setRevogar(null)}
      />
    </Layout>
  );
};

export default ChavesApiPage;
