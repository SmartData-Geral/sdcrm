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
  ptlPadrao: boolean;
  ptlConfigJson: Record<string, unknown> | null;
  ptlSchemaJson: Record<string, unknown> | null;
  ptlAtivo: boolean;
}

export interface PropostaBlocoItem {
  pblId: number;
  pblTipo: string;
  pblTitulo: string | null;
  pblSubtitulo: string | null;
  pblOrdem: number;
  pblVisivel: boolean;
  pblDadosJson: Record<string, unknown> | null;
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

export interface PropostaBlocoPadraoItem {
  pbpId: number;
  pbpEmpId: number;
  pbpPtlId: number | null;
  pbpTipo: string;
  pbpTitulo: string | null;
  pbpSubtitulo: string | null;
  pbpOrdem: number;
  pbpVisivel: boolean;
  pbpDadosJson: Record<string, unknown> | null;
  pbpAtivo: boolean;
}

