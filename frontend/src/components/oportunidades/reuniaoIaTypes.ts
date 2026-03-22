export type RanStatus = "pendente" | "processando" | "concluido" | "erro";
export type TemperaturaSugestao = "frio" | "morno" | "quente";

export interface ReuniaoArquivoResumo {
  nome: string;
  mime?: string | null;
  extensao?: string | null;
  tamanho_bytes: number;
  leitura_sucesso: boolean;
  mensagem?: string | null;
  conteudo_extraido?: string | null;
}

export interface ReuniaoAnaliseItem {
  ranId: number;
  ranEmpId: number;
  ranOpoId: number;
  ranUsuId: number | null;
  ranTranscricao: string | null;
  ranArquivosResumo: ReuniaoArquivoResumo[] | null;
  ranResumo: string | null;
  ranFeedbackIa: string | null;
  ranLeadScoreSugerido: number | null;
  ranTemperaturaSugerida: TemperaturaSugestao | null;
  ranDoresOportunidadesSugeridas: string | null;
  ranObservacoesSugeridas: string | null;
  ranProximosPassosSugeridos: string | null;
  ranPromptUtilizado: string | null;
  ranRespostaJson: Record<string, unknown> | null;
  ranModeloIa: string | null;
  ranProcessadoEm: string | null;
  ranStatus: RanStatus;
  ranAtivo: boolean;
  ranDataCriacao: string;
  ranDataAtualizacao: string | null;
}
