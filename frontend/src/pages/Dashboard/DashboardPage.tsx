import React, { useEffect, useMemo, useState } from "react";
import Layout from "../../components/Layout";
import Loader from "../../components/Loader";
import { useAuth } from "../../contexts/AuthContext";

interface CrmDashboardCards {
  recebidas: number;
  recebidas12m: number;
  recebidasUltimoMes: number;
  recebidasMesCorrente: number;
  ganhas: number;
  ganhas12m: number;
  ganhasUltimoMes: number;
  ganhasMesCorrente: number;
  perdidas: number;
  perdidas12m: number;
  perdidasUltimoMes: number;
  perdidasMesCorrente: number;
  taxaConversao: number;
  ativas: number;
  valorAtivas: number;
  mrrIncremental: number;
  mrrIncremental12m: number;
  mrrIncrementalUltimoMes: number;
  mrrIncrementalMesCorrente: number;
}

interface CrmDashboardGraficoPorMesItem {
  ano: number;
  mes: number;
  quantidade: number;
}

interface CrmDashboardGraficoPorFonteItem {
  fonte: string;
  quantidade: number;
}

interface CrmDashboardGraficoPorSolucaoItem {
  solucao: string;
  quantidade: number;
}

interface CrmDashboardGraficoAtivasPorResponsavelItem {
  responsavel: string;
  quantidade: number;
}

interface CrmDashboardResponse {
  cards: CrmDashboardCards;
  graficos: {
    porMes: CrmDashboardGraficoPorMesItem[];
    porFonte: CrmDashboardGraficoPorFonteItem[];
    porSolucao: CrmDashboardGraficoPorSolucaoItem[];
    ativasPorResponsavel: CrmDashboardGraficoAtivasPorResponsavelItem[];
  };
  filtros: {
    responsaveis: Array<{ id: number; nome: string }>;
  };
}

type StatusFiltro = "todas" | "ganhas" | "perdidas" | "ativas";

