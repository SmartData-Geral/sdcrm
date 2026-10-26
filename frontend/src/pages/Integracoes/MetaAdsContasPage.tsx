import React, { useEffect, useRef, useState } from "react";
import Layout from "../../components/Layout";
import ListingTableCard from "../../components/ListingTableCard";
import Loader from "../../components/Loader";
import Modal from "../../components/Modal";
import { useAuth } from "../../contexts/AuthContext";
import { dataBR } from "../Campanhas/metaAdsTipos";

interface Conta {
  macId: number;
  macNome: string;
  macContaExterna: string;
  macTokenFinal: string;
  macMoeda: string | null;
  macFuso: string | null;
  macStatus: string;
  macMensagem: string | null;
  macUltimaSync: string | null;
  macCargaInicialFeita: boolean;
  macAtivo: boolean;
  macExigirRastreio: boolean;
  origens: number[];
}

interface Origem {
  ccoId: number;
  ccoNome: string;
}

interface SyncLog {
  mslId: number;
  mslInicio: string;
  mslFim: string;
  mslOrigem: string;
  mslStatus: string;
  mslLinhas: number;
  mslLeadsVinculados: number;
  mslErro: string | null;
  mslDuracaoMs: number | null;
  mslDataExecucao: string;
}

const dataHora = (valor: string | null) => (valor ? new Date(valor).toLocaleString("pt-BR") : "—");

const STATUS: Record<string, { rotulo: string; classe: string }> = {
  pendente: { rotulo: "Aguardando sincronização", classe: "integracao-badge--warn" },
  sincronizando: { rotulo: "Sincronizando…", classe: "integracao-badge--warn" },
  ok: { rotulo: "OK", classe: "integracao-badge--ok" },
  aviso: { rotulo: "Aviso", classe: "integracao-badge--warn" },
  erro: { rotulo: "Erro", classe: "integracao-badge--danger" },
  token_invalido: { rotulo: "Token inválido", classe: "integracao-badge--danger" },
};

const badge = (status: string) => {
  const s = STATUS[status] ?? { rotulo: status, classe: "integracao-badge--warn" };
  return <span className={`integracao-badge ${s.classe}`}>{s.rotulo}</span>;
};

const FORM_VAZIO = { nome: "", conta: "", token: "", origens: [] as number[], exigirRastreio: false };

