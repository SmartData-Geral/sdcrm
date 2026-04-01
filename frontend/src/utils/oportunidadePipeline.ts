export type PipelineKey = "default" | "upsell";

export interface OportunidadePipelineContext {
  pipeline: PipelineKey;
  sectionLabel: string;
  listPath: string;
  kanbanPath: string;
  detailPath: (opoId: number | string) => string;
  newFromQueryPath: string;
  contractNewPath: (opoId: number | string) => string;
}

const DEFAULT_CONTEXT: OportunidadePipelineContext = {
  pipeline: "default",
  sectionLabel: "CRM",
  listPath: "/oportunidades",
  kanbanPath: "/oportunidades-kanban",
  detailPath: (opoId) => `/oportunidades/${opoId}`,
  newFromQueryPath: "/oportunidades",
  contractNewPath: (opoId) => `/oportunidades/${opoId}/contrato/novo`,
};

const UPSELL_CONTEXT: OportunidadePipelineContext = {
  pipeline: "upsell",
  sectionLabel: "Upsell",
  listPath: "/upsell/oportunidades",
  kanbanPath: "/upsell/oportunidades-kanban",
  detailPath: (opoId) => `/upsell/oportunidades/${opoId}`,
  newFromQueryPath: "/upsell/oportunidades",
  contractNewPath: (opoId) => `/upsell/oportunidades/${opoId}/contrato/novo`,
};

export function getOportunidadePipelineContext(pathname: string): OportunidadePipelineContext {
  return pathname.startsWith("/upsell") ? UPSELL_CONTEXT : DEFAULT_CONTEXT;
}
