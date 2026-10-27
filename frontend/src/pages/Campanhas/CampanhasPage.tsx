import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import Layout from "../../components/Layout";
import Loader from "../../components/Loader";
import { useAuth } from "../../contexts/AuthContext";
import CampanhaDetalheModal from "./CampanhaDetalheModal";
import { CartoesIndicadores } from "./cockpit/CartoesIndicadores";
import { FunilCockpit } from "./cockpit/FunilCockpit";
import { GraficosTendencia } from "./cockpit/GraficosTendencia";
import { MatrizCriativos } from "./cockpit/MatrizCriativos";
import { SaudeOperacao } from "./cockpit/SaudeOperacao";
import { TabelaCriativos } from "./cockpit/TabelaCriativos";
import {
  MetaAdsCockpit,
  MetaAdsContaOpcao,
  MetaAdsLinha,
  MetaAdsPainel,
  intervaloAnoCorrente,
  intervaloMesCorrente,
  intervaloUltimosDias,
  dataBR,
  horas,
  inteiro,
  moeda,
  multiplicador,
  percentual,
  rotuloStatusCampanha,
} from "./metaAdsTipos";

type Atalho = "30d" | "mes" | "ano" | "custom";
const ATALHOS: [Atalho, string][] = [
  ["30d", "Últimos 30 dias"],
  ["mes", "Mês atual"],
  ["ano", "Ano atual"],
  ["custom", "Personalizado"],
];

