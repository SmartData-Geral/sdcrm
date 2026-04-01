export interface ContratoModeloItem {
  ctmId: number;
  ctmEmpId: number;
  ctmNome: string;
  ctmDescricao: string | null;
  ctmAtivo: boolean;
  ctmDataCriacao: string;
  ctmDataAtualizacao: string | null;
}

export interface ContratoModeloClausulaItem {
  cmcId: number;
  cmcEmpId: number;
  cmcCtmId: number;
  cmcTitulo: string;
  cmcTextoPadrao: string;
  cmcUtilizarPadrao: boolean;
  cmcOrdem: number;
  cmcAtivo: boolean;
  cmcDataCriacao: string;
  cmcDataAtualizacao: string | null;
}

export interface ContratoModeloClausulaVariacaoItem {
  cmvId: number;
  cmvEmpId: number;
  cmvCmcId: number;
  cmvNome: string | null;
  cmvTitulo: string | null;
  cmvTexto: string;
  cmvAtivo: boolean;
  cmvDataCriacao: string;
  cmvDataAtualizacao: string | null;
}

