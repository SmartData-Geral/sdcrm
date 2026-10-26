import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import Layout from "../../components/Layout";
import Loader from "../../components/Loader";
import { useAuth } from "../../contexts/AuthContext";
import CampanhaDetalheModal from "./CampanhaDetalheModal";
import {
  MetaAdsContaOpcao,
  MetaAdsLinha,
  MetaAdsPainel,
  intervaloAnoCorrente,
  intervaloMesCorrente,
  dataBR,
  horas,
  inteiro,
  moeda,
  multiplicador,
  percentual,
  rotuloStatusCampanha,
} from "./metaAdsTipos";

const CampanhasPage: React.FC = () => {
  const { api, user } = useAuth();
  const padrao = intervaloAnoCorrente();
  const [inicioDraft, setInicioDraft] = useState(padrao.inicio);
  const [fimDraft, setFimDraft] = useState(padrao.fim);
  const [inicio, setInicio] = useState(padrao.inicio);
  const [fim, setFim] = useState(padrao.fim);
  const [macId, setMacId] = useState<string>("");
  const [somenteAtivas, setSomenteAtivas] = useState(false);
  const [contas, setContas] = useState<MetaAdsContaOpcao[]>([]);
  const [painel, setPainel] = useState<MetaAdsPainel | null>(null);
  const [loading, setLoading] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
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

  const aplicar = () => {
    setInicio(inicioDraft);
    setFim(fimDraft);
  };

  const rapido = (tipo: "mes" | "ano") => {
    const r = tipo === "mes" ? intervaloMesCorrente() : intervaloAnoCorrente();
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

  const semConta = painel && !painel.temConta;
  const t = painel?.total;

  return (
    <Layout>
      <section className="dashboard-filters campanhas-filtros">
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
        <button type="button" onClick={() => rapido("mes")}>
          Mês atual
        </button>
        <button type="button" onClick={() => rapido("ano")}>
          Ano atual
        </button>
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
      </section>

      {loading && <Loader />}
      {erro && <div className="integracao-erro">{erro}</div>}

      {!loading && semConta && (
        <section className="surface-card details-card">
          <p>Nenhuma conta do Meta Ads conectada nesta empresa.</p>
          {user?.usuAdmin ? (
            <Link to="/integracoes/meta-ads">Conectar uma conta em Integrações → Meta Ads</Link>
          ) : (
            <p className="muted-text">Peça a um administrador para conectar a conta em Integrações → Meta Ads.</p>
          )}
        </section>
      )}

      {!loading && painel && !semConta && t && (
        <>
          <section className="dashboard-cards-row campanhas-cards">
            {[
              ["Investimento", moeda(t.investimento), undefined],
              ["Leads Meta", String(t.leadsMeta), undefined],
              ["CPL", moeda(t.cpl), undefined],
              ["MQLs", String(t.mqls), undefined],
              ["Custo/MQL", moeda(t.custoMql), undefined],
              ["Oportunidades", String(t.oportunidades), undefined],
              ["Contratos", String(t.vendas), undefined],
              ["CAC", moeda(t.cac), undefined],
              ["Retorno", multiplicador(t.retorno), undefined],
              ["Cobertura de rastreio", painel.cobertura == null ? "—" : percentual(painel.cobertura), "% dos leads da Meta com ID do anúncio; meta ≥ 90%"],
            ].map(([rotulo, valor, dica]) => (
              <div key={rotulo} className="dashboard-card" title={dica}>
                <strong className="dashboard-card-value">{valor}</strong>
                <span className="dashboard-card-label">{rotulo}</span>
              </div>
            ))}
          </section>

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
            <section className="surface-card details-card campanhas-revisao">
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
