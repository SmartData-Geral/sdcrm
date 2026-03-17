import React, { useState } from "react";

interface Props {
  value: Record<string, unknown>;
  onChange: (next: Record<string, unknown>) => void;
}

interface DifferentialItem {
  titulo: string;
  descricao: string;
  icone?: string;
  ordem?: number;
}

const iconOptions: { value: string; label: string }[] = [
  { value: "experiencia", label: "Experiência" },
  { value: "personalizacao", label: "Personalização" },
  { value: "integracoes", label: "Integrações" },
  { value: "ia_automacao", label: "IA e automação" },
];

const normalizeItems = (raw: unknown[]): DifferentialItem[] => {
  return raw.map((item, idx) => {
    if (typeof item === "string") {
      return { titulo: item, descricao: "", icone: undefined, ordem: idx + 1 };
    }
    const rec = (item ?? {}) as Record<string, unknown>;
    return {
      titulo: String(rec.titulo ?? ""),
      descricao: String(rec.descricao ?? ""),
      icone: rec.icone ? String(rec.icone) : undefined,
      ordem: typeof rec.ordem === "number" ? rec.ordem : idx + 1,
    };
  });
};

const ProposalDifferentialsEditor: React.FC<Props> = ({ value, onChange }) => {
  const itensRaw = Array.isArray(value.itens) ? value.itens : [];
  const itens = normalizeItems(itensRaw);
  const [editingIndex, setEditingIndex] = useState<number | null>(null);

  const updateRoot = (patch: Record<string, unknown>) => {
    onChange({
      ...value,
      ...patch,
    });
  };

  const updateItem = (idx: number, patch: Partial<DifferentialItem>) => {
    const next = itens.map((item, i) => (i === idx ? { ...item, ...patch } : item));
    updateRoot({ itens: next });
  };

  const addItem = () => {
    const next: DifferentialItem = {
      titulo: "Novo diferencial",
      descricao: "",
      icone: "experiencia",
      ordem: itens.length + 1,
    };
    updateRoot({ itens: [...itens, next] });
    setEditingIndex(itens.length);
  };

  const removeItem = (idx: number) => {
    const next = itens.filter((_, i) => i !== idx);
    updateRoot({ itens: next });
    if (editingIndex === idx) setEditingIndex(null);
    else if (editingIndex !== null && editingIndex > idx) setEditingIndex(editingIndex - 1);
  };

  return (
    <div className="proposal-editor-block">
      <h4>Diferenciais</h4>
      <p className="proposal-editor-section-hint" style={{ marginTop: "-0.25rem", marginBottom: "0.75rem" }}>
        Título, subtítulo e cards de diferenciais competitivos exibidos na proposta pública.
      </p>
      <div className="proposal-editor-stack">
        <label>
          Título da seção
          <input
            value={String(value.titulo ?? "")}
            onChange={(e) => updateRoot({ titulo: e.target.value })}
            placeholder="Por que escolher a Smart Data"
          />
        </label>
        <label>
          Subtítulo da seção
          <input
            value={String(value.subtitulo ?? "")}
            onChange={(e) => updateRoot({ subtitulo: e.target.value })}
            placeholder="Soluções pensadas para gerar eficiência, integração e resultado real para a sua operação."
          />
        </label>
      </div>

      {itens.length === 0 ? (
        <div className="scope-empty-state" style={{ marginTop: "1rem" }}>
          <p>Nenhum diferencial cadastrado ainda.</p>
          <button type="button" className="scope-add-card-btn" onClick={addItem}>
            Adicionar primeiro diferencial
          </button>
        </div>
      ) : (
        <div className="differentials-cards-grid">
          {itens.map((item, idx) => (
            <div key={`diff-card-${idx}`} className="differential-card">
              {editingIndex === idx ? (
                <>
                  <div className="differential-card-header">
                    <h3 className="differential-card-title">Editar diferencial</h3>
                    <div className="differential-card-header-actions">
                      <button type="button" onClick={() => setEditingIndex(null)}>
                        Concluir
                      </button>
                      <button type="button" className="danger" onClick={() => removeItem(idx)}>
                        Remover
                      </button>
                    </div>
                  </div>
                  <div className="differential-card-form">
                    <label>
                      Título
                      <input
                        value={item.titulo}
                        onChange={(e) => updateItem(idx, { titulo: e.target.value })}
                      />
                    </label>
                    <label>
                      Descrição
                      <textarea
                        rows={3}
                        value={item.descricao}
                        onChange={(e) => updateItem(idx, { descricao: e.target.value })}
                      />
                    </label>
                    <label>
                      Ícone
                      <select
                        value={item.icone ?? ""}
                        onChange={(e) => updateItem(idx, { icone: e.target.value || undefined })}
                      >
                        <option value="">Padrão</option>
                        {iconOptions.map((opt) => (
                          <option key={opt.value} value={opt.value}>
                            {opt.label}
                          </option>
                        ))}
                      </select>
                      <span className="field-hint">
                        Escolha um tipo de ícone para este diferencial. Se vazio, um ícone padrão será usado.
                      </span>
                    </label>
                  </div>
                </>
              ) : (
                <>
                  <div className="differential-card-header">
                    <div className="differential-card-title-block">
                      <h3 className="differential-card-title">{item.titulo || "Diferencial sem título"}</h3>
                      {item.descricao ? (
                        <p className="differential-card-subtitle">{item.descricao}</p>
                      ) : null}
                    </div>
                    <div className="differential-card-header-actions">
                      <button type="button" onClick={() => setEditingIndex(idx)}>
                        Editar
                      </button>
                      <button type="button" className="danger" onClick={() => removeItem(idx)}>
                        Remover
                      </button>
                    </div>
                  </div>
                </>
              )}
            </div>
          ))}
        </div>
      )}

      {itens.length > 0 && (
        <button type="button" className="scope-add-card-btn" onClick={addItem}>
          + Adicionar diferencial
        </button>
      )}
    </div>
  );
};

export default ProposalDifferentialsEditor;

