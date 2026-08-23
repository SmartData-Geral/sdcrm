import React, { useEffect, useState } from "react";
import Layout from "../../components/Layout";
import ListingTableCard from "../../components/ListingTableCard";
import Loader from "../../components/Loader";
import Modal from "../../components/Modal";
import RevealSecretModal from "../../components/RevealSecretModal";
import { useAuth } from "../../contexts/AuthContext";

interface EventoCatalogo {
  id: string;
  prioridade: string;
  rotulo: string;
  descricao: string;
  disponivel: boolean;
  motivo_indisponivel: string | null;
}

interface Assinatura {
  whaId: number;
  whaNome: string;
  whaUrl: string;
  whaEventosJson: string[];
  whaFalhasConsecutivas: number;
  whaDesativadaEm: string | null;
  whaDesativadaMotivo: string | null;
  whaUltimaEntregaEm: string | null;
  whaUltimoStatusHttp: number | null;
  whaAtivo: boolean;
}

interface Entrega {
  wenId: number;
  wenStatus: string;
  wenTentativas: number;
  wenProximaTentativaEm: string | null;
  wenUltimoStatusHttp: number | null;
  wenUltimoErro: string | null;
  wenRespostaTrecho: string | null;
  wenDuracaoMs: number | null;
  wenDataCriacao: string;
}

const dataHora = (valor: string | null) => (valor ? new Date(valor).toLocaleString("pt-BR") : "—");

const classeEntrega = (status: string) => {
  if (status === "entregue") return "integracao-badge integracao-badge--ok";
  if (status === "retentando" || status === "pendente") return "integracao-badge integracao-badge--warn";
  return "integracao-badge integracao-badge--danger";
};