const MetaAdsContasPage: React.FC = () => {
  const { api } = useAuth();
  const [items, setItems] = useState<Conta[]>([]);
  const [origens, setOrigens] = useState<Origem[]>([]);
  const [loading, setLoading] = useState(false);
  const [salvando, setSalvando] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editando, setEditando] = useState<Conta | null>(null);
  const [form, setForm] = useState(FORM_VAZIO);
  const [erro, setErro] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const [logsDe, setLogsDe] = useState<Conta | null>(null);
  const [logs, setLogs] = useState<SyncLog[]>([]);
  const [logsCarregando, setLogsCarregando] = useState(false);
  const [periodoOpen, setPeriodoOpen] = useState(false);
  const [periodo, setPeriodo] = useState({ inicio: "", fim: "", macId: "" });
  const timerAviso = useRef<ReturnType<typeof setTimeout> | null>(null);

  const avisar = (texto: string) => {
    setAviso(texto);
    if (timerAviso.current) clearTimeout(timerAviso.current);
    timerAviso.current = setTimeout(() => setAviso(null), 7000);
  };

  const mensagemErro = (err: any, padrao: string) => {
    const detail = err?.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail) && detail[0]?.msg) return String(detail[0].msg).replace(/^Value error, /, "");
    return padrao;
  };

  const carregar = async () => {
    setLoading(true);
    try {
      const [lista, cco] = await Promise.allSettled([
        api.get<{ items: Conta[] }>("/meta-ads/contas"),
        api.get<{ items: Origem[] }>("/como-conheceu", { params: { status: "ativos", page_size: 100 } }),
      ]);
      if (lista.status === "fulfilled") {
        setItems(lista.value.data.items ?? []);
      } else {
        setItems([]);
        avisar(mensagemErro(lista.reason, "Não foi possível carregar as contas."));
      }
      if (cco.status === "fulfilled") {
        setOrigens((cco.value.data.items ?? []).sort((a, b) => a.ccoNome.localeCompare(b.ccoNome)));
      } else {
        setOrigens([]);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void carregar();
  }, []);

  const abrirNovo = () => {
    setEditando(null);
    setForm(FORM_VAZIO);
    setErro(null);
    setModalOpen(true);
  };

  const abrirEdicao = (row: Conta) => {
    setEditando(row);
    setForm({ nome: row.macNome, conta: row.macContaExterna, token: "", origens: row.origens, exigirRastreio: row.macExigirRastreio });
    setErro(null);
    setModalOpen(true);
  };

  const salvar = async (e: React.FormEvent) => {
    e.preventDefault();
    setSalvando(true);
    setErro(null);
    try {
      if (editando) {
        const corpo: Record<string, unknown> = { macNome: form.nome, origens: form.origens, macExigirRastreio: form.exigirRastreio };
        if (form.token.trim()) corpo.token = form.token;
        await api.put(`/meta-ads/contas/${editando.macId}`, corpo);
      } else {
        await api.post("/meta-ads/contas", {
          macNome: form.nome,
          macContaExterna: form.conta,
          token: form.token,
          origens: form.origens,
          macExigirRastreio: form.exigirRastreio,
        });
      }
      setModalOpen(false);
      await carregar();
    } catch (err: any) {
      setErro(mensagemErro(err, "Não foi possível salvar a conta."));
    } finally {
      setSalvando(false);
    }
  };

  const testar = async (row: Conta) => {
    try {
      const res = await api.post<{ ok: boolean; nome: string | null; moeda: string | null; fuso: string | null; mensagem: string | null }>(
        `/meta-ads/contas/${row.macId}/testar`
      );
      if (res.data.ok) {
        avisar(`Conexão OK: "${res.data.nome}" (${res.data.moeda ?? "?"}, ${res.data.fuso ?? "?"}).`);
      } else {
        avisar(`Falha na conexão: ${res.data.mensagem}`);
      }
    } catch (err: any) {
      avisar(mensagemErro(err, "Não foi possível testar a conexão."));
    }
    await carregar();
  };

  const sincronizar = async (row: Conta) => {
    try {
      await api.post(`/meta-ads/contas/${row.macId}/sincronizar`);
      avisar(`Sincronização de "${row.macNome}" iniciada. Atualize a página em alguns instantes.`);
    } catch (err: any) {
      avisar(mensagemErro(err, "Não foi possível iniciar a sincronização."));
    }
    await carregar();
  };

  const reprocessar = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post("/meta-ads/sincronizar-periodo", {
        data_inicial: periodo.inicio,
        data_final: periodo.fim,
        macId: periodo.macId ? Number(periodo.macId) : null,
      });
      setPeriodoOpen(false);
      avisar("Reprocessamento iniciado.");
      await carregar();
    } catch (err: any) {
      avisar(mensagemErro(err, "Não foi possível reprocessar o período."));
    }
  };

  const alternarAtivo = async (row: Conta) => {
    try {
      await api.put(`/meta-ads/contas/${row.macId}`, { macAtivo: !row.macAtivo });
    } catch (err: any) {
      avisar(mensagemErro(err, "Não foi possível alterar a conta."));
    }
    await carregar();
  };

  const verLogs = async (row: Conta) => {
    setLogsDe(row);
    setLogs([]);
    setLogsCarregando(true);
    try {
      const res = await api.get<{ items: SyncLog[] }>(`/meta-ads/contas/${row.macId}/logs`);
      setLogs(res.data.items ?? []);
    } catch (err: any) {
      setLogsDe(null);
      avisar(mensagemErro(err, "Não foi possível carregar o log."));
    } finally {
      setLogsCarregando(false);
    }
  };

  const fecharLogs = () => {
    setLogsDe(null);
    setLogs([]);
    setLogsCarregando(false);
  };

  const alternarOrigem = (id: number) =>
    setForm((f) => ({
      ...f,
      origens: f.origens.includes(id) ? f.origens.filter((o) => o !== id) : [...f.origens, id],
    }));

  const nomeOrigem = (id: number) => origens.find((o) => o.ccoId === id)?.ccoNome ?? `#${id}`;

  return (
    <Layout>
      <section className="surface-card details-card integracao-header">
        <div>
          <h2 className="section-title">Meta Ads</h2>
          <p className="muted-text">
            Conecte as contas de anúncio da empresa para ver investimento, custo por lead e retorno por campanha.
            A sincronização roda todo dia de madrugada e regrava os últimos 30 dias.
          </p>
        </div>
        <div className="integracao-acoes">
          <button type="button" onClick={() => setPeriodoOpen(true)} disabled={items.length === 0}>
            Reprocessar período
          </button>
          <button type="button" className="primary" onClick={abrirNovo}>
            Conectar conta
          </button>
        </div>
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
          <div className="datatable-empty">Nenhuma conta conectada. Veja docs/META_ADS.md para gerar o token.</div>
        ) : (
          <table className="datatable">
            <thead>
              <tr>
                <th>Conta</th>
                <th>Token</th>
                <th>Origens Meta</th>
                <th>Última sincronização</th>
                <th>Status</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {items.map((row) => (
                <tr key={row.macId}>
                  <td>
                    <strong>{row.macNome}</strong>
                    <div className="muted-text integracao-subtexto">
                      {row.macContaExterna}
                      {row.macMoeda ? ` · ${row.macMoeda}` : ""}
                    </div>
                  </td>
                  <td>
                    <code>••••{row.macTokenFinal}</code>
                  </td>
                  <td>
                    {row.origens.length === 0
                      ? "—"
                      : row.origens.map((id) => (
                          <code key={id} className="integracao-escopo">
                            {nomeOrigem(id)}
                          </code>
                        ))}
                  </td>
                  <td>{dataHora(row.macUltimaSync)}</td>
                  <td>
                    {row.macAtivo ? badge(row.macStatus) : <span className="integracao-badge integracao-badge--danger">Desativada</span>}
                    {row.macMensagem ? <div className="muted-text integracao-subtexto">{row.macMensagem}</div> : null}
                  </td>
                  <td className="integracao-acoes">
                    <button type="button" onClick={() => abrirEdicao(row)}>
                      Editar
                    </button>
                    <button type="button" onClick={() => void testar(row)}>
                      Testar conexão
                    </button>
                    <button type="button" onClick={() => void sincronizar(row)} disabled={!row.macAtivo}>
                      Sincronizar agora
                    </button>
                    <button type="button" onClick={() => void verLogs(row)}>
                      Log
                    </button>
                    <button type="button" onClick={() => void alternarAtivo(row)}>
                      {row.macAtivo ? "Desativar" : "Reativar"}
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
        title={editando ? `Editar: ${editando.macNome}` : "Conectar conta de anúncios"}
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
              placeholder="Ex.: Conta principal"
              required
              disabled={salvando}
            />
          </label>
          <label>
            ID da conta de anúncios
            <input
              value={form.conta}
              onChange={(e) => setForm((f) => ({ ...f, conta: e.target.value }))}
              placeholder="act_1234567890"
              required
              disabled={salvando || Boolean(editando)}
            />
          </label>
          <label>
            Token do System User
            <input
              type="password"
              autoComplete="off"
              value={form.token}
              onChange={(e) => setForm((f) => ({ ...f, token: e.target.value }))}
              placeholder={editando ? `Deixe vazio para manter ••••${editando.macTokenFinal}` : "EAAB…"}
              required={!editando}
              disabled={salvando}
            />
            <span className="field-hint">Precisa da permissão ads_read na conta. O token fica criptografado e não é exibido de novo.</span>
          </label>
          <fieldset className="integracao-escopos">
            <legend>Origens que contam como Meta Ads</legend>
            {origens.map((o) => (
              <label key={o.ccoId} className="checkbox-inline">
                <input
                  type="checkbox"
                  checked={form.origens.includes(o.ccoId)}
                  onChange={() => alternarOrigem(o.ccoId)}
                  disabled={salvando}
                />
                {o.ccoNome}
              </label>
            ))}
            <span className="field-hint">
              Leads dessas origens sem campanha identificada entram no total da conta, como "campanha não identificada".
            </span>
          </fieldset>
          <label className="checkbox-inline">
            <input
              type="checkbox"
              checked={form.exigirRastreio}
              onChange={(e) => setForm((f) => ({ ...f, exigirRastreio: e.target.checked }))}
              disabled={salvando}
            />
            Contar só leads com rastreio da Meta
          </label>
          <span className="field-hint">
            Leads de origem mapeada sem ID da Meta deixam de contar e vão para revisão.
          </span>
          <div className="modal-actions">
            <button type="button" onClick={() => setModalOpen(false)} disabled={salvando}>
              Cancelar
            </button>
            <button type="submit" className="primary" disabled={salvando || !form.nome.trim()}>
              {salvando ? "Salvando…" : "Salvar"}
            </button>
          </div>
        </form>
      </Modal>

      <Modal isOpen={periodoOpen} title="Reprocessar período" onClose={() => setPeriodoOpen(false)}>
        <form onSubmit={(e) => void reprocessar(e)}>
          <label>
            De
            <input type="date" value={periodo.inicio} onChange={(e) => setPeriodo((p) => ({ ...p, inicio: e.target.value }))} required />
          </label>
          <label>
            Até
            <input type="date" value={periodo.fim} onChange={(e) => setPeriodo((p) => ({ ...p, fim: e.target.value }))} required />
          </label>
          <label>
            Conta
            <select value={periodo.macId} onChange={(e) => setPeriodo((p) => ({ ...p, macId: e.target.value }))}>
              <option value="">Todas as contas ativas</option>
              {items.filter((c) => c.macAtivo).map((c) => (
                <option key={c.macId} value={c.macId}>
                  {c.macNome}
                </option>
              ))}
            </select>
            <span className="field-hint">Máximo de 366 dias.</span>
          </label>
          <div className="modal-actions">
            <button type="button" onClick={() => setPeriodoOpen(false)}>
              Cancelar
            </button>
            <button type="submit" className="primary">
              Reprocessar
            </button>
          </div>
        </form>
      </Modal>

      <Modal isOpen={Boolean(logsDe)} title={`Log: ${logsDe?.macNome ?? ""}`} onClose={fecharLogs}>
        {logsCarregando ? (
          <Loader />
        ) : logs.length === 0 ? (
          <p className="muted-text">Nenhuma sincronização registrada ainda.</p>
        ) : (
          <table className="datatable">
            <thead>
              <tr>
                <th>Quando</th>
                <th>Período</th>
                <th>Origem</th>
                <th>Status</th>
                <th>Linhas</th>
                <th>Leads ligados</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((l) => (
                <tr key={l.mslId}>
                  <td>{dataHora(l.mslDataExecucao)}</td>
                  <td>
                    {dataBR(l.mslInicio)} → {dataBR(l.mslFim)}
                  </td>
                  <td>{l.mslOrigem}</td>
                  <td>
                    {badge(l.mslStatus)}
                    {l.mslErro ? <div className="muted-text integracao-subtexto">{l.mslErro}</div> : null}
                  </td>
                  <td>{l.mslLinhas}</td>
                  <td>{l.mslLeadsVinculados}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Modal>
    </Layout>
  );
};

export default MetaAdsContasPage;