const DashboardPage: React.FC = () => {
  const { api } = useAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [cards, setCards] = useState<CrmDashboardCards | null>(null);
  const [porMes, setPorMes] = useState<CrmDashboardGraficoPorMesItem[]>([]);
  const [porFonte, setPorFonte] = useState<CrmDashboardGraficoPorFonteItem[]>([]);
  const [porSolucao, setPorSolucao] = useState<CrmDashboardGraficoPorSolucaoItem[]>([]);
  const [ativasPorResponsavel, setAtivasPorResponsavel] = useState<CrmDashboardGraficoAtivasPorResponsavelItem[]>([]);
  const [responsaveis, setResponsaveis] = useState<Array<{ id: number; nome: string }>>([]);

  const [dataInicialDraft, setDataInicialDraft] = useState("");
  const [dataFinalDraft, setDataFinalDraft] = useState("");
  const [responsavelDraft, setResponsavelDraft] = useState<number | "">("");
  const [statusDraft, setStatusDraft] = useState<StatusFiltro>("todas");

  const [dataInicial, setDataInicial] = useState<string | null>(null);
  const [dataFinal, setDataFinal] = useState<string | null>(null);
  const [responsavel, setResponsavel] = useState<number | null>(null);
  const [status, setStatus] = useState<StatusFiltro>("todas");

  const loadDashboard = async () => {
    setLoading(true);
    setError(null);
    try {
      const params: Record<string, unknown> = {
        status,
      };
      if (dataInicial) params.data_inicial = dataInicial;
      if (dataFinal) params.data_final = dataFinal;
      if (responsavel != null) params.responsavel_id = responsavel;

      const res = await api.get<CrmDashboardResponse>("/crm/dashboard", { params });
      setCards(res.data.cards);
      setPorMes(res.data.graficos.porMes);
      setPorFonte(res.data.graficos.porFonte);
      setPorSolucao(res.data.graficos.porSolucao);
      setAtivasPorResponsavel(res.data.graficos.ativasPorResponsavel);
      setResponsaveis(res.data.filtros.responsaveis ?? []);
    } catch (e) {
      console.error(e);
      setError("Não foi possível carregar a dashboard do CRM. Tente novamente.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadDashboard();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dataInicial, dataFinal, responsavel, status]);

  const aplicarFiltros = () => {
    setDataInicial(dataInicialDraft || null);
    setDataFinal(dataFinalDraft || null);
    setResponsavel(responsavelDraft === "" ? null : Number(responsavelDraft));
    setStatus(statusDraft);
  };

  const limparFiltros = () => {
    setDataInicialDraft("");
    setDataFinalDraft("");
    setResponsavelDraft("");
    setStatusDraft("todas");
    setDataInicial(null);
    setDataFinal(null);
    setResponsavel(null);
    setStatus("todas");
  };

  const maxPorMes = useMemo(() => (porMes.length ? Math.max(...porMes.map((m) => m.quantidade)) : 0), [porMes]);
  const maxHorizontal = useMemo(
    () =>
      Math.max(
        porFonte.length ? Math.max(...porFonte.map((f) => f.quantidade)) : 0,
        porSolucao.length ? Math.max(...porSolucao.map((s) => s.quantidade)) : 0
      ),
    [porFonte, porSolucao]
  );
  const totalAtivasResponsavel = useMemo(
    () => ativasPorResponsavel.reduce((acc, item) => acc + item.quantidade, 0),
    [ativasPorResponsavel]
  );

  const formatCurrencyBRL = (value: number) =>
    value.toLocaleString("pt-BR", { style: "currency", currency: "BRL", minimumFractionDigits: 2 });

  const formatPercent = (value: number) =>
    `${value.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}%`;

  const formatMesLabel = (item: CrmDashboardGraficoPorMesItem) => {
    const month = String(item.mes).padStart(2, "0");
    return `${month}/${item.ano}`;
  };

  return (
    <Layout>
      <section className="dashboard-filters">
        <div className="surface-card dashboard-filters-inner">
          <div className="form-row">
            <label className="form-field">
              <span className="form-label">Período</span>
              <div className="form-inline">
                <input
                  type="date"
                  value={dataInicialDraft}
                  onChange={(e) => setDataInicialDraft(e.target.value)}
                  aria-label="Data inicial"
                />
                <span className="oportunidades-filtros-separador">até</span>
                <input
                  type="date"
                  value={dataFinalDraft}
                  onChange={(e) => setDataFinalDraft(e.target.value)}
                  aria-label="Data final"
                />
              </div>
            </label>
            <label className="form-field">
              <span className="form-label">Responsável</span>
              <select
                value={responsavelDraft}
                onChange={(e) => {
                  const value = e.target.value;
                  setResponsavelDraft(value === "" ? "" : Number(value));
                }}
              >
                <option value="">Todos</option>
                {responsaveis.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.nome}
                  </option>
                ))}
              </select>
            </label>
            <fieldset className="form-field">
              <legend className="form-label">Status</legend>
              <div className="radio-group">
                {(["todas", "ganhas", "perdidas", "ativas"] as const).map((value) => (
                  <label key={value} className="radio-option">
                    <input
                      type="radio"
                      name="statusDashboard"
                      value={value}
                      checked={statusDraft === value}
                      onChange={() => setStatusDraft(value)}
                    />
                    <span>
                      {value === "todas" && "Todas"}
                      {value === "ganhas" && "Ganhas"}
                      {value === "perdidas" && "Perdidas"}
                      {value === "ativas" && "Ativas"}
                    </span>
                  </label>
                ))}
              </div>
            </fieldset>
            <div className="form-actions">
              <button type="button" className="btn-primary" onClick={aplicarFiltros}>
                Filtrar
              </button>
              <button type="button" onClick={limparFiltros}>
                Limpar
              </button>
            </div>
          </div>
        </div>
      </section>

      {loading && <Loader />}
      {!loading && error && (
        <section className="surface-card">
          <p className="error-text">{error}</p>
        </section>
      )}

      {!loading && !error && cards && (
        <>
          <section className="dashboard-cards-row">
            <div className="dashboard-card dashboard-card--blue">
              <div className="dashboard-card-header">
                <span className="dashboard-card-icon dashboard-card-icon--recebidas" aria-hidden>
                  <svg viewBox="0 0 24 24">
                    <path d="M4 4h16v4H4zM4 10h10v4H4zM4 16h7v4H4z" />
                  </svg>
                </span>
                <strong className="dashboard-card-value">{cards.recebidas}</strong>
              </div>
              <span className="dashboard-card-label">Oportunidades Recebidas</span>
              <span className="dashboard-card-subvalue">12M: {cards.recebidas12m}</span>
              <span className="dashboard-card-subvalue">Últ. mês: {cards.recebidasUltimoMes}</span>
              <span className="dashboard-card-subvalue">Mês atual: {cards.recebidasMesCorrente}</span>
            </div>
            <div className="dashboard-card dashboard-card--green">
              <div className="dashboard-card-header">
                <span className="dashboard-card-icon dashboard-card-icon--ganhas" aria-hidden>
                  <svg viewBox="0 0 24 24">
                    <path d="M5 13l4 4L19 7" />
                  </svg>
                </span>
                <strong className="dashboard-card-value">{cards.ganhas}</strong>
              </div>
              <span className="dashboard-card-label">Oportunidades Ganhas</span>
              <span className="dashboard-card-subvalue">12M: {cards.ganhas12m}</span>
              <span className="dashboard-card-subvalue">Últ. mês: {cards.ganhasUltimoMes}</span>
              <span className="dashboard-card-subvalue">Mês atual: {cards.ganhasMesCorrente}</span>
            </div>
            <div className="dashboard-card dashboard-card--red">
              <div className="dashboard-card-header">
                <span className="dashboard-card-icon dashboard-card-icon--perdidas" aria-hidden>
                  <svg viewBox="0 0 24 24">
                    <path d="M6 6l12 12M18 6L6 18" />
                  </svg>
                </span>
                <strong className="dashboard-card-value">{cards.perdidas}</strong>
              </div>
              <span className="dashboard-card-label">Oportunidades Perdidas</span>
              <span className="dashboard-card-subvalue">12M: {cards.perdidas12m}</span>
              <span className="dashboard-card-subvalue">Últ. mês: {cards.perdidasUltimoMes}</span>
              <span className="dashboard-card-subvalue">Mês atual: {cards.perdidasMesCorrente}</span>
            </div>
            <div className="dashboard-card dashboard-card--purple">
              <div className="dashboard-card-header">
                <span className="dashboard-card-icon dashboard-card-icon--taxa" aria-hidden>
                  <svg viewBox="0 0 24 24">
                    <path d="M4 19h16M5 15l4-4 4 4 6-6" />
                  </svg>
                </span>
                <strong className="dashboard-card-value">{formatPercent(cards.taxaConversao)}</strong>
              </div>
              <span className="dashboard-card-label">Taxa de Conversão</span>
            </div>
            <div className="dashboard-card dashboard-card--cyan">
              <div className="dashboard-card-header">
                <span className="dashboard-card-icon dashboard-card-icon--ativas" aria-hidden>
                  <svg viewBox="0 0 24 24">
                    <path d="M4 12h4l2-4 4 8 2-4h4" />
                  </svg>
                </span>
                <strong className="dashboard-card-value">{cards.ativas}</strong>
              </div>
              <span className="dashboard-card-label">Oportunidades Ativas</span>
              <span className="dashboard-card-subvalue">{formatCurrencyBRL(cards.valorAtivas)}</span>
            </div>
            <div className="dashboard-card dashboard-card--orange">
              <div className="dashboard-card-header">
                <span className="dashboard-card-icon dashboard-card-icon--mrr" aria-hidden>
                  <svg viewBox="0 0 24 24">
                    <path d="M4 18h16V6H4zm4-5h2.5a2 2 0 100-4H9m0 8h2.5a2 2 0 100-4H9" />
                  </svg>
                </span>
                <strong className="dashboard-card-value">{formatCurrencyBRL(cards.mrrIncremental)}</strong>
              </div>
              <span className="dashboard-card-label">MRR Incremental</span>
              <span className="dashboard-card-subvalue">
                12M: {formatCurrencyBRL(cards.mrrIncremental12m)}
              </span>
              <span className="dashboard-card-subvalue">
                Últ. mês: {formatCurrencyBRL(cards.mrrIncrementalUltimoMes)}
              </span>
              <span className="dashboard-card-subvalue">
                Mês atual: {formatCurrencyBRL(cards.mrrIncrementalMesCorrente)}
              </span>
            </div>
          </section>

          <section className="dashboard-charts-grid">
            <article className="surface-card">
              <h2>Oportunidades por Mês</h2>
              {porMes.length === 0 ? (
                <p className="empty-state-text">Nenhum dado encontrado para o período.</p>
              ) : (
                <div className="chart chart--bars-vertical">
                  {porMes.map((item) => {
                    const basePercent = maxPorMes > 0 ? (item.quantidade / maxPorMes) * 100 : 0;
                    const heightPercent = basePercent > 0 ? 20 + basePercent * 0.75 : 0;
                    return (
                      <div key={`${item.ano}-${item.mes}`} className="chart-bar-vertical">
                        <div className="chart-bar-vertical-bar" style={{ height: `${heightPercent}%` }}>
                          <span className="chart-bar-vertical-value">{item.quantidade}</span>
                        </div>
                        <span className="chart-bar-vertical-label">{formatMesLabel(item)}</span>
                      </div>
                    );
                  })}
                </div>
              )}
            </article>

            <article className="surface-card">
              <h2>Oportunidades por Fonte</h2>
              {porFonte.length === 0 ? (
                <p className="empty-state-text">Nenhum dado encontrado para o período.</p>
              ) : (
                <div className="chart chart--bars-horizontal">
                  {porFonte.map((item) => {
                    const widthPercent = maxHorizontal > 0 ? (item.quantidade / maxHorizontal) * 100 : 0;
                    return (
                      <div key={item.fonte} className="chart-bar-horizontal">
                        <span className="chart-bar-horizontal-label">{item.fonte}</span>
                        <div className="chart-bar-horizontal-track">
                          <div className="chart-bar-horizontal-bar" style={{ width: `${widthPercent}%` }} />
                        </div>
                        <span className="chart-bar-horizontal-value">{item.quantidade}</span>
                      </div>
                    );
                  })}
                </div>
              )}
            </article>

            <article className="surface-card">
              <h2>Oportunidades por Solução</h2>
              {porSolucao.length === 0 ? (
                <p className="empty-state-text">Nenhum dado encontrado para o período.</p>
              ) : (
                <div className="chart chart--bars-horizontal">
                  {porSolucao.map((item) => {
                    const widthPercent = maxHorizontal > 0 ? (item.quantidade / maxHorizontal) * 100 : 0;
                    return (
                      <div key={item.solucao} className="chart-bar-horizontal">
                        <span className="chart-bar-horizontal-label">{item.solucao}</span>
                        <div className="chart-bar-horizontal-track">
                          <div className="chart-bar-horizontal-bar chart-bar-horizontal-bar--secondary" style={{ width: `${widthPercent}%` }} />
                        </div>
                        <span className="chart-bar-horizontal-value">{item.quantidade}</span>
                      </div>
                    );
                  })}
                </div>
              )}
            </article>

            <article className="surface-card">
              <h2>Oportunidades Ativas por Responsável</h2>
              {totalAtivasResponsavel === 0 ? (
                <p className="empty-state-text">Nenhum dado encontrado para o período.</p>
              ) : (
                <div className="chart-donut-wrapper">
                  <svg
                    className="chart-donut"
                    viewBox="0 0 42 42"
                    role="img"
                    aria-label="Distribuição de oportunidades ativas por responsável"
                  >
                    <circle className="chart-donut-bg" cx="21" cy="21" r="15.91549430918954" />
                    {ativasPorResponsavel.reduce<JSX.Element[]>((acc, item, index) => {
                      const previousTotal = ativasPorResponsavel
                        .slice(0, index)
                        .reduce((sum, curr) => sum + curr.quantidade, 0);
                      const startOffset = (previousTotal / totalAtivasResponsavel) * 100;
                      const length = (item.quantidade / totalAtivasResponsavel) * 100;
                      const dashArray = `${length} ${100 - length}`;
                      const colorClass = `chart-donut-segment chart-donut-segment--${index % 5}`;
                      acc.push(
                        <circle
                          key={item.responsavel}
                          className={colorClass}
                          cx="21"
                          cy="21"
                          r="15.91549430918954"
                          strokeDasharray={dashArray}
                          strokeDashoffset={25 - startOffset}
                        />
                      );
                      return acc;
                    }, [])}
                  </svg>
                  <div className="chart-donut-legend">
                    {ativasPorResponsavel.map((item, index) => (
                      <div key={item.responsavel} className="chart-donut-legend-item">
                        <span className={`chart-donut-legend-color chart-donut-legend-color--${index % 5}`} />
                        <span className="chart-donut-legend-label">{item.responsavel}</span>
                        <span className="chart-donut-legend-value">
                          {item.quantidade} ({formatPercent((item.quantidade / totalAtivasResponsavel) * 100)})
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </article>
          </section>
        </>
      )}
    </Layout>
  );
};

export default DashboardPage;