const WebhooksPage: React.FC = () => {
  const { api } = useAuth();
  const [catalogo, setCatalogo] = useState<EventoCatalogo[]>([]);
  const [items, setItems] = useState<Assinatura[]>([]);
  const [loading, setLoading] = useState(false);
  const [salvando, setSalvando] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editando, setEditando] = useState<Assinatura | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [segredo, setSegredo] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const [entregasDe, setEntregasDe] = useState<Assinatura | null>(null);
  const [entregas, setEntregas] = useState<Entrega[]>([]);
  const [form, setForm] = useState({ nome: "", url: "", eventos: [] as string[] });

  const carregar = async () => {
    setLoading(true);
    try {
      const [lista, cat] = await Promise.all([
        api.get<{ items: Assinatura[] }>("/webhooks"),
        api.get<{ items: EventoCatalogo[] }>("/webhooks/eventos"),
      ]);
      setItems(lista.data.items ?? []);
      setCatalogo(cat.data.items ?? []);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void carregar();
  }, []);

  const abrirNovo = () => {
    setEditando(null);
    setForm({ nome: "", url: "", eventos: [] });
    setErro(null);
    setModalOpen(true);
  };

  const abrirEdicao = (row: Assinatura) => {
    setEditando(row);
    setForm({ nome: row.whaNome, url: row.whaUrl, eventos: row.whaEventosJson ?? [] });
    setErro(null);
    setModalOpen(true);
  };

  const salvar = async (e: React.FormEvent) => {
    e.preventDefault();
    setSalvando(true);
    setErro(null);
    try {
      if (editando) {
        await api.put(`/webhooks/${editando.whaId}`, {
          whaNome: form.nome,
          whaUrl: form.url,
          eventos: form.eventos,
        });
        setModalOpen(false);
      } else {
        const res = await api.post<{ segredo: string }>("/webhooks", {
          whaNome: form.nome,
          whaUrl: form.url,
          eventos: form.eventos,
        });
        setModalOpen(false);
        setSegredo(res.data.segredo);
      }
      await carregar();
    } catch (err: any) {
      setErro(err?.response?.data?.detail ?? "Não foi possível salvar a assinatura.");
    } finally {
      setSalvando(false);
    }
  };

  const testar = async (row: Assinatura) => {
    await api.post(`/webhooks/${row.whaId}/testar`);
    setAviso(`Evento de teste enfileirado para "${row.whaNome}". A entrega ocorre em até 10 segundos.`);
    setTimeout(() => setAviso(null), 6000);
  };

  const rotacionar = async (row: Assinatura) => {
    const res = await api.post<{ segredo: string }>(`/webhooks/${row.whaId}/rotacionar-segredo`);
    setSegredo(res.data.segredo);
  };

  const alternarAtivo = async (row: Assinatura) => {
    await api.put(`/webhooks/${row.whaId}`, { whaAtivo: !row.whaAtivo });
    await carregar();
  };

  const verEntregas = async (row: Assinatura) => {
    setEntregasDe(row);
    const res = await api.get<{ items: Entrega[] }>(`/webhooks/${row.whaId}/entregas`);
    setEntregas(res.data.items ?? []);
  };

  const reenviar = async (wenId: number) => {
    await api.post(`/webhooks/entregas/${wenId}/reenviar`);
    if (entregasDe) await verEntregas(entregasDe);
  };

  const alternarEvento = (id: string) =>
    setForm((f) => ({
      ...f,
      eventos: f.eventos.includes(id) ? f.eventos.filter((e) => e !== id) : [...f.eventos, id],
    }));

  return (
    <Layout>
      <section className="surface-card details-card integracao-header">
        <div>
          <h2 className="section-title">Webhooks de saída</h2>
          <p className="muted-text">
            O CRM avisa sistemas externos quando algo acontece. Cada entrega vai assinada com HMAC-SHA256 e é
            retentada com espera crescente (30s, 2min, 10min, 1h, 6h, 24h) em caso de erro transitório.
          </p>
        </div>
        <button type="button" className="primary" onClick={abrirNovo}>
          Nova assinatura
        </button>
      </section>

      {aviso ? (
        <div className="integracao-aviso" role="status">
          {aviso}
        </div>
      ) : null}

      <ListingTableCard>
        {loading ? (
          <Loader />
        ) : items.length === 0 ? (
          <div className="datatable-empty">
            Nenhuma assinatura. Crie uma apontando para um Catch Hook do Zapier.
          </div>
        ) : (
          <table className="datatable">
            <thead>
              <tr>
                <th>Nome</th>
                <th>Destino</th>
                <th>Eventos</th>
                <th>Última entrega</th>
                <th>Status</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {items.map((row) => (
                <tr key={row.whaId}>
                  <td>
                    <strong>{row.whaNome}</strong>
                    {row.whaDesativadaMotivo ? (
                      <div className="muted-text integracao-subtexto">{row.whaDesativadaMotivo}</div>
                    ) : null}
                  </td>
                  <td>
                    <code className="integracao-url">{row.whaUrl}</code>
                  </td>
                  <td>
                    {(row.whaEventosJson ?? []).map((evento) => (
                      <code key={evento} className="integracao-escopo">
                        {evento}
                      </code>
                    ))}
                  </td>
                  <td>
                    {dataHora(row.whaUltimaEntregaEm)}
                    {row.whaUltimoStatusHttp ? ` (${row.whaUltimoStatusHttp})` : ""}
                  </td>
                  <td>
                    {row.whaAtivo ? (
                      <span className="integracao-badge integracao-badge--ok">Ativa</span>
                    ) : (
                      <span className="integracao-badge integracao-badge--danger">Desativada</span>
                    )}
                    {row.whaFalhasConsecutivas > 0 ? (
                      <div className="muted-text integracao-subtexto">
                        {row.whaFalhasConsecutivas} falha(s) seguida(s)
                      </div>
                    ) : null}
                  </td>
                  <td className="integracao-acoes">
                    <button type="button" onClick={() => abrirEdicao(row)}>
                      Editar
                    </button>
                    <button type="button" onClick={() => void testar(row)}>
                      Testar
                    </button>
                    <button type="button" onClick={() => void verEntregas(row)}>
                      Entregas
                    </button>
                    <button type="button" onClick={() => void rotacionar(row)}>
                      Rotacionar segredo
                    </button>
                    <button type="button" onClick={() => void alternarAtivo(row)}>
                      {row.whaAtivo ? "Desativar" : "Reativar"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </ListingTableCard>

      <Modal
        isOpen={modalOpen}
        title={editando ? `Editar: ${editando.whaNome}` : "Nova assinatura"}
        onClose={() => !salvando && setModalOpen(false)}
      >
        <form onSubmit={(e) => void salvar(e)}>
          {erro ? (
            <div className="integracao-erro" role="alert">
              {erro}
            </div>
          ) : null}
          <label>
            Nome
            <input
              value={form.nome}
              onChange={(e) => setForm((f) => ({ ...f, nome: e.target.value }))}
              placeholder="Ex.: Zapier — Avisos no Slack"
              required
              disabled={salvando}
            />
          </label>
          <label>
            URL de destino
            <input
              value={form.url}
              onChange={(e) => setForm((f) => ({ ...f, url: e.target.value }))}
              placeholder="https://hooks.zapier.com/hooks/catch/000000/abcdef/"
              required
              disabled={salvando}
            />
            <span className="field-hint">
              Precisa ser https e apontar para um host público — endereços internos são recusados.
            </span>
          </label>
          <fieldset className="integracao-escopos">
            <legend>Eventos</legend>
            {catalogo.map((evento) => (
              <label
                key={evento.id}
                className={`checkbox-inline${evento.disponivel ? "" : " checkbox-inline--off"}`}
                title={evento.motivo_indisponivel ?? evento.descricao}
              >
                <input
                  type="checkbox"
                  checked={form.eventos.includes(evento.id)}
                  onChange={() => alternarEvento(evento.id)}
                  disabled={salvando || !evento.disponivel}
                />
                <code>{evento.id}</code>
                <span className="muted-text"> {evento.prioridade}</span>
                {!evento.disponivel ? (
                  <span className="muted-text integracao-subtexto">{evento.motivo_indisponivel}</span>
                ) : null}
              </label>
            ))}
            <span className="field-hint">Sem nenhum marcado, a assinatura recebe todos os disponíveis.</span>
          </fieldset>
          <div className="modal-actions">
            <button type="button" onClick={() => setModalOpen(false)} disabled={salvando}>
              Cancelar
            </button>
            <button
              type="submit"
              className="primary"
              disabled={salvando || !form.nome.trim() || !form.url.trim()}
            >
              {salvando ? "Salvando…" : "Salvar"}
            </button>
          </div>
        </form>
      </Modal>

      <Modal
        isOpen={Boolean(entregasDe)}
        title={`Entregas: ${entregasDe?.whaNome ?? ""}`}
        onClose={() => setEntregasDe(null)}
      >
        {entregas.length === 0 ? (
          <p className="muted-text">Nenhuma entrega registrada ainda.</p>
        ) : (
          <table className="datatable">
            <thead>
              <tr>
                <th>Quando</th>
                <th>Status</th>
                <th>Tent.</th>
                <th>HTTP</th>
                <th>Próxima</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {entregas.map((row) => (
                <tr key={row.wenId}>
                  <td>{dataHora(row.wenDataCriacao)}</td>
                  <td>
                    <span className={classeEntrega(row.wenStatus)}>{row.wenStatus}</span>
                    {row.wenUltimoErro ? (
                      <div className="muted-text integracao-subtexto">{row.wenUltimoErro}</div>
                    ) : null}
                  </td>
                  <td>{row.wenTentativas}</td>
                  <td>{row.wenUltimoStatusHttp ?? "—"}</td>
                  <td>{dataHora(row.wenProximaTentativaEm)}</td>
                  <td>
                    {row.wenStatus !== "entregue" ? (
                      <button type="button" onClick={() => void reenviar(row.wenId)}>
                        Reenviar
                      </button>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Modal>

      <RevealSecretModal
        isOpen={Boolean(segredo)}
        title="Segredo do webhook"
        secret={segredo ?? ""}
        description="Use este segredo para validar o header X-SDCRM-Signature no destino. Ele não pode ser recuperado depois — só rotacionado."
        onClose={() => setSegredo(null)}
      />
    </Layout>
  );
};

export default WebhooksPage;
