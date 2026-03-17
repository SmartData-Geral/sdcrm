import React from "react";

interface Props {
  tipo: string;
  titulo?: string | null;
  subtitulo?: string | null;
  dados?: Record<string, unknown> | null;
}

const renderList = (value: unknown) => {
  if (!Array.isArray(value)) return null;
  const items = value.filter((item) => typeof item === "string");
  if (!items.length) return null;
  return (
    <ul className="proposal-render-list">
      {items.map((item) => (
        <li key={`${item}`}>{item}</li>
      ))}
    </ul>
  );
};

const ProposalBlockRenderer: React.FC<Props> = ({ tipo, titulo, subtitulo, dados }) => {
  const data = dados ?? {};
  if (tipo === "hero") {
    return (
      <section className="proposal-render-hero">
        <h2>{String((data.titulo as string) ?? titulo ?? "Proposta Comercial")}</h2>
        <p>{String((data.subtitulo as string) ?? subtitulo ?? "")}</p>
      </section>
    );
  }
  if (tipo === "metodologia") {
    const sectionTitle = String((data.titulo as string) ?? titulo ?? "Diferenciais");
    const sectionSubtitle = String(
      (data.subtitulo as string) ??
        "Soluções pensadas para gerar eficiência, integração e resultado real para a sua operação.",
    );
    const rawItens = Array.isArray(data.itens) ? data.itens : [];
    const itens = rawItens.map((item, idx) => {
      if (typeof item === "string") {
        return { titulo: item, descricao: "", icone: undefined, ordem: idx + 1 };
      }
      const obj = (item ?? {}) as Record<string, unknown>;
      return {
        titulo: String(obj.titulo ?? ""),
        descricao: String(obj.descricao ?? ""),
        icone: String(obj.icone ?? ""),
        ordem: typeof obj.ordem === "number" ? obj.ordem : idx + 1,
      };
    });
    const iconFor = (key: string | undefined) => {
      const raw = (key ?? "").toLowerCase().trim();
      if (!raw) return "◆";
      if (raw.includes("exper")) return "★";
      if (raw.includes("personal")) return "⚙";
      if (raw.includes("integr")) return "🔗";
      if (raw.includes("ia") || raw.includes("auto")) return "⚡";
      return "◆";
    };
    return (
      <section className="proposal-render-section">
        <h3>{sectionTitle}</h3>
        <p>{sectionSubtitle}</p>
        <div className="proposal-render-grid">
          {itens.map((item, idx) => (
            <article className="proposal-render-card" key={`diff-${idx}`}>
              <div style={{ marginBottom: "0.25rem" }}>
                <span
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    justifyContent: "center",
                    width: 32,
                    height: 32,
                    borderRadius: 10,
                    background: "linear-gradient(145deg, #fee2e2, #fef3c7)",
                    fontSize: "1.1rem",
                  }}
                >
                  {iconFor(item.icone)}
                </span>
              </div>
              <h4>{item.titulo || "Diferencial"}</h4>
              {item.descricao ? <p>{item.descricao}</p> : null}
            </article>
          ))}
        </div>
      </section>
    );
  }
  if (tipo === "escopo_inicial") {
    const cards = Array.isArray(data.cards) ? data.cards : [];
    return (
      <section className="proposal-render-section">
        <h3>{titulo ?? "Escopo Inicial"}</h3>
        <div className="proposal-render-grid">
          {cards.map((card, idx) => {
            const item = (card ?? {}) as Record<string, unknown>;
            return (
              <article className="proposal-render-card" key={`scope-${idx}`}>
                <h4>{String(item.titulo ?? "Card")}</h4>
                <p>{String(item.subtitulo ?? "")}</p>
                {renderList(item.itens)}
              </article>
            );
          })}
        </div>
      </section>
    );
  }
  if (tipo === "valores_planos") {
    const planos = Array.isArray(data.planos) ? data.planos : [];
    return (
      <section className="proposal-render-section">
        <h3>{titulo ?? "Planos"}</h3>
        <div className="proposal-render-grid">
          {planos.map((plano, idx) => {
            const item = (plano ?? {}) as Record<string, unknown>;
            return (
              <article className={`proposal-render-card ${item.destaque ? "is-highlight" : ""}`} key={`plano-${idx}`}>
                <h4>{String(item.nome ?? "Plano")}</h4>
                <p>{String(item.subtitulo ?? "")}</p>
                {renderList(item.beneficios)}
                <strong>
                  {String(item.valor ?? "")}
                  <small>{String(item.complemento_valor ?? "")}</small>
                </strong>
              </article>
            );
          })}
        </div>
      </section>
    );
  }
  if (tipo === "valores_projeto") {
    const itens = ["setup", "prazo", "garantia", "manutencao_mensal", "melhorias_opcionais"]
      .map((key) => (data[key] as Record<string, unknown>) ?? null)
      .filter((item) => item?.visivel);
    return (
      <section className="proposal-render-section">
        <h3>{titulo ?? "Projeto"}</h3>
        <ul className="proposal-render-list">
          {itens.map((item, idx) => (
            <li key={`proj-${idx}`}>
              <strong>{String(item?.label ?? "Item")}:</strong> {String(item?.valor ?? "")} {String(item?.complemento ?? "")}
            </li>
          ))}
        </ul>
      </section>
    );
  }
  return (
    <section className="proposal-render-section">
      <h3>{titulo ?? tipo}</h3>
      {subtitulo ? <p>{subtitulo}</p> : null}
      {typeof data.texto === "string" ? <p>{data.texto}</p> : null}
      {renderList(data.itens)}
    </section>
  );
};

export default ProposalBlockRenderer;

