export type NivelLinha = "campanha" | "conjunto" | "anuncio" | "nao_identificada" | "total";

export interface MetaAdsLinha {
  nivel: NivelLinha;
  id: number | null;
  mcgId: number | null;
  nome: string;
  status: string | null;
  macId: number | null;
  investimento: number;
  impressoes: number;
  cliques: number;
  leadsMeta: number;
  leadsCrm: number;
  mqls: number;
  oportunidades: number;
  vendas: number;
  mrr: number;
  projeto: number;
  ctr: number | null;
  cpc: number | null;
  cpl: number | null;
  custoLeadCrm: number | null;
  custoMql: number | null;
  custoOportunidade: number | null;
  cac: number | null;
  retorno: number | null;
  horasPrimeiroContato: number | null;
  filhos: MetaAdsLinha[];
}

export interface MetaAdsRevisaoItem {
  opoId: number;
  opoTitulo: string;
  opoNomeContato: string | null;
  opoDataRecebimento: string | null;
}

export interface MetaAdsPainel {
  temConta: boolean;
  total: MetaAdsLinha;
  campanhas: MetaAdsLinha[];
  naoIdentificada: MetaAdsLinha | null;
  cobertura: number | null;
  revisaoOrigem: MetaAdsRevisaoItem[];
}

export interface MetaAdsSerieDia {
  data: string;
  investimento: number;
  leadsMeta: number;
  leadsCrm: number;
}

export interface MetaAdsLeadItem {
  opoId: number;
  opoTitulo: string;
  opoNomeContato: string | null;
  opoDataRecebimento: string | null;
  opoStatusFechamento: string | null;
  opoValorFechado: number | null;
}

export interface MetaAdsCampanhaDetalhe {
  campanha: MetaAdsLinha;
  serie: MetaAdsSerieDia[];
  leads: MetaAdsLeadItem[];
}

export interface MetaAdsResumo {
  temConta: boolean;
  investimento: number;
  leadsCrm: number;
  vendas: number;
  cpl: number | null;
  cac: number | null;
  retorno: number | null;
}

export interface MetaAdsContaOpcao {
  macId: number;
  macNome: string;
}

export const moeda = (v: number | null | undefined) =>
  v == null ? "—" : v.toLocaleString("pt-BR", { style: "currency", currency: "BRL", minimumFractionDigits: 2 });

export const inteiro = (v: number) => v.toLocaleString("pt-BR");

export const percentual = (v: number | null) =>
  v == null ? "—" : `${v.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}%`;

export const multiplicador = (v: number | null) =>
  v == null ? "—" : `${v.toLocaleString("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 })}×`;

export const dataBR = (v: string | null) => {
  if (!v) return "—";
  const [a, m, d] = v.slice(0, 10).split("-");
  return `${d}/${m}/${a}`;
};

const STATUS_CAMPANHA: Record<string, string> = {
  ACTIVE: "Ativa",
  PAUSED: "Pausada",
  CAMPAIGN_PAUSED: "Pausada",
  ARCHIVED: "Arquivada",
  DELETED: "Excluída",
  IN_PROCESS: "Em análise",
  WITH_ISSUES: "Com problemas",
};

export const rotuloStatusCampanha = (s: string | null) => (s ? STATUS_CAMPANHA[s] ?? s : "—");

const isoLocal = (d: Date) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;

export function intervaloAnoCorrente(): { inicio: string; fim: string } {
  const hoje = new Date();
  return { inicio: `${hoje.getFullYear()}-01-01`, fim: isoLocal(hoje) };
}

export function intervaloMesCorrente(): { inicio: string; fim: string } {
  const hoje = new Date();
  return { inicio: isoLocal(new Date(hoje.getFullYear(), hoje.getMonth(), 1)), fim: isoLocal(hoje) };
}

