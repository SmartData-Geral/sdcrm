import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import Layout from "../../components/Layout";
import Loader from "../../components/Loader";
import { useAuth } from "../../contexts/AuthContext";
import ConfigMonitoramentoModal from "./ConfigMonitoramentoModal";
import {
  MetaAdsAlerta,
  ROTULO_ALERTA,
  ResumoDiario,
  ResumoDiarioItem,
  ResumoItem,
  dataBR,
  hojeISO,
  inteiro,
  mensagemErroApi,
  moeda,
  percentual,
} from "../Campanhas/metaAdsTipos";

const dataHora = (valor: string) => new Date(valor).toLocaleString("pt-BR");

const variacao = (v: number | null | undefined) =>
  v == null ? "sem base" : `${v > 0 ? "+" : ""}${v.toLocaleString("pt-BR", { maximumFractionDigits: 1 })}% vs. média do período`;

const leadDoAlerta = (a: MetaAdsAlerta): string | null => {
  if (a.malTipo !== "sem_contato") return null;
  const m = /^lead:(\d+)$/.exec(a.malChave);
  return m ? m[1] : null;
};

const TabelaRanking: React.FC<{ titulo: string; itens: ResumoItem[] }> = ({ titulo, itens }) => (
  <div>
    <h4>{titulo}</h4>
    {itens.length === 0 ? (
      <p className="muted-text">Nenhum anúncio atinge o gasto mínimo.</p>
    ) : (
      <div className="campanhas-tabela-scroll">
        <table className="dashboard-ranking-table campanhas-tabela">
          <thead>
            <tr>
              <th>Anúncio</th>
              <th>Gasto</th>
              <th>Leads Meta</th>
              <th>CPL</th>
              <th>MQLs</th>
              <th>Custo/MQL</th>
            </tr>
          </thead>
          <tbody>
            {itens.map((a) => (
              <tr key={a.id ?? a.nome}>
                <td className="campanhas-col-nome">{a.nome}</td>
                <td>{moeda(a.investimento)}</td>
                <td>{a.leadsMeta}</td>
                <td>{moeda(a.cpl)}</td>
                <td>{a.mqls}</td>
                <td>{moeda(a.custoMql)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    )}
  </div>
);

const MonitoramentoPage: React.FC = () => {
  const { api, user } = useAuth();
  const admin = Boolean(user?.usuAdmin);

  const [datas, setDatas] = useState<ResumoDiarioItem[]>([]);
  const [dataSel, setDataSel] = useState("");
  const [resumo, setResumo] = useState<ResumoDiario | null>(null);
  const [resumoCarregando, setResumoCarregando] = useState(false);
  const [resumoErro, setResumoErro] = useState<string | null>(null);
  const [gerando, setGerando] = useState(false);
  const [recarga, setRecarga] = useState(0);

  const [alertas, setAlertas] = useState<MetaAdsAlerta[]>([]);
  const [mostrarCientes, setMostrarCientes] = useState(false);
  const [alertasCarregando, setAlertasCarregando] = useState(false);
  const [alertasErro, setAlertasErro] = useState<string | null>(null);
  const [recargaAlertas, setRecargaAlertas] = useState(0);
  const [cienteEm, setCienteEm] = useState<number | null>(null);

  const [configAberta, setConfigAberta] = useState(false);

  useEffect(() => {
    let ativo = true;
    api
      .get<{ items: ResumoDiarioItem[] }>("/meta-ads/resumos", { params: { limite: 60 } })
      .then((r) => {
        if (ativo) setDatas(r.data.items ?? []);
      })
      .catch(() => {
        if (ativo) setDatas([]);
      });
    return () => {
      ativo = false;
    };
  }, [api, recarga]);

  useEffect(() => {
    let ativo = true;
    setResumoCarregando(true);
    setResumoErro(null);
    api
      .get<ResumoDiario>(`/meta-ads/resumos/${dataSel || "ultimo"}`)
      .then((r) => {
        if (ativo) setResumo(r.data);
      })
      .catch((err) => {
        if (!ativo) return;
        setResumo(null);
        if (err?.response?.status !== 404) setResumoErro(mensagemErroApi(err, "Não foi possível carregar o resumo."));
      })
      .finally(() => {
        if (ativo) setResumoCarregando(false);
      });
    return () => {
      ativo = false;
    };
  }, [api, dataSel, recarga]);

  useEffect(() => {
    let ativo = true;
    setAlertasCarregando(true);
    setAlertasErro(null);
    const buscas = [api.get<{ items: MetaAdsAlerta[] }>("/meta-ads/alertas", { params: { status: "aberto" } })];
    if (mostrarCientes) buscas.push(api.get<{ items: MetaAdsAlerta[] }>("/meta-ads/alertas", { params: { status: "ciente" } }));
    Promise.all(buscas)
      .then((rs) => {
        if (!ativo) return;
        const todos = rs.flatMap((r) => r.data.items ?? []);
        todos.sort((a, b) => b.malPrimeiroEm.localeCompare(a.malPrimeiroEm));
        setAlertas(todos);
      })
      .catch((err) => {
        if (!ativo) return;
        setAlertas([]);
        setAlertasErro(mensagemErroApi(err, "Não foi possível carregar os alertas."));
      })
      .finally(() => {
        if (ativo) setAlertasCarregando(false);
      });
    return () => {
      ativo = false;
    };
  }, [api, mostrarCientes, recargaAlertas]);

  const gerar = async (data: string) => {
    setGerando(true);
    setResumoErro(null);
    try {
      const r = await api.post<ResumoDiario>(`/meta-ads/resumos/${data}/gerar`);
      setResumo(r.data);
      setDataSel(r.data.mrsData);
      setRecarga((n) => n + 1);
    } catch (err) {
      setResumoErro(mensagemErroApi(err, "Não foi possível gerar o resumo."));
    } finally {
      setGerando(false);
    }
  };

  const ciente = async (a: MetaAdsAlerta) => {
    setCienteEm(a.malId);
    setAlertasErro(null);
    try {
      await api.post(`/meta-ads/alertas/${a.malId}/ciente`);
      setRecargaAlertas((n) => n + 1);
    } catch (err) {
      setAlertasErro(mensagemErroApi(err, "Não foi possível marcar o alerta como ciente."));
    } finally {
      setCienteEm(null);
    }
  };

  const d = resumo?.mrsDados;
  const cartoes = (p: NonNullable<typeof d>["periodo"], comVariacao: boolean, cobertura: number | null) => {
    const v = d?.comparacao.variacaoPct ?? {};
    const itens: [string, string, string | undefined][] = [
      ["Gasto", moeda(p.investimento), comVariacao ? variacao(v.investimento) : undefined],
      ["Leads Meta", String(p.leadsMeta), comVariacao ? variacao(v.leadsMeta) : undefined],
      ["CPL", moeda(p.cpl), undefined],
      ["MQLs", String(p.mqls), comVariacao ? variacao(v.mqls) : undefined],
      ["Custo/MQL", moeda(p.custoMql), undefined],
    ];
    if (comVariacao) itens.push(["Cobertura de rastreio", cobertura == null ? "—" : percentual(cobertura), undefined]);
    return (
      <section className="dashboard-cards-row campanhas-cards">
        {itens.map(([rotulo, valor, dica]) => (
          <div key={rotulo} className="dashboard-card" title={dica}>
            <strong className="dashboard-card-value">{valor}</strong>
            <span className="dashboard-card-label">{rotulo}</span>
            {dica ? <span className="muted-text monitoramento-variacao">{dica}</span> : null}
          </div>
        ))}
      </section>
    );
  };

  return (
    <Layout>
      <section className="surface-card details-card monitoramento-bloco">
        <div className="monitoramento-titulo">
          <h2 className="section-title">Resumo diário</h2>
          <div className="monitoramento-acoes">
            {datas.length > 0 && (
              <label>
                Data
                <select value={dataSel} onChange={(e) => setDataSel(e.target.value)} disabled={gerando}>
                  <option value="">Mais recente</option>
                  {datas.map((x) => (
                    <option key={x.mrsData} value={x.mrsData}>
                      {dataBR(x.mrsData)}
                    </option>
                  ))}
                </select>
              </label>
            )}
            {resumo && (
              <button type="button" onClick={() => void gerar(resumo.mrsData)} disabled={gerando}>
                {gerando ? "Gerando…" : "Gerar de novo"}
              </button>
            )}
            {admin && (
              <button type="button" className="primary" onClick={() => setConfigAberta(true)}>
                Configurar
              </button>
            )}
          </div>
        </div>

        {(resumoCarregando || gerando) && <Loader />}
        {resumoErro && <div className="integracao-erro">{resumoErro}</div>}

        {!resumoCarregando && !resumo && !resumoErro && (
          <div>
            <p>Nenhum resumo gerado ainda.</p>
            <button type="button" className="primary" onClick={() => void gerar(hojeISO())} disabled={gerando}>
              {gerando ? "Gerando…" : "Gerar agora"}
            </button>
          </div>
        )}

        {!resumoCarregando && resumo && d && (
          <>
            <p className="muted-text">
              Resumo de {dataBR(resumo.mrsData)} · gerado em {dataHora(resumo.mrsGeradoEm)} · {d.alertasAbertos}{" "}
              {d.alertasAbertos === 1 ? "alerta aberto" : "alertas abertos"}
            </p>

            <h3>
              Período anterior ({dataBR(d.periodo.inicio)}
              {d.periodo.fim !== d.periodo.inicio ? ` a ${dataBR(d.periodo.fim)}` : ""})
            </h3>
            {cartoes(d.periodo, false, null)}

            <h3>
              Últimos 7 dias ({dataBR(d.ultimos7.inicio)} a {dataBR(d.ultimos7.fim)})
            </h3>
            {cartoes(d.ultimos7, true, d.cobertura)}

            <h3>Leitura</h3>
            {resumo.mrsLeitura ? (
              <p className="monitoramento-leitura">{resumo.mrsLeitura}</p>
            ) : (
              <p className="muted-text">{resumo.mrsAviso ?? "Leitura por IA indisponível."}</p>
            )}

            <div className="monitoramento-rankings">
              <TabelaRanking titulo="3 melhores anúncios" itens={d.melhores} />
              <TabelaRanking titulo="3 piores anúncios" itens={d.piores} />
            </div>

            <h3>Por campanha (últimos 7 dias)</h3>
            {d.campanhas.length === 0 ? (
              <p className="muted-text">Sem campanhas no período.</p>
            ) : (
              <div className="campanhas-tabela-scroll">
                <table className="dashboard-ranking-table campanhas-tabela">
                  <thead>
                    <tr>
                      <th>Campanha</th>
                      <th>Gasto</th>
                      <th>Impressões</th>
                      <th>Leads Meta</th>
                      <th>CPL</th>
                      <th>MQLs</th>
                      <th>Custo/MQL</th>
                    </tr>
                  </thead>
                  <tbody>
                    {d.campanhas.map((c) => (
                      <tr key={c.id ?? c.nome}>
                        <td className="campanhas-col-nome">{c.nome}</td>
                        <td>{moeda(c.investimento)}</td>
                        <td>{inteiro(c.impressoes)}</td>
                        <td>{c.leadsMeta}</td>
                        <td>{moeda(c.cpl)}</td>
                        <td>{c.mqls}</td>
                        <td>{moeda(c.custoMql)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </section>

      <section className="surface-card details-card monitoramento-bloco">
        <div className="monitoramento-titulo">
          <h2 className="section-title">Alertas abertos</h2>
          <label className="checkbox-inline">
            <input type="checkbox" checked={mostrarCientes} onChange={(e) => setMostrarCientes(e.target.checked)} />
            Mostrar cientes
          </label>
        </div>
        {alertasCarregando && <Loader />}
        {alertasErro && <div className="integracao-erro">{alertasErro}</div>}
        {!alertasCarregando && !alertasErro && alertas.length === 0 && <p className="muted-text">Nenhum alerta no momento.</p>}
        {!alertasCarregando && alertas.length > 0 && (
          <ul className="monitoramento-alertas">
            {alertas.map((a) => {
              const leadId = leadDoAlerta(a);
              return (
                <li key={a.malId} className="monitoramento-alerta">
                  <div>
                    <strong>{ROTULO_ALERTA[a.malTipo] ?? a.malTipo}</strong>
                    {a.alvoNome ? <span className="muted-text"> · {a.alvoNome}</span> : null}
                    {a.malStatus === "ciente" ? <span className="integracao-badge integracao-badge--warn"> Ciente</span> : null}
                    <p>{a.malMensagem}</p>
                    <span className="muted-text">Desde {dataHora(a.malPrimeiroEm)}</span>
                    {leadId ? (
                      <>
                        {" · "}
                        <Link to={`/oportunidades/${leadId}`}>Abrir lead</Link>
                      </>
                    ) : null}
                  </div>
                  {a.malStatus === "aberto" && (
                    <button type="button" onClick={() => void ciente(a)} disabled={cienteEm === a.malId}>
                      Ciente
                    </button>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </section>

      {admin && (
        <ConfigMonitoramentoModal
          isOpen={configAberta}
          onClose={() => setConfigAberta(false)}
          onSaved={() => setRecargaAlertas((n) => n + 1)}
        />
      )}
    </Layout>
  );
};

export default MonitoramentoPage;
