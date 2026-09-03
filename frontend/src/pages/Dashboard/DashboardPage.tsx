import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import Layout from "../../components/Layout";
import Loader from "../../components/Loader";
import { useAuth } from "../../contexts/AuthContext";

interface CrmDashboardCards {
  recebidas: number;
  recebidas12m: number;
  recebidasUltimoMes: number;
  recebidasMesCorrente: number;
  recebidasUltimos7Dias: number;
  ganhas: number;
  ganhas12m: number;
  ganhasUltimoMes: number;
  ganhasMesCorrente: number;
  ganhasUltimos7Dias: number;
  perdidas: number;
  perdidas12m: number;
  perdidasUltimoMes: number;
  perdidasMesCorrente: number;
  perdidasUltimos7Dias: number;
  taxaConversao: number;
  ativas: number;
  valorAtivas: number;
  forecastAtivas: number;
  mrrIncremental: number;
  mrrIncremental12m: number;
  mrrIncrementalUltimoMes: number;
  mrrIncrementalMesCorrente: number;
  mrrIncrementalUltimos7Dias: number;
  valorProjeto: number;
  valorProjeto12m: number;
  valorProjetoUltimoMes: number;
  valorProjetoMesCorrente: number;
  valorProjetoUltimos7Dias: number;
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

interface CrmDashboardResumoMetaLinha {
  meta: number | null;
  realizado: number;
  percentual: number | null;
  gap: number | null;
}

interface CrmDashboardResumoMetas {
  recebimento: CrmDashboardResumoMetaLinha;
  fechamento: CrmDashboardResumoMetaLinha;
  mrrIncremental: CrmDashboardResumoMetaLinha;
  valorProjeto: CrmDashboardResumoMetaLinha;
}

interface CrmDashboardMotivoPerdaItem {
  motivo: string;
  quantidade: number;
  percentualQuantidade: number;
  mrrPerdido: number;
  percentualMrr: number;
}

type MetricaSerie =
  | "recebidas"
  | "ganhas"
  | "perdidas"
  | "taxaConversao"
  | "mrrIncremental"
  | "mrrMedio"
  | "valorProjeto"
  | "forecast";

/* Gráfico "Meta x Realizado" suprimido — comparação com meta na Evolução mensal.
type MetricaMetaReal = "recebidas" | "ganhas" | "mrrIncremental";
*/

interface CrmDashboardSerieMensalItem {
  periodo: string;
  label: string;
  recebidas: number;
  ganhas: number;
  perdidas: number;
  taxaConversao: number;
  mrrIncremental: number;
  mrrMedio: number;
  valorProjeto: number;
  forecast: number;
  metaRecebidas: number | null;
  metaGanhas: number | null;
  metaMrr: number | null;
  metaValorProjeto: number | null;
}

function getValorPorMetrica(item: CrmDashboardSerieMensalItem, metrica: MetricaSerie): number {
  switch (metrica) {
    case "recebidas":
      return item.recebidas;
    case "ganhas":
      return item.ganhas;
    case "perdidas":
      return item.perdidas;
    case "taxaConversao":
      return item.taxaConversao;
    case "mrrIncremental":
      return item.mrrIncremental;
    case "mrrMedio":
      return item.mrrMedio;
    case "valorProjeto":
      return item.valorProjeto;
    case "forecast":
      return item.forecast;
    default:
      return 0;
  }
}

function getMetaSerie(item: CrmDashboardSerieMensalItem, metrica: MetricaSerie): number | null {
  switch (metrica) {
    case "recebidas":
      return item.metaRecebidas;
    case "ganhas":
      return item.metaGanhas;
    case "mrrIncremental":
      return item.metaMrr;
    case "valorProjeto":
      return item.metaValorProjeto;
    default:
      return null;
  }
}

/*
function getRealMetaRealizado(item: CrmDashboardSerieMensalItem, metrica: MetricaMetaReal): number {
  if (metrica === "recebidas") return item.recebidas;
  if (metrica === "ganhas") return item.ganhas;
  return item.mrrIncremental;
}

function getMetaMetaRealizado(item: CrmDashboardSerieMensalItem, metrica: MetricaMetaReal): number | null {
  if (metrica === "recebidas") return item.metaRecebidas;
  if (metrica === "ganhas") return item.metaGanhas;
  return item.metaMrr;
}

function formatMetaRealDatalabel(n: number, isMrr: boolean): string {
  if (!isMrr) return Math.round(n).toLocaleString("pt-BR");
  const v = Math.abs(n);
  if (v >= 1_000_000) {
    return `R$ ${(n / 1_000_000).toFixed(1).replace(".", ",")} Mi`;
  }
  if (v >= 1000) {
    return `R$ ${(n / 1000).toFixed(n % 1000 === 0 ? 0 : 1).replace(".", ",")} mil`;
  }
  return n.toLocaleString("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });
}
*/

function labelMetricaSerie(metrica: MetricaSerie): string {
  const map: Record<MetricaSerie, string> = {
    recebidas: "Recebidas",
    ganhas: "Ganhas",
    perdidas: "Perdidas",
    taxaConversao: "Conversão",
    mrrIncremental: "MRR incremental",
    mrrMedio: "MRR médio",
    valorProjeto: "Valor de projeto",
    forecast: "Forecast",
  };
  return map[metrica];
}

interface CrmDashboardRankingResponsavel {
  responsavelId: number | null;
  responsavel: string;
  recebidas: number;
  ganhas: number;
  perdidas: number;
  ativas: number;
  taxaConversao: number;
  mrrIncremental: number;
  valorProjeto: number;
  ticketMedio: number;
}

interface CrmDashboardRankingFonte {
  fonte: string;
  recebidas: number;
  ganhas: number;
  perdidas: number;
  taxaConversao: number;
  mrrIncremental: number;
  valorProjeto: number;
}

interface CrmDashboardRankingSolucao {
  solucao: string;
  recebidas: number;
  ganhas: number;
  perdidas: number;
  taxaConversao: number;
  mrrIncremental: number;
  valorProjeto: number;
}

interface CrmDashboardRankings {
  responsaveis: CrmDashboardRankingResponsavel[];
  fontes: CrmDashboardRankingFonte[];
  solucoes: CrmDashboardRankingSolucao[];
}

interface CrmDashboardOportunidadeResumo {
  id: number;
  nome: string;
  cliente: string | null;
  responsavel: string | null;
  status: string;
  fonte: string | null;
  solucao: string | null;
  motivoPerda: string | null;
  valorMrr: number | null;
  valorProjeto: number | null;
  forecast: number | null;
  dataCriacao: string | null;
  dataFechamento: string | null;
  etapa: string | null;
}

interface CrmDashboardOportunidadesListResponse {
  itens: CrmDashboardOportunidadeResumo[];
  total: number;
  resumo: {
    quantidade: number;
    mrrTotal: number;
    valorProjetoTotal: number;
    forecastTotal: number;
    ticketMedio: number;
  };
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
  temMeta?: boolean;
  resumoMetas?: CrmDashboardResumoMetas;
  motivosPerda?: CrmDashboardMotivoPerdaItem[];
  serieMensal?: CrmDashboardSerieMensalItem[];
  rankings?: CrmDashboardRankings;
}

export type MetricaDetalhamento =
  | "recebidas"
  | "ganhas"
  | "perdidas"
  | "ativas"
  | "mrrIncremental"
  | "valorProjeto";

export interface DetalhamentoParams {
  metrica?: MetricaDetalhamento;
  periodo?: string;
  fonte?: string;
  solucao?: string;
  motivo_perda?: string;
  responsavel_id?: number;
}

export interface DetalhamentoConfig {
  titulo: string;
  params: DetalhamentoParams;
}

function formatarTituloDetalhamento(config: DetalhamentoConfig): string {
  return config.titulo;
}

function serieMetricaParaDrill(metrica: MetricaSerie): MetricaDetalhamento {
  switch (metrica) {
    case "ganhas":
      return "ganhas";
    case "perdidas":
      return "perdidas";
    case "mrrIncremental":
      return "mrrIncremental";
    case "valorProjeto":
      return "valorProjeto";
    case "forecast":
      return "ativas";
    case "taxaConversao":
    case "mrrMedio":
    case "recebidas":
    default:
      return "recebidas";
  }
}

type StatusFiltro = "todas" | "ganhas" | "perdidas" | "ativas";
type FiltroRapidoPeriodo =
  | ""
  | "mes_corrente"
  | "mes_passado"
  | "ano_corrente"
  | "ultimos_7_dias"
  | "ultimos_30_dias"
  | "ultimo_trimestre";

function formatDateInputValue(value: Date): string {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

/** 1º de janeiro do ano corrente até hoje (datas locais). */
function getDefaultAnoCorrenteRange(): { dataInicial: string; dataFinal: string } {
  const hoje = new Date();
  const dataFinal = new Date(hoje.getFullYear(), hoje.getMonth(), hoje.getDate());
  const dataInicial = new Date(dataFinal.getFullYear(), 0, 1);
  return { dataInicial: formatDateInputValue(dataInicial), dataFinal: formatDateInputValue(dataFinal) };
}

const STATUS_TABS: { value: StatusFiltro; label: string; tabClass: string }[] = [
  { value: "todas", label: "Todas", tabClass: "" },
  { value: "ganhas", label: "Ganhas", tabClass: "tab--ganhas" },
  { value: "perdidas", label: "Perdidas", tabClass: "tab--perdidas" },
  { value: "ativas", label: "Ativas", tabClass: "tab--ativas" },
];

const SERIE_METRIC_TABS: { value: MetricaSerie; label: string }[] = [
  { value: "recebidas", label: "Recebidas" },
  { value: "ganhas", label: "Ganhas" },
  { value: "perdidas", label: "Perdidas" },
  { value: "taxaConversao", label: "Conversão" },
  { value: "mrrIncremental", label: "MRR" },
  { value: "mrrMedio", label: "MRR médio" },
  { value: "valorProjeto", label: "Projeto" },
  { value: "forecast", label: "Forecast" },
];

/*
const META_REAL_METRIC_TABS: { value: MetricaMetaReal; label: string }[] = [
  { value: "recebidas", label: "Recebidas" },
  { value: "ganhas", label: "Ganhas" },
  { value: "mrrIncremental", label: "MRR" },
];
*/

const DashboardPage: React.FC = () => {
  const { api } = useAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [cards, setCards] = useState<CrmDashboardCards | null>(null);
  const [serieMensal, setSerieMensal] = useState<CrmDashboardSerieMensalItem[]>([]);
  const [porFonte, setPorFonte] = useState<CrmDashboardGraficoPorFonteItem[]>([]);
  const [porSolucao, setPorSolucao] = useState<CrmDashboardGraficoPorSolucaoItem[]>([]);
  const [ativasPorResponsavel, setAtivasPorResponsavel] = useState<CrmDashboardGraficoAtivasPorResponsavelItem[]>([]);
  const [responsaveis, setResponsaveis] = useState<Array<{ id: number; nome: string }>>([]);
  const [temMeta, setTemMeta] = useState(false);
  const [resumoMetas, setResumoMetas] = useState<CrmDashboardResumoMetas | null>(null);
  const [motivosPerda, setMotivosPerda] = useState<CrmDashboardMotivoPerdaItem[]>([]);
  const [rankings, setRankings] = useState<CrmDashboardRankings | null>(null);
  const [dimensaoTab, setDimensaoTab] = useState<"responsaveis" | "fontes" | "solucoes">("responsaveis");
  const [detalheOpen, setDetalheOpen] = useState(false);
  const [detalheConfig, setDetalheConfig] = useState<DetalhamentoConfig | null>(null);
  const [detalheLoading, setDetalheLoading] = useState(false);
  const [detalheError, setDetalheError] = useState<string | null>(null);
  const [detalhePayload, setDetalhePayload] = useState<CrmDashboardOportunidadesListResponse | null>(null);
  const [metricaSerie, setMetricaSerie] = useState<MetricaSerie>("recebidas");
  // const [metricaMetaReal, setMetricaMetaReal] = useState<MetricaMetaReal>("recebidas"); // Meta x Realizado (suprimido)
  const [serieTooltip, setSerieTooltip] = useState<{ x: number; y: number; lines: string[] } | null>(null);

  const [dataInicialDraft, setDataInicialDraft] = useState(() => getDefaultAnoCorrenteRange().dataInicial);
  const [dataFinalDraft, setDataFinalDraft] = useState(() => getDefaultAnoCorrenteRange().dataFinal);
  const [periodoRapido, setPeriodoRapido] = useState<FiltroRapidoPeriodo>("ano_corrente");
  const [responsavelDraft, setResponsavelDraft] = useState<number | "">("");
  const [statusDraft, setStatusDraft] = useState<StatusFiltro>("todas");

  const anosSerieOpcoes = useMemo(() => {
    const y = new Date().getFullYear();
    const minAno = 2024;
    if (y < minAno) return [y];
    return Array.from({ length: y - minAno + 1 }, (_, i) => y - i);
  }, []);

  const [anosSerieGraficos, setAnosSerieGraficos] = useState<number[]>(() => [new Date().getFullYear()]);

  const [dataInicial, setDataInicial] = useState<string | null>(() => getDefaultAnoCorrenteRange().dataInicial);
  const [dataFinal, setDataFinal] = useState<string | null>(() => getDefaultAnoCorrenteRange().dataFinal);
  const [responsavel, setResponsavel] = useState<number | null>(null);
  const [status, setStatus] = useState<StatusFiltro>("todas");

  const toggleAnoSerieGrafico = (ano: number) => {
    setAnosSerieGraficos((prev) => {
      if (prev.includes(ano)) {
        const next = prev.filter((a) => a !== ano);
        return next.length > 0 ? next.sort((a, b) => a - b) : [ano];
      }
      return [...prev, ano].sort((a, b) => a - b);
    });
  };

  const loadDashboard = async () => {
    setLoading(true);
    setError(null);
    try {
      const params: Record<string, unknown> = { status };
      if (dataInicial) params.data_inicial = dataInicial;
      if (dataFinal) params.data_final = dataFinal;
      if (responsavel != null) params.responsavel_id = responsavel;
      if (anosSerieGraficos.length > 0) {
        params.serie_anos = anosSerieGraficos.join(",");
      }

      const res = await api.get<CrmDashboardResponse>("/crm/dashboard", { params });
      setCards(res.data.cards);
      setSerieMensal(res.data.serieMensal ?? []);
      setPorFonte(res.data.graficos.porFonte);
      setPorSolucao(res.data.graficos.porSolucao);
      setAtivasPorResponsavel(res.data.graficos.ativasPorResponsavel);
      setResponsaveis(res.data.filtros.responsaveis ?? []);
      setTemMeta(Boolean(res.data.temMeta));
      setResumoMetas(res.data.resumoMetas ?? null);
      setMotivosPerda(res.data.motivosPerda ?? []);
      setRankings(
        res.data.rankings ?? {
          responsaveis: [],
          fontes: [],
          solucoes: [],
        }
      );
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
  }, [dataInicial, dataFinal, responsavel, status, anosSerieGraficos]);

  const aplicarFiltros = () => {
    setDataInicial(dataInicialDraft || null);
    setDataFinal(dataFinalDraft || null);
    setResponsavel(responsavelDraft === "" ? null : Number(responsavelDraft));
    setStatus(statusDraft);
  };

  const limparFiltros = () => {
    setDataInicialDraft("");
    setDataFinalDraft("");
    setPeriodoRapido("");
    setResponsavelDraft("");
    setStatusDraft("todas");
    setDataInicial(null);
    setDataFinal(null);
    setResponsavel(null);
    setStatus("todas");
    setAnosSerieGraficos([new Date().getFullYear()]);
  };

  const maxPorFonte = useMemo(
    () => (porFonte.length ? Math.max(...porFonte.map((f) => f.quantidade)) : 0),
    [porFonte]
  );
  const maxPorSolucao = useMemo(
    () => (porSolucao.length ? Math.max(...porSolucao.map((s) => s.quantidade)) : 0),
    [porSolucao]
  );

  // const metaRealGlobalMax = useMemo(() => {
  //   let m = 1;
  //   for (const it of serieMensal) {
  //     const real = getRealMetaRealizado(it, metricaMetaReal);
  //     const meta = getMetaMetaRealizado(it, metricaMetaReal);
  //     m = Math.max(m, real, meta ?? 0);
  //   }
  //   return m;
  // }, [serieMensal, metricaMetaReal]);
  const totalAtivasResponsavel = useMemo(
    () => ativasPorResponsavel.reduce((acc, item) => acc + item.quantidade, 0),
    [ativasPorResponsavel]
  );
  const maxMotivosQuantidade = useMemo(
    () => (motivosPerda.length ? Math.max(...motivosPerda.map((m) => m.quantidade)) : 0),
    [motivosPerda]
  );

  const formatCurrencyBRL = (value: number) =>
    value.toLocaleString("pt-BR", { style: "currency", currency: "BRL", minimumFractionDigits: 2 });

  const formatPercent = (value: number) =>
    `${value.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}%`;

  const formatSerieMetricValue = (valor: number, metrica: MetricaSerie) => {
    if (metrica === "taxaConversao") return formatPercent(valor);
    if (
      metrica === "mrrIncremental" ||
      metrica === "mrrMedio" ||
      metrica === "valorProjeto" ||
      metrica === "forecast"
    )
      return formatCurrencyBRL(valor);
    return Math.round(valor).toLocaleString("pt-BR");
  };

  const maxSerieDinamico = useMemo(() => {
    let m = 0;
    for (const it of serieMensal) {
      m = Math.max(m, Math.abs(getValorPorMetrica(it, metricaSerie)));
      if (temMeta) {
        const meta = getMetaSerie(it, metricaSerie);
        if (meta != null && meta > 0) m = Math.max(m, meta);
      }
    }
    return m > 0 ? m : 1;
  }, [serieMensal, metricaSerie, temMeta]);

  const buildSerieTooltipLines = (item: CrmDashboardSerieMensalItem): string[] => {
    const v = getValorPorMetrica(item, metricaSerie);
    const lines: string[] = [`${item.label}`, `${labelMetricaSerie(metricaSerie)}: ${formatSerieMetricValue(v, metricaSerie)}`];
    if (temMeta) {
      const meta = getMetaSerie(item, metricaSerie);
      if (meta != null && meta > 0) {
        lines.push(`Meta: ${formatSerieMetricValue(meta, metricaSerie)}`);
        const pct = (v / meta) * 100;
        lines.push(
          `${pct.toLocaleString("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 })}% da meta`
        );
      }
    }
    return lines;
  };

  const renderKpiMetaLinha = (linha: CrmDashboardResumoMetaLinha | undefined, isMoeda: boolean) => {
    if (!temMeta || !linha || linha.meta == null) return null;
    const gap = linha.gap;
    const gapClass =
      gap == null ? "" : gap >= 0 ? "dashboard-card-meta-gap--pos" : "dashboard-card-meta-gap--neg";
    const metaTxt = isMoeda ? formatCurrencyBRL(linha.meta) : Math.round(linha.meta).toLocaleString("pt-BR");
    const gapTxt = isMoeda ? formatCurrencyBRL(gap ?? 0) : Math.round(gap ?? 0).toLocaleString("pt-BR");
    return (
      <div className="dashboard-card-meta">
        <span>
          Meta: <strong>{metaTxt}</strong>
        </span>
        {linha.percentual != null && (
          <span>
            {formatPercent(linha.percentual)} da meta
          </span>
        )}
        {gap != null && (
          <span className={gapClass}>{gapTxt}</span>
        )}
      </div>
    );
  };

  const formatDateInput = (value: Date) => formatDateInputValue(value);

  const aplicarPeriodoRapido = (value: FiltroRapidoPeriodo) => {
    setPeriodoRapido(value);
    if (!value) return;

    const hoje = new Date();
    let dataFinal = new Date(hoje.getFullYear(), hoje.getMonth(), hoje.getDate());
    let dataInicial = new Date(dataFinal);

    switch (value) {
      case "mes_corrente":
        dataInicial = new Date(dataFinal.getFullYear(), dataFinal.getMonth(), 1);
        break;
      case "mes_passado": {
        const ultimoDiaMesAnterior = new Date(dataFinal.getFullYear(), dataFinal.getMonth(), 0);
        dataInicial = new Date(ultimoDiaMesAnterior.getFullYear(), ultimoDiaMesAnterior.getMonth(), 1);
        dataFinal = ultimoDiaMesAnterior;
        break;
      }
      case "ano_corrente":
        dataInicial = new Date(dataFinal.getFullYear(), 0, 1);
        break;
      case "ultimos_7_dias":
        dataInicial.setDate(dataInicial.getDate() - 6);
        break;
      case "ultimos_30_dias":
        dataInicial.setDate(dataInicial.getDate() - 29);
        break;
      case "ultimo_trimestre":
        dataInicial = new Date(dataFinal);
        dataInicial.setMonth(dataInicial.getMonth() - 3);
        dataInicial.setDate(dataInicial.getDate() + 1);
        break;
      default:
        break;
    }

    setDataInicialDraft(formatDateInput(dataInicial));
    setDataFinalDraft(formatDateInput(dataFinal));
  };

  const carregarDetalhamento = useCallback(
    async (config: DetalhamentoConfig) => {
      setDetalheLoading(true);
      setDetalheError(null);
      try {
        const params: Record<string, string | number> = { status };
        if (dataInicial) params.data_inicial = dataInicial;
        if (dataFinal) params.data_final = dataFinal;
        if (responsavel != null) params.responsavel_id = responsavel;
        const p = config.params;
        if (p.metrica) params.metrica = p.metrica;
        if (p.periodo) params.periodo = p.periodo;
        if (p.fonte) params.fonte = p.fonte;
        if (p.solucao) params.solucao = p.solucao;
        if (p.motivo_perda) params.motivo_perda = p.motivo_perda;
        if (typeof p.responsavel_id === "number") params.responsavel_id = p.responsavel_id;
        const res = await api.get<CrmDashboardOportunidadesListResponse>("/crm/dashboard/oportunidades", { params });
        setDetalhePayload(res.data);
      } catch (err) {
        console.error(err);
        setDetalheError("Não foi possível carregar os detalhes.");
        setDetalhePayload(null);
      } finally {
        setDetalheLoading(false);
      }
    },
    [api, dataInicial, dataFinal, responsavel, status]
  );

  const abrirDetalhamento = (config: DetalhamentoConfig) => {
    setDetalheConfig(config);
    setDetalheOpen(true);
    void carregarDetalhamento(config);
  };

  const fecharDetalhamento = useCallback(() => {
    setDetalheOpen(false);
    setDetalheConfig(null);
    setDetalhePayload(null);
    setDetalheError(null);
  }, []);

  useEffect(() => {
    if (!detalheOpen) return undefined;
    const onKey = (ev: KeyboardEvent) => {
      if (ev.key === "Escape") fecharDetalhamento();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [detalheOpen, fecharDetalhamento]);

  /** Cor por status (título da oportunidade + nome do cliente). */
  const classeCorStatusOportunidade = (statusOpp: string): string => {
    const s = statusOpp.trim().toLowerCase();
    if (s === "ganha") return "dashboard-detalhe-opp--ganha";
    if (s === "perdida") return "dashboard-detalhe-opp--perdida";
    if (s === "ativa") return "dashboard-detalhe-opp--ativa";
    if (s === "stand-by" || s === "stand by") return "dashboard-detalhe-opp--standby";
    return "dashboard-detalhe-opp--neutro";
  };

  const serieAnosToolbar = (
    <div
      className="chart-serie-anos"
      role="group"
      aria-label="Anos da série mensal (independente do período da dashboard)"
    >
      <span className="chart-serie-anos-label">Anos</span>
      {anosSerieOpcoes.map((ano) => (
        <button
          key={ano}
          type="button"
          className={`chart-serie-ano-pill${anosSerieGraficos.includes(ano) ? " is-active" : ""}`}
          onClick={() => toggleAnoSerieGrafico(ano)}
        >
          {ano}
        </button>
      ))}
    </div>
  );

  return (
    <Layout>
      <div className="dashboard-page">
      {/* Filters */}
      <section className="dashboard-filters">
        <div className="surface-card dashboard-filters-inner">
          <div className="form-row">
            <label className="form-field">
              <span className="form-label">Período rápido</span>
              <select
                value={periodoRapido}
                onChange={(e) => {
                  const v = e.target.value as FiltroRapidoPeriodo;
                  aplicarPeriodoRapido(v);
                }}
                aria-label="Período rápido"
              >
                <option value="">Selecione…</option>
                <option value="mes_corrente">Mês atual</option>
                <option value="mes_passado">Mês anterior</option>
                <option value="ultimo_trimestre">Último trimestre</option>
                <option value="ano_corrente">Ano corrente</option>
                <option value="ultimos_30_dias">Últimos 30 dias</option>
                <option value="ultimos_7_dias">Últimos 7 dias</option>
              </select>
            </label>

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

            <div className="form-field">
              <span className="form-label">Status</span>
              <div className="status-tabs" role="group" aria-label="Filtrar por status">
                {STATUS_TABS.map(({ value, label, tabClass }) => (
                  <button
                    key={value}
                    type="button"
                    className={`status-tab ${tabClass} ${statusDraft === value ? "active" : ""}`}
                    onClick={() => setStatusDraft(value)}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>

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
          {/* KPI Cards */}
          <section className="dashboard-cards-row">
            <div
              role="button"
              tabIndex={0}
              className="dashboard-card dashboard-card--blue dashboard-card--clickable"
              onClick={() =>
                abrirDetalhamento({
                  titulo: "Oportunidades recebidas",
                  params: { metrica: "recebidas" },
                })
              }
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  abrirDetalhamento({
                    titulo: "Oportunidades recebidas",
                    params: { metrica: "recebidas" },
                  });
                }
              }}
            >
              <div className="dashboard-card-header">
                <span className="dashboard-card-icon" aria-hidden>
                  <svg viewBox="0 0 24 24">
                    <path d="M4 4h16v4H4zM4 10h10v4H4zM4 16h7v4H4z" />
                  </svg>
                </span>
                <strong className="dashboard-card-value">{cards.recebidas}</strong>
              </div>
              <span className="dashboard-card-label">Oportunidades Recebidas</span>
              <div className="dashboard-card-subvalues">
                <span className="dashboard-card-subvalue"><span>12 meses</span><span>{cards.recebidas12m}</span></span>
                <span className="dashboard-card-subvalue"><span>Últ. mês</span><span>{cards.recebidasUltimoMes}</span></span>
                <span className="dashboard-card-subvalue"><span>Mês atual</span><span>{cards.recebidasMesCorrente}</span></span>
                <span className="dashboard-card-subvalue"><span>Últ. 7 dias</span><span>{cards.recebidasUltimos7Dias}</span></span>
              </div>
              {renderKpiMetaLinha(resumoMetas?.recebimento, false)}
              <span className="dashboard-click-hint">Clique para ver detalhes</span>
            </div>

            <div
              role="button"
              tabIndex={0}
              className="dashboard-card dashboard-card--green dashboard-card--clickable"
              onClick={() =>
                abrirDetalhamento({
                  titulo: "Oportunidades ganhas",
                  params: { metrica: "ganhas" },
                })
              }
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  abrirDetalhamento({
                    titulo: "Oportunidades ganhas",
                    params: { metrica: "ganhas" },
                  });
                }
              }}
            >
              <div className="dashboard-card-header">
                <span className="dashboard-card-icon" aria-hidden>
                  <svg viewBox="0 0 24 24">
                    <path d="M5 13l4 4L19 7" />
                  </svg>
                </span>
                <strong className="dashboard-card-value">{cards.ganhas}</strong>
              </div>
              <span className="dashboard-card-label">Oportunidades Ganhas</span>
              <div className="dashboard-card-subvalues">
                <span className="dashboard-card-subvalue"><span>12 meses</span><span>{cards.ganhas12m}</span></span>
                <span className="dashboard-card-subvalue"><span>Últ. mês</span><span>{cards.ganhasUltimoMes}</span></span>
                <span className="dashboard-card-subvalue"><span>Mês atual</span><span>{cards.ganhasMesCorrente}</span></span>
                <span className="dashboard-card-subvalue"><span>Últ. 7 dias</span><span>{cards.ganhasUltimos7Dias}</span></span>
              </div>
              {renderKpiMetaLinha(resumoMetas?.fechamento, false)}
              <span className="dashboard-click-hint">Clique para ver detalhes</span>
            </div>

            <div
              role="button"
              tabIndex={0}
              className="dashboard-card dashboard-card--red dashboard-card--clickable"
              onClick={() =>
                abrirDetalhamento({
                  titulo: "Oportunidades perdidas",
                  params: { metrica: "perdidas" },
                })
              }
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  abrirDetalhamento({
                    titulo: "Oportunidades perdidas",
                    params: { metrica: "perdidas" },
                  });
                }
              }}
            >
              <div className="dashboard-card-header">
                <span className="dashboard-card-icon" aria-hidden>
                  <svg viewBox="0 0 24 24">
                    <path d="M6 6l12 12M18 6L6 18" />
                  </svg>
                </span>
                <strong className="dashboard-card-value">{cards.perdidas}</strong>
              </div>
              <span className="dashboard-card-label">Oportunidades Perdidas</span>
              <div className="dashboard-card-subvalues">
                <span className="dashboard-card-subvalue"><span>12 meses</span><span>{cards.perdidas12m}</span></span>
                <span className="dashboard-card-subvalue"><span>Últ. mês</span><span>{cards.perdidasUltimoMes}</span></span>
                <span className="dashboard-card-subvalue"><span>Mês atual</span><span>{cards.perdidasMesCorrente}</span></span>
                <span className="dashboard-card-subvalue"><span>Últ. 7 dias</span><span>{cards.perdidasUltimos7Dias}</span></span>
              </div>
              <span className="dashboard-click-hint">Clique para ver detalhes</span>
            </div>

            <div
              role="button"
              tabIndex={0}
              className="dashboard-card dashboard-card--purple dashboard-card--clickable"
              onClick={() =>
                abrirDetalhamento({
                  titulo: "Oportunidades ativas",
                  params: { metrica: "ativas" },
                })
              }
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  abrirDetalhamento({
                    titulo: "Oportunidades ativas",
                    params: { metrica: "ativas" },
                  });
                }
              }}
            >
              <div className="dashboard-card-header">
                <span className="dashboard-card-icon" aria-hidden>
                  <svg viewBox="0 0 24 24">
                    <path d="M4 19h16M5 15l4-4 4 4 6-6" />
                  </svg>
                </span>
                <strong className="dashboard-card-value">{formatPercent(cards.taxaConversao)}</strong>
              </div>
              <span className="dashboard-card-label">Taxa de Conversão</span>
              <div className="dashboard-card-subvalues">
                <span className="dashboard-card-subvalue">
                  <span>Oportunidades ativas</span>
                  <span>{cards.ativas}</span>
                </span>
                <span className="dashboard-card-subvalue">
                  <span>Valor pipeline</span>
                  <span>{formatCurrencyBRL(cards.valorAtivas)}</span>
                </span>
                <span className="dashboard-card-subvalue">
                  <span>Forecast</span>
                  <span>{formatCurrencyBRL(cards.forecastAtivas)}</span>
                </span>
              </div>
              <span className="dashboard-click-hint">Clique para ver detalhes</span>
            </div>

            <div
              role="button"
              tabIndex={0}
              className="dashboard-card dashboard-card--orange dashboard-card--clickable"
              onClick={() =>
                abrirDetalhamento({
                  titulo: "MRR incremental (ganhos)",
                  params: { metrica: "mrrIncremental" },
                })
              }
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  abrirDetalhamento({
                    titulo: "MRR incremental (ganhos)",
                    params: { metrica: "mrrIncremental" },
                  });
                }
              }}
            >
              <div className="dashboard-card-header">
                <span className="dashboard-card-icon" aria-hidden>
                  <svg viewBox="0 0 24 24">
                    <path d="M4 18h16V6H4zm4-5h2.5a2 2 0 100-4H9m0 8h2.5a2 2 0 100-4H9" />
                  </svg>
                </span>
                <strong className="dashboard-card-value">{formatCurrencyBRL(cards.mrrIncremental)}</strong>
              </div>
              <span className="dashboard-card-label">MRR Incremental</span>
              <div className="dashboard-card-subvalues">
                <span className="dashboard-card-subvalue"><span>12 meses</span><span>{formatCurrencyBRL(cards.mrrIncremental12m)}</span></span>
                <span className="dashboard-card-subvalue"><span>Últ. mês</span><span>{formatCurrencyBRL(cards.mrrIncrementalUltimoMes)}</span></span>
                <span className="dashboard-card-subvalue"><span>Mês atual</span><span>{formatCurrencyBRL(cards.mrrIncrementalMesCorrente)}</span></span>
                <span className="dashboard-card-subvalue"><span>Últ. 7 dias</span><span>{formatCurrencyBRL(cards.mrrIncrementalUltimos7Dias)}</span></span>
              </div>
              {renderKpiMetaLinha(resumoMetas?.mrrIncremental, true)}
              <span className="dashboard-click-hint">Clique para ver detalhes</span>
            </div>

            <div
              role="button"
              tabIndex={0}
              className="dashboard-card dashboard-card--cyan dashboard-card--clickable"
              onClick={() =>
                abrirDetalhamento({
                  titulo: "Valor de projeto fechado",
                  params: { metrica: "valorProjeto" },
                })
              }
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  abrirDetalhamento({
                    titulo: "Valor de projeto fechado",
                    params: { metrica: "valorProjeto" },
                  });
                }
              }}
            >
              <div className="dashboard-card-header">
                <span className="dashboard-card-icon" aria-hidden>
                  <svg viewBox="0 0 24 24">
                    <path d="M3 7l9-4 9 4-9 4-9-4zm0 5l9 4 9-4M3 17l9 4 9-4" />
                  </svg>
                </span>
                <strong className="dashboard-card-value">{formatCurrencyBRL(cards.valorProjeto)}</strong>
              </div>
              <span className="dashboard-card-label">Valor de Projeto</span>
              <div className="dashboard-card-subvalues">
                <span className="dashboard-card-subvalue"><span>12 meses</span><span>{formatCurrencyBRL(cards.valorProjeto12m)}</span></span>
                <span className="dashboard-card-subvalue"><span>Últ. mês</span><span>{formatCurrencyBRL(cards.valorProjetoUltimoMes)}</span></span>
                <span className="dashboard-card-subvalue"><span>Mês atual</span><span>{formatCurrencyBRL(cards.valorProjetoMesCorrente)}</span></span>
                <span className="dashboard-card-subvalue"><span>Últ. 7 dias</span><span>{formatCurrencyBRL(cards.valorProjetoUltimos7Dias)}</span></span>
              </div>
              {renderKpiMetaLinha(resumoMetas?.valorProjeto, true)}
              <span className="dashboard-click-hint">Clique para ver detalhes</span>
            </div>
          </section>

          {/* Charts */}
          <section className="dashboard-charts-grid">
            <article className="surface-card chart-card chart-card--span-full">
              <div className="chart-card-header chart-serie-header">
                <div>
                  <h2>Evolução mensal</h2>
                  <span className="dashboard-click-hint">Clique em um mês para ver detalhes</span>
                  {serieAnosToolbar}
                </div>
                <div className="chart-metric-tabs" role="tablist" aria-label="Métrica do gráfico mensal">
                  {SERIE_METRIC_TABS.map(({ value, label }) => (
                    <button
                      key={value}
                      type="button"
                      role="tab"
                      aria-selected={metricaSerie === value}
                      className={`chart-metric-tab ${metricaSerie === value ? "active" : ""}`}
                      onClick={() => setMetricaSerie(value)}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </div>
              <div
                className="chart-card-body chart-serie-body"
                onMouseLeave={() => setSerieTooltip(null)}
              >
                {serieMensal.length === 0 ? (
                  <p className="empty-state-text">Nenhum dado encontrado para o período.</p>
                ) : (
                  <div className="chart chart--bars-vertical chart--serie-mensal">
                    {serieMensal.map((item) => {
                      const v = getValorPorMetrica(item, metricaSerie);
                      const basePercent = maxSerieDinamico > 0 ? (Math.abs(v) / maxSerieDinamico) * 100 : 0;
                      const heightPercent = basePercent > 0 ? 12 + basePercent * 0.78 : 0;
                      const metaVal = temMeta ? getMetaSerie(item, metricaSerie) : null;
                      const metaPercent =
                        metaVal != null && metaVal > 0 && maxSerieDinamico > 0
                          ? Math.min(100, (metaVal / maxSerieDinamico) * 100)
                          : null;
                      return (
                        <div
                          key={item.periodo}
                          role="button"
                          tabIndex={0}
                          className="chart-bar-vertical chart-bar-vertical--serie chart-bar-vertical--clickable"
                          onClick={() =>
                            abrirDetalhamento({
                              titulo: `${labelMetricaSerie(metricaSerie)} — ${item.label}`,
                              params: {
                                periodo: item.periodo,
                                metrica: serieMetricaParaDrill(metricaSerie),
                              },
                            })
                          }
                          onKeyDown={(e) => {
                            if (e.key === "Enter" || e.key === " ") {
                              e.preventDefault();
                              abrirDetalhamento({
                                titulo: `${labelMetricaSerie(metricaSerie)} — ${item.label}`,
                                params: {
                                  periodo: item.periodo,
                                  metrica: serieMetricaParaDrill(metricaSerie),
                                },
                              });
                            }
                          }}
                          onMouseEnter={(e) =>
                            setSerieTooltip({
                              x: e.clientX + 12,
                              y: e.clientY + 12,
                              lines: buildSerieTooltipLines(item),
                            })
                          }
                          onMouseMove={(e) =>
                            setSerieTooltip((prev) =>
                              prev ? { ...prev, x: e.clientX + 12, y: e.clientY + 12 } : prev
                            )
                          }
                        >
                          <div className="chart-bar-vertical-track">
                            {metaPercent != null && (
                              <div
                                className="chart-bar-vertical-meta-line"
                                style={{ bottom: `${metaPercent}%` }}
                                aria-hidden
                              />
                            )}
                            <div className="chart-bar-vertical-bar" style={{ height: `${heightPercent}%` }}>
                              <span className="chart-bar-vertical-value">
                                {formatSerieMetricValue(v, metricaSerie)}
                              </span>
                            </div>
                          </div>
                          <span className="chart-bar-vertical-label">{item.label}</span>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </article>

            <article className="surface-card chart-card">
              <div className="chart-card-header">
                <h2>Oportunidades por Fonte</h2>
              </div>
              <div className="chart-card-body">
                {porFonte.length === 0 ? (
                  <p className="empty-state-text">Nenhum dado encontrado para o período.</p>
                ) : (
                  <div className="chart chart--bars-horizontal">
                    {porFonte.map((item) => {
                      const widthPercent = maxPorFonte > 0 ? (item.quantidade / maxPorFonte) * 100 : 0;
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
              </div>
            </article>

            <article className="surface-card chart-card">
              <div className="chart-card-header">
                <h2>Oportunidades por Solução</h2>
              </div>
              <div className="chart-card-body">
                {porSolucao.length === 0 ? (
                  <p className="empty-state-text">Nenhum dado encontrado para o período.</p>
                ) : (
                  <div className="chart chart--bars-horizontal">
                    {porSolucao.map((item) => {
                      const widthPercent = maxPorSolucao > 0 ? (item.quantidade / maxPorSolucao) * 100 : 0;
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
              </div>
            </article>

            <article className="surface-card chart-card">
              <div className="chart-card-header">
                <div>
                  <h2>Ativas por Responsável</h2>
                  <span className="dashboard-click-hint">Clique na legenda para ver detalhes</span>
                </div>
              </div>
              <div className="chart-card-body">
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
                        <div
                          key={item.responsavel}
                          role="button"
                          tabIndex={0}
                          className="chart-donut-legend-item chart-bar-horizontal--clickable"
                          onClick={() => {
                            const rowR = rankings?.responsaveis.find((r) => r.responsavel === item.responsavel);
                            const matchId =
                              rowR != null && rowR.responsavelId != null
                                ? rowR.responsavelId
                                : responsaveis.find((r) => r.nome === item.responsavel)?.id;
                            abrirDetalhamento({
                              titulo: `Ativas — ${item.responsavel}`,
                              params: {
                                metrica: "ativas",
                                responsavel_id: matchId ?? -1,
                              },
                            });
                          }}
                          onKeyDown={(e) => {
                            if (e.key === "Enter" || e.key === " ") {
                              e.preventDefault();
                              const rowR = rankings?.responsaveis.find((r) => r.responsavel === item.responsavel);
                              const matchId =
                                rowR != null && rowR.responsavelId != null
                                  ? rowR.responsavelId
                                  : responsaveis.find((r) => r.nome === item.responsavel)?.id;
                              abrirDetalhamento({
                                titulo: `Ativas — ${item.responsavel}`,
                                params: {
                                  metrica: "ativas",
                                  responsavel_id: matchId ?? -1,
                                },
                              });
                            }
                          }}
                        >
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
              </div>
            </article>

            <article className="surface-card chart-card">
              <div className="chart-card-header">
                <div>
                  <h2>Motivos de Perda</h2>
                  <span className="dashboard-click-hint">Clique em um motivo para ver detalhes</span>
                </div>
              </div>
              <div className="chart-card-body">
                {motivosPerda.length === 0 ? (
                  <p className="empty-state-text">Nenhum motivo de perda encontrado no período.</p>
                ) : (
                  <div className="chart chart--bars-horizontal">
                    {motivosPerda.map((item, idx) => {
                      const widthPercent =
                        maxMotivosQuantidade > 0 ? (item.quantidade / maxMotivosQuantidade) * 100 : 0;
                      return (
                        <div
                          key={`${item.motivo}-${idx}`}
                          role="button"
                          tabIndex={0}
                          className="chart-bar-horizontal chart-bar-horizontal--clickable"
                          title={`${item.quantidade} oportunidade(s) — MRR perdido: ${formatCurrencyBRL(item.mrrPerdido)}`}
                          onClick={() =>
                            abrirDetalhamento({
                              titulo: `Perdas — ${item.motivo}`,
                              params: { metrica: "perdidas", motivo_perda: item.motivo },
                            })
                          }
                          onKeyDown={(e) => {
                            if (e.key === "Enter" || e.key === " ") {
                              e.preventDefault();
                              abrirDetalhamento({
                                titulo: `Perdas — ${item.motivo}`,
                                params: { metrica: "perdidas", motivo_perda: item.motivo },
                              });
                            }
                          }}
                        >
                          <span className="chart-bar-horizontal-label">{item.motivo}</span>
                          <div className="chart-bar-horizontal-track">
                            <div className="chart-bar-horizontal-bar chart-bar-horizontal-bar--loss" style={{ width: `${widthPercent}%` }} />
                          </div>
                          <span className="chart-bar-horizontal-value chart-bar-horizontal-value--with-pct">
                            {item.quantidade}{" "}
                            <span className="chart-bar-horizontal-pct">({formatPercent(item.percentualQuantidade)})</span>
                          </span>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </article>

            {/* Gráfico "Meta x Realizado (Mensal)" suprimido — meta já comparada na Evolução mensal.
            {temMeta && serieMensal.length > 0 && (
              <article className="surface-card chart-card chart-card--meta-real chart-card--span-full">
                <div className="chart-card-header chart-serie-header">
                  <div>
                    <h2>Meta x Realizado (Mensal)</h2>
                    {serieAnosToolbar}
                  </div>
                  <div className="chart-metric-tabs" role="tablist" aria-label="Métrica meta x realizado">
                    {META_REAL_METRIC_TABS.map(({ value, label }) => (
                      <button
                        key={value}
                        type="button"
                        className={`chart-metric-tab ${metricaMetaReal === value ? "active" : ""}`}
                        onClick={() => setMetricaMetaReal(value)}
                      >
                        {label}
                      </button>
                    ))}
                  </div>
                </div>
                <div className="chart-card-body">
                  <div className="chart-meta-real-legend" aria-hidden>
                    <span className="chart-meta-real-legend-item">
                      <span className="chart-meta-real-legend-swatch chart-meta-real-legend-swatch--meta" />
                      Meta
                    </span>
                    <span className="chart-meta-real-legend-item">
                      <span className="chart-meta-real-legend-swatch chart-meta-real-legend-swatch--real" />
                      Realizado
                    </span>
                  </div>
                  <div className="chart-meta-real-scroll">
                    <div className="chart-meta-real-months">
                      {serieMensal.map((it) => {
                        const real = getRealMetaRealizado(it, metricaMetaReal);
                        const meta = getMetaMetaRealizado(it, metricaMetaReal);
                        const gMax = metaRealGlobalMax > 0 ? metaRealGlobalMax : 1;
                        const pctReal = (real / gMax) * 100;
                        const metaNum = meta != null && meta > 0 ? meta : 0;
                        const pctMeta = (metaNum / gMax) * 100;
                        const isMrr = metricaMetaReal === "mrrIncremental";
                        const fmtMetaVal = (n: number) =>
                          isMrr ? formatCurrencyBRL(n) : Math.round(n).toLocaleString("pt-BR");
                        const titleMeta =
                          meta != null && meta > 0 ? `Meta: ${fmtMetaVal(meta)}` : "Sem meta neste mês";
                        return (
                          <div key={it.periodo} className="chart-meta-real-col">
                            <div className="chart-meta-real-cluster">
                              <div className="chart-meta-real-stack" title={titleMeta}>
                                <span className="chart-meta-real-datalabel">
                                  {meta != null && meta > 0 ? formatMetaRealDatalabel(meta, isMrr) : "—"}
                                </span>
                                <div className="chart-meta-real-track">
                                  {metaNum > 0 && (
                                    <div
                                      className="chart-meta-real-bar chart-meta-real-bar--meta"
                                      style={{ height: `${Math.max(pctMeta, 2)}%` }}
                                    />
                                  )}
                                </div>
                              </div>
                              <div className="chart-meta-real-stack" title={`Realizado: ${fmtMetaVal(real)}`}>
                                <span className="chart-meta-real-datalabel">
                                  {formatMetaRealDatalabel(real, isMrr)}
                                </span>
                                <div className="chart-meta-real-track">
                                  {real > 0 && (
                                    <div
                                      className="chart-meta-real-bar chart-meta-real-bar--real"
                                      style={{ height: `${Math.max(pctReal, 2)}%` }}
                                    />
                                  )}
                                </div>
                              </div>
                            </div>
                            <span className="chart-meta-real-label">{it.label}</span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>
              </article>
            )}
            */}

            {rankings && (
              <article className="surface-card chart-card chart-card--span-full">
                <div className="chart-card-header">
                  <h2>Análise por Dimensão</h2>
                </div>
                <div className="chart-card-body">
                  <div className="dashboard-dimensao-tabs" role="tablist" aria-label="Dimensão da análise">
                    <button
                      type="button"
                      className={`dashboard-dimensao-tab ${dimensaoTab === "responsaveis" ? "active" : ""}`}
                      onClick={() => setDimensaoTab("responsaveis")}
                    >
                      Responsáveis
                    </button>
                    <button
                      type="button"
                      className={`dashboard-dimensao-tab ${dimensaoTab === "fontes" ? "active" : ""}`}
                      onClick={() => setDimensaoTab("fontes")}
                    >
                      Fontes
                    </button>
                    <button
                      type="button"
                      className={`dashboard-dimensao-tab ${dimensaoTab === "solucoes" ? "active" : ""}`}
                      onClick={() => setDimensaoTab("solucoes")}
                    >
                      Soluções
                    </button>
                  </div>
                  <div className="dashboard-ranking-table-wrap">
                    {dimensaoTab === "responsaveis" && (
                      <table className="dashboard-ranking-table">
                        <thead>
                          <tr>
                            <th>Nome</th>
                            <th>Recebidas</th>
                            <th>Ganhas</th>
                            <th>Perdidas</th>
                            <th>Ativas</th>
                            <th>Conversão</th>
                            <th>MRR</th>
                            <th>Projeto</th>
                          </tr>
                        </thead>
                        <tbody>
                          {rankings.responsaveis.map((row) => (
                            <tr
                              key={`${row.responsavel}-${row.responsavelId ?? "x"}`}
                              className="dashboard-ranking-row--clickable"
                              tabIndex={0}
                              onClick={() =>
                                abrirDetalhamento({
                                  titulo: `Responsável — ${row.responsavel}`,
                                  params: {
                                    responsavel_id: row.responsavelId ?? -1,
                                  },
                                })
                              }
                              onKeyDown={(e) => {
                                if (e.key === "Enter" || e.key === " ") {
                                  e.preventDefault();
                                  abrirDetalhamento({
                                    titulo: `Responsável — ${row.responsavel}`,
                                    params: {
                                      responsavel_id: row.responsavelId ?? -1,
                                    },
                                  });
                                }
                              }}
                            >
                              <td>{row.responsavel}</td>
                              <td>{row.recebidas}</td>
                              <td>{row.ganhas}</td>
                              <td>{row.perdidas}</td>
                              <td>{row.ativas}</td>
                              <td>{formatPercent(row.taxaConversao)}</td>
                              <td>{formatCurrencyBRL(row.mrrIncremental)}</td>
                              <td>{formatCurrencyBRL(row.valorProjeto)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}
                    {dimensaoTab === "fontes" && (
                      <table className="dashboard-ranking-table">
                        <thead>
                          <tr>
                            <th>Nome</th>
                            <th>Recebidas</th>
                            <th>Ganhas</th>
                            <th>Perdidas</th>
                            <th>Conversão</th>
                            <th>MRR</th>
                            <th>Projeto</th>
                          </tr>
                        </thead>
                        <tbody>
                          {rankings.fontes.map((row) => (
                            <tr
                              key={row.fonte}
                              className="dashboard-ranking-row--clickable"
                              tabIndex={0}
                              onClick={() =>
                                abrirDetalhamento({
                                  titulo: `Fonte — ${row.fonte}`,
                                  params: { fonte: row.fonte },
                                })
                              }
                              onKeyDown={(e) => {
                                if (e.key === "Enter" || e.key === " ") {
                                  e.preventDefault();
                                  abrirDetalhamento({
                                    titulo: `Fonte — ${row.fonte}`,
                                    params: { fonte: row.fonte },
                                  });
                                }
                              }}
                            >
                              <td>{row.fonte}</td>
                              <td>{row.recebidas}</td>
                              <td>{row.ganhas}</td>
                              <td>{row.perdidas}</td>
                              <td>{formatPercent(row.taxaConversao)}</td>
                              <td>{formatCurrencyBRL(row.mrrIncremental)}</td>
                              <td>{formatCurrencyBRL(row.valorProjeto)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}
                    {dimensaoTab === "solucoes" && (
                      <table className="dashboard-ranking-table">
                        <thead>
                          <tr>
                            <th>Nome</th>
                            <th>Recebidas</th>
                            <th>Ganhas</th>
                            <th>Perdidas</th>
                            <th>Conversão</th>
                            <th>MRR</th>
                            <th>Projeto</th>
                          </tr>
                        </thead>
                        <tbody>
                          {rankings.solucoes.map((row) => (
                            <tr
                              key={row.solucao}
                              className="dashboard-ranking-row--clickable"
                              tabIndex={0}
                              onClick={() =>
                                abrirDetalhamento({
                                  titulo: `Solução — ${row.solucao}`,
                                  params: { solucao: row.solucao },
                                })
                              }
                              onKeyDown={(e) => {
                                if (e.key === "Enter" || e.key === " ") {
                                  e.preventDefault();
                                  abrirDetalhamento({
                                    titulo: `Solução — ${row.solucao}`,
                                    params: { solucao: row.solucao },
                                  });
                                }
                              }}
                            >
                              <td>{row.solucao}</td>
                              <td>{row.recebidas}</td>
                              <td>{row.ganhas}</td>
                              <td>{row.perdidas}</td>
                              <td>{formatPercent(row.taxaConversao)}</td>
                              <td>{formatCurrencyBRL(row.mrrIncremental)}</td>
                              <td>{formatCurrencyBRL(row.valorProjeto)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}
                  </div>
                </div>
              </article>
            )}
          </section>

          {serieTooltip && (
            <div
              className="chart-serie-tooltip"
              style={{ position: "fixed", left: serieTooltip.x, top: serieTooltip.y, zIndex: 200 }}
              role="tooltip"
            >
              {serieTooltip.lines.map((line, i) => (
                <div
                  key={`${line}-${i}`}
                  className={i === 0 ? "chart-serie-tooltip-line chart-serie-tooltip-line--title" : "chart-serie-tooltip-line"}
                >
                  {line}
                </div>
              ))}
            </div>
          )}

          {detalheOpen && (
            <>
              <div
                className="dashboard-detalhe-backdrop"
                onClick={fecharDetalhamento}
                aria-hidden="true"
              />
              <aside
                className="dashboard-detalhe-panel"
                role="dialog"
                aria-modal="true"
                aria-labelledby="dashboard-detalhe-titulo-principal"
              >
                <header className="dashboard-detalhe-header">
                  <div>
                    <h2 id="dashboard-detalhe-titulo-principal">Detalhamento de Oportunidades</h2>
                    {detalheConfig && (
                      <p className="dashboard-detalhe-subtitulo">{formatarTituloDetalhamento(detalheConfig)}</p>
                    )}
                  </div>
                  <button type="button" className="dashboard-detalhe-close" onClick={fecharDetalhamento} aria-label="Fechar">
                    ×
                  </button>
                </header>
                {!detalheLoading && detalhePayload && (
                  <div className="dashboard-detalhe-resumo">
                    <div>
                      Quantidade
                      <strong>{detalhePayload.resumo.quantidade.toLocaleString("pt-BR")}</strong>
                    </div>
                    <div>
                      MRR total
                      <strong>{formatCurrencyBRL(detalhePayload.resumo.mrrTotal)}</strong>
                    </div>
                    <div>
                      Projeto total
                      <strong>{formatCurrencyBRL(detalhePayload.resumo.valorProjetoTotal)}</strong>
                    </div>
                    <div>
                      Forecast total
                      <strong>{formatCurrencyBRL(detalhePayload.resumo.forecastTotal)}</strong>
                    </div>
                    <div>
                      Ticket médio
                      <strong>{formatCurrencyBRL(detalhePayload.resumo.ticketMedio)}</strong>
                    </div>
                  </div>
                )}
                <div className="dashboard-detalhe-body">
                  {detalheLoading && <p className="dashboard-detalhe-muted">Carregando oportunidades...</p>}
                  {!detalheLoading && detalheError && <p className="dashboard-detalhe-muted">{detalheError}</p>}
                  {!detalheLoading && !detalheError && detalhePayload && detalhePayload.total === 0 && (
                    <p className="dashboard-detalhe-muted">Nenhuma oportunidade encontrada para este recorte.</p>
                  )}
                  {!detalheLoading && !detalheError && detalhePayload && detalhePayload.itens.length > 0 && (
                    <table className="dashboard-detalhe-table">
                      <thead>
                        <tr>
                          <th>Oportunidade</th>
                          <th>Resp.</th>
                          <th>Fonte</th>
                          <th>Solução</th>
                          <th>MRR</th>
                          <th>Projeto</th>
                          <th>Forecast</th>
                          <th />
                        </tr>
                      </thead>
                      <tbody>
                        {detalhePayload.itens.map((row) => {
                          const corStatus = classeCorStatusOportunidade(row.status);
                          return (
                          <tr key={row.id}>
                            <td className="dashboard-detalhe-opp-cell">
                              <span className={`dashboard-detalhe-opp-titulo ${corStatus}`}>{row.nome}</span>
                              {row.cliente?.trim() ? (
                                <span className={`dashboard-detalhe-opp-cliente ${corStatus}`}>{row.cliente.trim()}</span>
                              ) : null}
                            </td>
                            <td>{row.responsavel ?? "—"}</td>
                            <td>{row.fonte ?? "—"}</td>
                            <td>{row.solucao ?? "—"}</td>
                            <td>{row.valorMrr != null ? formatCurrencyBRL(row.valorMrr) : "—"}</td>
                            <td>{row.valorProjeto != null ? formatCurrencyBRL(row.valorProjeto) : "—"}</td>
                            <td>{row.forecast != null ? formatCurrencyBRL(row.forecast) : "—"}</td>
                            <td>
                              <Link to={`/oportunidades/${row.id}`}>Abrir</Link>
                            </td>
                          </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  )}
                </div>
              </aside>
            </>
          )}
        </>
      )}
      </div>
    </Layout>
  );
};

export default DashboardPage;