export const horas = (v: number | null | undefined) =>
  v == null ? "—" : v.toLocaleString("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });

export interface MonitorConfig {
  etapaMqlId: number | null;
  etapaOportunidadeId: number | null;
  cplFator: number;
  gastoSemLead: number;
  frequenciaMax: number;
  quedaCtrPct: number;
  horasSemContato: number;
  gastoMinRanking: number;
  metaCpl: number;
  metaTaxaMql: number;
  horaResumo: number;
  alertas: Record<string, boolean>;
}

export interface MetaAdsAlerta {
  malId: number;
  malTipo: string;
  malChave: string;
  malStatus: string;
  malMensagem: string;
  malDados: Record<string, unknown> | null;
  malPrimeiroEm: string;
  malUltimoEm: string;
  malResolvidoEm: string | null;
  alvoNome: string | null;
}

export const ROTULO_ALERTA: Record<string, string> = {
  cpl: "CPL fora do padrão",
  gasto: "Gasto sem retorno",
  frequencia: "Criativo saturando",
  ctr: "Queda de CTR",
  parado: "Anúncio parado",
  sem_contato: "Lead sem contato",
};

export interface ResumoTotais {
  investimento: number;
  impressoes: number;
  cliques: number;
  leadsMeta: number;
  leadsCrm: number;
  mqls: number;
  oportunidades: number;
  vendas: number;
  cpl: number | null;
  custoMql: number | null;
  ctr: number | null;
}

export interface ResumoPeriodo extends ResumoTotais {
  inicio: string;
  fim: string;
  dias: number;
  /** So no periodo anterior (resumos gerados antes desta versao nao tem). */
  cobertura?: number | null;
}

export interface ResumoItem extends ResumoTotais {
  id: number | null;
  mcgId: number | null;
  nome: string;
  status: string | null;
}

export interface ResumoDados {
  periodo: ResumoPeriodo;
  ultimos7: ResumoPeriodo;
  comparacao: {
    /** Janela da base da variacao: os 7 dias antes do periodo anterior. */
    base?: { inicio: string; fim: string; dias: number };
    mediaDiariaPeriodo: Record<string, number>;
    mediaDiariaBase?: Record<string, number>;
    mediaDiariaUltimos7: Record<string, number>;
    variacaoPct: Record<string, number | null>;
  };
  campanhas: ResumoItem[];
  anuncios: ResumoItem[];
  melhores: ResumoItem[];
  piores: ResumoItem[];
  cobertura: number | null;
  horasPrimeiroContato: number | null;
  alertasAbertos: number;
}

export interface ResumoDiario {
  mrsId: number;
  mrsData: string;
  mrsInicio: string;
  mrsFim: string;
  mrsDados: ResumoDados;
  mrsLeitura: string | null;
  mrsAviso: string | null;
  mrsGeradoEm: string;
}

export interface ResumoDiarioItem {
  mrsData: string;
  mrsGeradoEm: string;
}

export const hojeISO = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
};

export const mensagemErroApi = (err: any, padrao: string) => {
  const detail = err?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail[0]?.msg) return String(detail[0].msg).replace(/^Value error, /, "");
  return padrao;
};

// ---- Cockpit de campanhas (espelha backend/schemas/meta_ads.py) ----

export type CockpitSelo = "bom" | "atencao" | "ruim" | "sem_dados";
export type CockpitQuadrante = "escalar" | "otimizar_custo" | "rever_publico" | "pausar" | "aguardar_dados";
export type CockpitEtapaChave = "impressoes" | "cliques" | "leads" | "crm" | "mql" | "oportunidade" | "contrato";

export interface CockpitMetas {
  cpl: number;
  taxaMql: number;
  custoMqlImplicito: number;
  cplFator: number;
}

export interface CockpitSelos {
  cpl: CockpitSelo;
  taxaMql: CockpitSelo;
  custoMql: CockpitSelo;
  saude: CockpitSelo;
}