const CampanhasPage: React.FC = () => {
  const { api, user } = useAuth();
  const padrao = intervaloAnoCorrente();
  const [inicioDraft, setInicioDraft] = useState(padrao.inicio);
  const [fimDraft, setFimDraft] = useState(padrao.fim);
  const [inicio, setInicio] = useState(padrao.inicio);
  const [fim, setFim] = useState(padrao.fim);
  const [atalho, setAtalho] = useState<Atalho>("ano");
  const [comparar, setComparar] = useState(true);
  const [macId, setMacId] = useState<string>("");
  const [somenteAtivas, setSomenteAtivas] = useState(false);
  const [contas, setContas] = useState<MetaAdsContaOpcao[]>([]);
  const [painel, setPainel] = useState<MetaAdsPainel | null>(null);
  const [cockpit, setCockpit] = useState<MetaAdsCockpit | null>(null);
  const [loading, setLoading] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [loadingCockpit, setLoadingCockpit] = useState(false);
  const [erroCockpit, setErroCockpit] = useState<string | null>(null);
  const [detalheId, setDetalheId] = useState<number | null>(null);
  const [expandidos, setExpandidos] = useState<Set<string>>(new Set());

  useEffect(() => {
    api
      .get<{ items: MetaAdsContaOpcao[] }>("/meta-ads/contas-opcoes")
      .then((r) => setContas(r.data.items ?? []))
      .catch(() => setContas([]));
  }, [api]);

  useEffect(() => {
    let ativo = true;
    setLoading(true);
    setErro(null);
    api
      .get<MetaAdsPainel>("/meta-ads/painel", {
        params: {
          data_inicial: inicio || undefined,
          data_final: fim || undefined,
          macId: macId || undefined,
          somente_ativas: somenteAtivas,
        },
      })
      .then((r) => {
        if (ativo) setPainel(r.data);
      })
      .catch(() => {
        if (!ativo) return;
        setPainel(null);
        setErro("Não foi possível carregar as campanhas.");
      })
      .finally(() => {
        if (ativo) setLoading(false);
      });
    return () => {
      ativo = false;
    };
  }, [api, inicio, fim, macId, somenteAtivas]);

  useEffect(() => {
    let ativo = true;
    setLoadingCockpit(true);
    setErroCockpit(null);
    api
      .get<MetaAdsCockpit>("/meta-ads/cockpit", {
        params: {
          data_inicial: inicio || undefined,
          data_final: fim || undefined,
          macId: macId || undefined,
          somente_ativas: somenteAtivas,
        },
      })
      .then((r) => {
        if (ativo) setCockpit(r.data);
      })
      .catch(() => {
        if (!ativo) return;
        setCockpit(null);
        setErroCockpit("Não foi possível carregar o cockpit.");
      })
      .finally(() => {
        if (ativo) setLoadingCockpit(false);
      });
    return () => {
      ativo = false;
    };
  }, [api, inicio, fim, macId, somenteAtivas]);

  const aplicar = () => {
    setInicio(inicioDraft);
    setFim(fimDraft);
  };

  const escolherAtalho = (tipo: Atalho) => {
    setAtalho(tipo);
    if (tipo === "custom") return;
    const r = tipo === "30d" ? intervaloUltimosDias(30) : tipo === "mes" ? intervaloMesCorrente() : intervaloAnoCorrente();
    setInicioDraft(r.inicio);
    setFimDraft(r.fim);
    setInicio(r.inicio);
    setFim(r.fim);
  };

  const alternar = (chave: string) =>
    setExpandidos((atual) => {
      const novo = new Set(atual);
      if (novo.has(chave)) novo.delete(chave);
      else novo.add(chave);
      return novo;
    });

  const linhaTabela = (l: MetaAdsLinha, opcoes: { classe?: string; nivel?: number }): React.ReactNode[] => {
    const nivel = opcoes.nivel ?? 0;
    const chave = `${l.nivel}:${l.id}`;
    const temFilhos = l.filhos.length > 0;
    const aberto = expandidos.has(chave);
    const clicavel = l.nivel === "campanha" && l.mcgId != null;
    const nomeTexto = l.nome;
    const linhas: React.ReactNode[] = [
      <tr key={`${l.nivel}:${l.id ?? l.nome}`} className={opcoes.classe ?? ""}>
        <td className="campanhas-col-nome" style={{ paddingLeft: `${0.5 + nivel * 1.25}rem` }}>
          {temFilhos ? (
            <button
              type="button"
              className="campanhas-expansor"
              aria-expanded={aberto}
              aria-label={aberto ? "Recolher" : "Expandir"}
              onClick={() => alternar(chave)}
            >
              {aberto ? "▾" : "▸"}
            </button>
          ) : (
            <span className="campanhas-expansor" aria-hidden="true" style={{ display: "inline-block" }} />
          )}
          {clicavel ? (
            <button type="button" className="link-button" onClick={() => setDetalheId(l.mcgId)}>
              {nomeTexto}
            </button>
          ) : (
            nomeTexto
          )}
        </td>
        <td>{l.nivel === "total" || l.nivel === "nao_identificada" ? "" : rotuloStatusCampanha(l.status)}</td>
        <td>{moeda(l.investimento)}</td>
        <td>{inteiro(l.impressoes)}</td>
        <td>{inteiro(l.cliques)}</td>
        <td>{percentual(l.ctr)}</td>
        <td>{moeda(l.cpc)}</td>
        <td>{l.leadsMeta}</td>
        <td>{moeda(l.cpl)}</td>
        <td>{l.leadsCrm}</td>
        <td>{moeda(l.custoLeadCrm)}</td>
        <td>{l.mqls}</td>
        <td>{moeda(l.custoMql)}</td>
        <td>{l.oportunidades}</td>
        <td>{moeda(l.custoOportunidade)}</td>
        <td>{l.vendas}</td>
        <td>{moeda(l.cac)}</td>
        <td>{moeda(l.mrr)}</td>
        <td>{moeda(l.projeto)}</td>
        <td>{multiplicador(l.retorno)}</td>
        <td>{horas(l.horasPrimeiroContato)}</td>
      </tr>,
    ];
    if (temFilhos && aberto) {
      for (const f of l.filhos) {
        linhas.push(...linhaTabela(f, { nivel: nivel + 1, classe: `campanhas-nivel-${f.nivel}` }));
      }
    }
    return linhas;
  };

  const semConta = (painel && !painel.temConta) || (cockpit && !cockpit.temConta);
  const t = painel?.total;
  const carregando = loading || loadingCockpit;

  return (
    <Layout>
      <section className="dashboard-filters campanhas-filtros">
        {ATALHOS.map(([chave, rotulo]) => (
          <button key={chave} type="button" aria-pressed={atalho === chave} onClick={() => escolherAtalho(chave)}>
            {rotulo}
          </button>
        ))}
        {atalho === "custom" && (
          <>
            <label>
              De
              <input type="date" value={inicioDraft} onChange={(e) => setInicioDraft(e.target.value)} />
            </label>
            <label>
              Até
              <input type="date" value={fimDraft} onChange={(e) => setFimDraft(e.target.value)} />
            </label>
            <button type="button" className="primary" onClick={aplicar}>
              Aplicar
            </button>
          </>
        )}
        <label>
          Conta
          <select value={macId} onChange={(e) => setMacId(e.target.value)}>
            <option value="">Todas</option>
            {contas.map((c) => (
              <option key={c.macId} value={c.macId}>
                {c.macNome}
              </option>
            ))}
          </select>
        </label>
        <label className="checkbox-inline">
          <input type="checkbox" checked={somenteAtivas} onChange={(e) => setSomenteAtivas(e.target.checked)} />
          Só campanhas ativas
        </label>
        <label className="checkbox-inline">
          <input type="checkbox" checked={comparar} onChange={(e) => setComparar(e.target.checked)} />
          Comparar com período anterior
        </label>
      </section>

      {/* Task 9: LeituraAnalista + PergunteAnalista entram aqui, acima dos indicadores. */}

      {carregando && <Loader />}
      {erro && <div className="integracao-erro">{erro}</div>}
      {erroCockpit && <div className="integracao-erro">{erroCockpit}</div>}

      {!carregando && semConta && (
        <section className="surface-card details-card">
          <p>Nenhuma conta do Meta Ads conectada nesta empresa.</p>
          {user?.usuAdmin ? (
            <Link to="/integracoes/meta-ads">Conectar uma conta em Integrações → Meta Ads</Link>
          ) : (
            <p className="muted-text">Peça a um administrador para conectar a conta em Integrações → Meta Ads.</p>
          )}
        </section>
      )}

      {!loadingCockpit && cockpit && cockpit.temConta && (
        <>
          <CartoesIndicadores cockpit={cockpit} comparar={comparar} />
          <FunilCockpit cockpit={cockpit} />
          <GraficosTendencia cockpit={cockpit} />
          <MatrizCriativos cockpit={cockpit} metas={cockpit.metas} />
          <TabelaCriativos cockpit={cockpit} />
          <SaudeOperacao cockpit={cockpit} />
        </>
      )}

      {!loading && painel && !semConta && t && (
        <>
          <h2 className="section-title">Detalhe por campanha</h2>
          <section className="surface-card campanhas-tabela-card">
            <div className="campanhas-tabela-scroll">
              <table className="dashboard-ranking-table campanhas-tabela">
                <thead>
                  <tr>
                    <th>Campanha / Anúncio</th>
                    <th>Status</th>
                    <th>Investimento</th>
                    <th>Impressões</th>
                    <th>Cliques</th>
                    <th>CTR</th>
                    <th>CPC</th>
                    <th>Leads Meta</th>
                    <th>CPL</th>
                    <th>Leads CRM</th>
                    <th>Custo/lead CRM</th>
                    <th>MQLs</th>
                    <th>Custo/MQL</th>
                    <th>Oportunidades</th>
                    <th>Custo/oportunidade</th>
                    <th>Contratos</th>
                    <th>CAC</th>
                    <th>MRR</th>
                    <th>Projeto</th>
                    <th title="(MRR × 12 + Projeto) ÷ Investimento">Retorno</th>
                    <th>Tempo até 1º contato (h)</th>
                  </tr>
                </thead>
                <tbody>
                  {painel.campanhas.length === 0 && !painel.naoIdentificada ? (
                    <tr>
                      <td colSpan={21} className="muted-text">
                        Sem investimento nem leads no período.
                      </td>
                    </tr>
                  ) : null}
                  {painel.campanhas.flatMap((l) => linhaTabela(l, {}))}
                  {painel.naoIdentificada ? linhaTabela(painel.naoIdentificada, { classe: "campanhas-linha-nao-identificada" }) : null}
                </tbody>
                <tfoot>{linhaTabela(t, { classe: "campanhas-linha-total" })}</tfoot>
              </table>
            </div>
          </section>

          {painel.revisaoOrigem.length > 0 && (
            <section id="revisao-origem" className="surface-card details-card campanhas-revisao">
              <h3 className="section-title">Origem Anúncios sem registro na Meta</h3>
              <p className="muted-text">
                Leads com origem mapeada como Meta Ads, mas sem nenhum sinal da Meta (campanha, conjunto ou anúncio). Revise a origem
                de cada um.
              </p>
              <div className="campanhas-tabela-scroll">
                <table className="dashboard-ranking-table">
                  <thead>
                    <tr>
                      <th>Lead</th>
                      <th>Contato</th>
                      <th>Recebido</th>
                    </tr>
                  </thead>
                  <tbody>
                    {painel.revisaoOrigem.map((r) => (
                      <tr key={r.opoId}>
                        <td>
                          <Link to={`/oportunidades/${r.opoId}`}>{r.opoTitulo}</Link>
                        </td>
                        <td>{r.opoNomeContato ?? "—"}</td>
                        <td>{dataBR(r.opoDataRecebimento)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}
        </>
      )}

      <CampanhaDetalheModal mcgId={detalheId} inicio={inicio} fim={fim} onClose={() => setDetalheId(null)} />
    </Layout>
  );
};

export default CampanhasPage;
