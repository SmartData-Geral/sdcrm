import React from "react";
import ProposalBlockRenderer from "./ProposalBlockRenderer";

interface Props {
  config: Record<string, unknown>;
}

const ProposalPreview: React.FC<Props> = ({ config }) => {
  const escopoConfig = (config.escopo_inicial as Record<string, unknown>) ?? {};
  const clientesConfig = (config.clientes as Record<string, unknown>) ?? {};
  const sections = [
    { tipo: "hero", titulo: "Hero", dados: (config.hero as Record<string, unknown>) ?? null },
    { tipo: "apresentacao", titulo: "Apresentação", dados: (config.apresentacao as Record<string, unknown>) ?? null },
    { tipo: "metodologia", titulo: "Diferenciais", dados: (config.metodologia as Record<string, unknown>) ?? null },
    {
      tipo: "escopo_inicial",
      titulo: String(escopoConfig.titulo ?? "Fases do projeto"),
      dados: (config.escopo_inicial as Record<string, unknown>) ?? null,
    },
    { tipo: "valores_projeto", titulo: "Valores Projeto", dados: (config.valores_projeto as Record<string, unknown>) ?? null },
    { tipo: "valores_planos", titulo: "Valores Planos", dados: (config.valores_planos as Record<string, unknown>) ?? null },
    {
      tipo: "clientes",
      titulo: String(clientesConfig.titulo ?? "Clientes"),
      subtitulo: String(clientesConfig.subtitulo ?? ""),
      dados: (config.clientes as Record<string, unknown>) ?? null,
    },
    { tipo: "cta_final", titulo: "CTA Final", dados: (config.cta_final as Record<string, unknown>) ?? null },
  ];
  const visibilidade = (config.visibilidade as Record<string, unknown>) ?? {};

  return (
    <div className="proposal-preview-landing">
      <div className="proposal-preview">
        {sections
          .filter((s) => visibilidade[s.tipo] !== false)
          .map((section) => (
            <ProposalBlockRenderer
              key={section.tipo}
              tipo={section.tipo}
              titulo={section.titulo}
              subtitulo={section.subtitulo as string | undefined}
              dados={section.dados}
            />
          ))}
      </div>
    </div>
  );
};

export default ProposalPreview;

