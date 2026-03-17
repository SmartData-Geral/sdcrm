import React, { useState } from "react";

interface Props {
  value: Record<string, unknown>;
  onChange: (next: Record<string, unknown>) => void;
}

const ProposalScopeEditor: React.FC<Props> = ({ value, onChange }) => {
  const cards = (Array.isArray(value.cards) ? value.cards : []) as Array<Record<string, unknown>>;
  const [editingIndex, setEditingIndex] = useState<number | null>(null);

  const updateCard = (idx: number, patch: Record<string, unknown>) => {
    onChange({
      ...value,
      cards: cards.map((c, i) => (i === idx ? { ...c, ...patch } : c)),
    });
  };

  const addCard = () => {
    onChange({
      ...value,
      cards: [...cards, { titulo: "Novo bloco", subtitulo: "", itens: ["Novo item"] }],
    });
    setEditingIndex(cards.length);
  };

  const removeCard = (idx: number) => {
    onChange({
      ...value,
      cards: cards.filter((_, i) => i !== idx),
    });
    if (editingIndex === idx) setEditingIndex(null);
    else if (editingIndex !== null && editingIndex > idx) setEditingIndex(editingIndex - 1);
  };

  const itensList = (card: Record<string, unknown>) => {
    const itens = Array.isArray(card.itens) ? card.itens : [];
    return itens
      .filter((i): i is string => typeof i === "string")
      .map((s) => s.trim())
      .filter(Boolean);
  };

  return (
    <div className="proposal-editor-block">
      <div className="proposal-editor-row">
        <h4>Escopo inicial</h4>
      </div>
      <div className="proposal-editor-stack" style={{ marginBottom: "0.75rem" }}>
        <label>
          Título da seção (página pública)
          <input
            value={String(value.titulo ?? "")}
            onChange={(e) => onChange({ ...value, titulo: e.target.value })}
            placeholder="Fases do projeto"
          />
        </label>
        <label>
          Subtítulo da seção (página pública)
          <input
            value={String(value.subtitulo ?? "")}
            onChange={(e) => onChange({ ...value, subtitulo: e.target.value })}
            placeholder="Detalhamento dos itens da proposta"
          />
        </label>
      </div>
      <label className="checkbox-inline" style={{ marginBottom: "0.75rem" }}>
        <input
          type="checkbox"
          checked={Boolean(value.visivel ?? true)}
          onChange={(e) => onChange({ ...value, visivel: e.target.checked })}
        />
        Exibir seção na proposta
      </label>
      {cards.length === 0 ? (
        <div className="scope-empty-state">
          <p>Nenhum bloco de escopo ainda.</p>
          <button type="button" className="scope-add-card-btn" onClick={addCard}>
            Adicionar primeiro bloco de escopo
          </button>
        </div>
      ) : (
      <div className="scope-cards-grid">
        {cards.map((card, idx) => (
          <div key={`scope-card-${idx}`} className="scope-card">
            {editingIndex === idx ? (
              <>
                <div className="scope-card-header">
                  <span className="scope-card-drag" title="Mover (em breve)" aria-hidden>⋮⋮</span>
                  <h3 className="scope-card-title">Editar bloco</h3>
                  <div className="scope-card-header-actions">
                    <button type="button" onClick={() => setEditingIndex(null)}>Concluir</button>
                    <button type="button" className="danger" onClick={() => removeCard(idx)}>Remover</button>
                  </div>
                </div>
                <div className="scope-card-form">
                  <label>
                    Título
                    <input
                      value={String(card.titulo ?? "")}
                      onChange={(e) => updateCard(idx, { titulo: e.target.value })}
                    />
                  </label>
                  <label>
                    Subtítulo
                    <input
                      value={String(card.subtitulo ?? "")}
                      onChange={(e) => updateCard(idx, { subtitulo: e.target.value })}
                    />
                  </label>
                  <label>
                    Itens (um por linha)
                    <textarea
                      rows={5}
                      placeholder="Digite um item por linha. Use Enter para nova linha."
                      value={Array.isArray(card.itens) ? (card.itens as string[]).join("\n") : ""}
                      onChange={(e) =>
                        updateCard(idx, {
                          itens: e.target.value.split("\n"),
                        })
                      }
                    />
                  </label>
                </div>
              </>
            ) : (
              <>
                <div className="scope-card-header">
                  <span className="scope-card-drag" title="Mover (em breve)" aria-hidden>⋮⋮</span>
                  <div className="scope-card-title-block">
                    <h3 className="scope-card-title">{String(card.titulo || "Bloco sem título")}</h3>
                    <span className="scope-card-item-count">{itensList(card).length} itens</span>
                  </div>
                  <div className="scope-card-header-actions">
                    <button type="button" onClick={() => setEditingIndex(idx)}>
                      Editar
                    </button>
                    <button type="button" className="danger" onClick={() => removeCard(idx)}>
                      Remover
                    </button>
                  </div>
                </div>
                {card.subtitulo ? (
                  <p className="scope-card-subtitle">{String(card.subtitulo)}</p>
                ) : null}
                <ul className="scope-card-list">
                  {itensList(card).map((item, i) => (
                    <li key={i}>{item}</li>
                  ))}
                </ul>
              </>
            )}
          </div>
        ))}
      </div>
      )}
      {cards.length > 0 && (
        <button type="button" className="scope-add-card-btn" onClick={addCard}>
          + Adicionar bloco de escopo
        </button>
      )}
    </div>
  );
};

export default ProposalScopeEditor;
