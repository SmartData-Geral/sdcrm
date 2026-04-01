export interface ContratoItem {
  ctrId: number;
  ctrEmpId: number;
  ctrOpoId: number | null;
  ctrCtmId: number;
  ctrNome: string;
  ctrStatus: "pronto" | "assinado" | string;
  ctrTokenPublico: string | null;

  ctrRazaoSocial: string;
  ctrCnpj: string;
  ctrEndereco: string;
  ctrResponsavelNome: string;
  ctrResponsavelCpf: string;
  ctrObjetoContrato: string;
  ctrValorContrato: number;
  ctrFormaPagamento: string;
  ctrVigencia: string;
  ctrDataInicio: string; // date => string from API
  ctrForo: string;
  ctrReajuste: string | null;

  ctrHtmlSnapshot: string | null;
  ctrPdfPath: string | null;
}

export interface ContratoClausulaVariacao {
  cmvId: number;
  cmvNome: string | null;
  cmvTitulo: string | null;
  cmvTexto: string;
  cmvAtivo: boolean;
}

export interface ContratoClausula {
  cclId: number;
  cclCmcId: number;
  cclCmvId: number | null;
  cclTitulo: string;
  cclTexto: string;
  cclUtilizar: boolean;
  cclOrdemBase: number;
  cclOrdemFinal: number;
  cclAtivo: boolean;

  cmcTituloPadrao: string;
  cmcTextoPadrao: string;

  variacoes: ContratoClausulaVariacao[];
}

