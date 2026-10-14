export interface MetaAdsLinha {
  mcgId: number | null;
  nome: string;
  status: string | null;
  macId: number | null;
  investimento: number;
  impressoes: number;
  cliques: number;
  leadsMeta: number;
  leadsCrm: number;
  vendas: number;
  mrr: number;
  projeto: number;
  ctr: number | null;
  cpc: number | null;
  cpl: number | null;
  cac: number | null;
  retorno: number | null;
}

export interface MetaAdsPainel {
  temConta: boolean;
  total: MetaAdsLinha;
  campanhas: MetaAdsLinha[];
  naoIdentificada: MetaAdsLinha | null;
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
