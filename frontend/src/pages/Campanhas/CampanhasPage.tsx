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

  useEffect(() => {
    api
      .get<{ items: MetaAdsContaOpcao[] }>("/meta-ads/contas-opcoes")
      .then((r) => setContas(r.data.items ?? []))
      .catch(() => setContas([]));
  }, [api]);

  useEffect(() => {
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
      .then((r) => setPainel(r.data))
      .catch(() => setErro("Não foi possível carregar as campanhas."))
      .finally(() => setLoading(false));
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

  const linhaTabela = (l: MetaAdsLinha, opcoes: { clicavel: boolean; classe?: string }) => (
    <tr
      key={l.mcgId ?? l.nome}
      className={`${opcoes.clicavel ? "dashboard-ranking-row--clickable" : ""} ${opcoes.classe ?? ""}`}
      tabIndex={opcoes.clicavel ? 0 : undefined}
      onClick={opcoes.clicavel ? () => setDetalheId(l.mcgId) : undefined}
      onKeyDown={
        opcoes.clicavel
          ? (e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                setDetalheId(l.mcgId);
              }
            }
          : undefined
      }
    >
      <td className="campanhas-col-nome">{l.nome}</td>
      <td>{l.mcgId != null ? rotuloStatusCampanha(l.status) : ""}</td>
      <td>{moeda(l.investimento)}</td>
      <td>{inteiro(l.impressoes)}</td>
      <td>{inteiro(l.cliques)}</td>
      <td>{percentual(l.ctr)}</td>
      <td>{moeda(l.cpc)}</td>
      <td>{l.leadsMeta}</td>
      <td>{l.leadsCrm}</td>
      <td>{moeda(l.cpl)}</td>
      <td>{l.vendas}</td>
      <td>{moeda(l.cac)}</td>
      <td>{moeda(l.mrr)}</td>
      <td>{moeda(l.projeto)}</td>
      <td>{multiplicador(l.retorno)}</td>
    </tr>
  );

  const semConta = painel && !painel.temConta;
  const t = painel?.total;

  return (
    <Layout>
      <section className="surface-card details-card integracao-header">
        <div>
          <h2 className="section-title">Campanhas</h2>
          <p className="muted-text">Investimento do Meta Ads cruzado com os leads e as vendas do CRM.</p>
        </div>
      </section>

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
              ["Investimento", moeda(t.investimento)],
              ["Leads CRM", String(t.leadsCrm)],
              ["CPL", moeda(t.cpl)],
              ["Vendas", String(t.vendas)],
              ["CAC", moeda(t.cac)],
              ["MRR", moeda(t.mrr)],
              ["Retorno", multiplicador(t.retorno)],
            ].map(([rotulo, valor]) => (
              <div key={rotulo} className="dashboard-card">
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
                    <th>Campanha</th>
                    <th>Status</th>
                    <th>Investimento</th>
                    <th>Impressões</th>
                    <th>Cliques</th>
                    <th>CTR</th>
                    <th>CPC</th>
                    <th>Leads Meta</th>
                    <th>Leads CRM</th>
                    <th>CPL</th>
                    <th>Vendas</th>
                    <th>CAC</th>
                    <th>MRR</th>
                    <th>Projeto</th>
                    <th title="(MRR × 12 + Projeto) ÷ Investimento">Retorno</th>
                  </tr>
                </thead>
                <tbody>
                  {painel.campanhas.length === 0 && !painel.naoIdentificada ? (
                    <tr>
                      <td colSpan={15} className="muted-text">
                        Sem investimento nem leads no período.
                      </td>
                    </tr>
                  ) : null}
                  {painel.campanhas.map((l) => linhaTabela(l, { clicavel: true }))}
                  {painel.naoIdentificada ? linhaTabela(painel.naoIdentificada, { clicavel: false, classe: "campanhas-linha-nao-identificada" }) : null}
                </tbody>
                <tfoot>{linhaTabela(t, { clicavel: false, classe: "campanhas-linha-total" })}</tfoot>
              </table>
            </div>
          </section>
        </>
      )}

      <CampanhaDetalheModal mcgId={detalheId} inicio={inicio} fim={fim} onClose={() => setDetalheId(null)} />
    </Layout>
  );
};

export default CampanhasPage;