export interface CockpitEtapa {
  chave: CockpitEtapaChave;
  quantidade: number;
  taxa: number | null;
  custo: number | null;
  gargalo: boolean;
}

export interface CockpitPonto {
  inicio: string;
  fim: string;
  rotulo: string;
  investimento: number;
  impressoes: number;
  cliques: number;
  leadsMeta: number;
  leadsCrm: number;
  mqls: number;
  cpl: number | null;
}

export interface CockpitCriativo {
  id: number | null;
  mcgId: number | null;
  nome: string;
  campanha: string;
  status: string | null;
  ativo: boolean;
  investimento: number;
  leadsMeta: number;
  leadsCrm: number;
  mqls: number;
  cpl: number | null;
  taxaMql: number | null;
  quadrante: CockpitQuadrante;
  motivo: "sem_lead" | "sem_crm" | null;
  amostraPequena: boolean;
  recomendacao: string;
  porque: string;
}

export interface CockpitOperacao {
  cobertura: number | null;
  horasPrimeiroContato: number | null;
  alertasAbertos: number;
  origemRevisar: number;
}

export interface MetaAdsCockpit {
  temConta: boolean;
  inicio: string;
  fim: string;
  metas: CockpitMetas;
  total: MetaAdsLinha;
  taxaMql: number | null;
  anterior: MetaAdsLinha;
  anteriorInicio: string;
  anteriorFim: string;
  anteriorTemDados: boolean;
  selos: CockpitSelos;
  funil: CockpitEtapa[];
  gargalo: "mql" | "oportunidade" | "contrato" | null;
  fraseGargalo: string | null;
  intervalo: "mes" | "semana";
  serie: CockpitPonto[];
  criativos: CockpitCriativo[];
  operacao: CockpitOperacao;
}

export const ROTULO_SELO: Record<CockpitSelo, string> = {
  bom: "Bom",
  atencao: "Atenção",
  ruim: "Ruim",
  sem_dados: "Sem dados",
};

export const ROTULO_ETAPA: Record<CockpitEtapaChave, string> = {
  impressoes: "Viram o anúncio",
  cliques: "Clicaram",
  leads: "Viraram lead",
  crm: "Chegaram ao CRM",
  mql: "Viraram MQL",
  oportunidade: "Oportunidade",
  contrato: "Contrato",
};

/** Hoje e os n-1 dias anteriores. */
export function intervaloUltimosDias(n: number): { inicio: string; fim: string } {
  const hoje = new Date();
  const ini = new Date(hoje.getFullYear(), hoje.getMonth(), hoje.getDate() - (n - 1));
  return { inicio: isoLocal(ini), fim: isoLocal(hoje) };
}

// ---- Leitura do analista e chat (espelha backend/schemas/meta_ads.py) ----

export interface CockpitLeituraEstruturada {
  manchete: string;
  funciona: string;
  problema: string;
  olharAgora: string;
}

export interface MetaAdsCockpitLeitura {
  leitura: CockpitLeituraEstruturada | null;
  texto: string | null;
  geradoEm: string | null;
  desatualizada: boolean;
  aviso: string | null;
  iaDisponivel: boolean;
}

export interface CockpitRecorte {
  inicio: string;
  fim: string;
  macId: string;
  somenteAtivas: boolean;
}

export interface CockpitTroca {
  pergunta: string;
  resposta: string;
}

export interface MetaAdsCockpitResposta {
  resposta: string;
  restantesHoje: number;
}

// Datas do backend vêm em UTC "naive" (sem offset); sem designador de fuso, interpreta como UTC.
export function dataHoraUtc(iso: string | null | undefined): string {
  if (!iso) return "";
  const temFuso = /(Z|[+-]\d{2}:?\d{2})$/i.test(iso);
  const d = new Date(temFuso ? iso : `${iso}Z`);
  if (Number.isNaN(d.getTime())) return "";
  return d
    .toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit", hour12: false })
    .replace(",", "");
}
