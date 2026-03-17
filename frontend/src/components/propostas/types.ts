export type TipoProposta = "projeto" | "planos" | "hibrida";

export interface PropostaItem {
  prpId: number;
  prpEmpId: number;
  prpOpoId: number;
  prpTplId: number | null;
  prpTitulo: string;
  prpTipo: TipoProposta;
  prpStatus: string;
  prpTokenPublico: string;
  prpVersaoAtual: number | null;
  prpUsuResponsavelId: number | null;
  prpNomeContato: string | null;
  prpEmailContato: string | null;
  prpWhatsappContato: string | null;
  prpObservacaoInterna: string | null;
  prpJsonConfiguracao: Record<string, unknown> | null;
  prpHtmlRenderizado: string | null;
  prpPublicadaEm: string | null;
  prpAceitaEm: string | null;
}

export interface PropostaTemplateItem {
  ptlId: number;
  ptlNome: string;
  ptlTipoSolucao: string | null;
  ptlTipoProposta: TipoProposta;
  ptlPrpOrigemId: number | null;
  ptlAtivo: boolean;
  ptlPadrao: boolean;
  ptlConfigJson: Record<string, unknown> | null;
  ptlDataCriacao?: string | null;
}

export interface PropostaVersaoItem {
  prvId: number;
  prvNumero: number;
  prvTitulo: string | null;
  prvPublicada: boolean;
  prvDataPublicacao: string | null;
}

export interface PropostaEventoItem {
  pevId: number;
  pevTipo: string;
  pevIp: string | null;
  pevDataEvento: string;
}

