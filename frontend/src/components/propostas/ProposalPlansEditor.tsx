import React, { useState } from "react";

interface Props {
  planos: Array<Record<string, unknown>>;
  onChange: (next: Array<Record<string, unknown>>) => void;
}

const ProposalPlansEditor: React.FC<Props> = ({ planos, onChange }) => {
  const [editingIndex, setEditingIndex] = useState<number | null>(null);

  const updatePlano = (idx: number, patch: Record<string, unknown>) => {
    onChange(planos.map((p, i) => (i === idx ? { ...p, ...patch } : p)));
  };

  const addPlano = () => {
    onChange([
      ...planos,
      {
        nome: "Novo Plano",
        subtitulo: "",
        destaque: false,
        tema: "padrao",
        beneficios: ["Novo benefício"],
        valor: "",
        complemento_valor: "/mes",
        observacao: "",
      },
    ]);
    setEditingIndex(planos.length);
  };

  const duplicatePlano = (idx: number) => {
    const base = planos[idx];
    if (!base) return;
    const copy = {
      ...base,
      nome: `${String(base.nome ?? "Plano")} (cópia)`,
    };
    const next = [...planos];
    next.splice(idx + 1, 0, copy);
    onChange(next);
    setEditingIndex(idx + 1);
  };

  const removePlano = (idx: number) => {
    onChange(planos.filter((_, i) => i !== idx));
    if (editingIndex === idx) setEditingIndex(null);
    else if (editingIndex !== null && editingIndex > idx) setEditingIndex(editingIndex - 1);
  };

  const beneficiosRaw = (plano: Record<string, unknown>): string[] => {
    const b = Array.isArray(plano.beneficios) ? plano.beneficios : [];
    return b.filter((i): i is string => typeof i === "string");
  };

  const beneficiosList = (plano: Record<string, unknown>) => {
    return beneficiosRaw(plano)
      .map((s) => s.trim())
      .filter(Boolean);
  };

  const formatValor = (valor: unknown, complemento: unknown): string => {
    const v = String(valor ?? "").trim();
    if (!v) return "—";
    const num = v.replace(/\D/g, "");
    const formatted = num
      ? "R$ " + Number(num).toLocaleString("pt-BR", { minimumFractionDigits: 0, maximumFractionDigits: 2 })
      : v.startsWith("R$") ? v : "R$ " + v;
    const comp = String(complemento ?? "").trim().replace(/^\/?\s*/, "").toLowerCase();
    const compLabel = comp === "mes" || comp === "mês" ? " / mês" : comp === "ano" ? " / ano" : comp ? " / " + comp : "";
    return formatted + compLabel;
  };

  return (
    <div className="proposal-editor-block">
      <h4>Planos</h4>
      <p className="proposal-editor-section-hint" style={{ marginTop: "-0.25rem", marginBottom: "1rem" }}>
        Defina os planos e valores que o cliente verá na proposta.
      </p>
      {planos.length === 0 ? (
        <div className="plans-empty-state">
          <p>Nenhum plano cadastrado ainda.</p>
          <button type="button" className="plans-add-btn" onClick={addPlano}>
            Adicionar primeiro plano
          </button>
        </div>
      ) : (
      <div className="plans-cards-grid">
        {planos.map((plano, idx) => (
          <div
            key={`plano-edit-${idx}`}
            className={`plan-card ${plano.destaque ? "is-destaque" : ""}`}
          >
            {editingIndex === idx ? (
              <>
                <div className="plan-card-form">
                  <label>
                    Nome do plano
                    <input
                      value={String(plano.nome ?? "")}
                      onChange={(e) => updatePlano(idx, { nome: e.target.value })}
                    />
                  </label>
                  <label>
                    Subtítulo
                    <input
                      value={String(plano.subtitulo ?? "")}
                      onChange={(e) => updatePlano(idx, { subtitulo: e.target.value })}
                    />
                  </label>
                  <label>
                    Valor
                    <input
                      value={String(plano.valor ?? "")}
                      onChange={(e) => updatePlano(idx, { valor: e.target.value })}
                    />
                  </label>
                  <label>
                    Benefícios (um por linha)
                    <textarea
                      rows={4}
                      placeholder="Digite um benefício por linha. Use Enter para nova linha."
                      value={beneficiosRaw(plano).join("\n")}
                      onChange={(e) =>
                        updatePlano(idx, {
                          beneficios: e.target.value.split("\n"),
                        })
                      }
                    />
                  </label>
                  <label className="checkbox-inline">
                    <input
                      type="checkbox"
                      checked={Boolean(plano.destaque)}
                      onChange={(e) => updatePlano(idx, { destaque: e.target.checked })}
                    />
                    Destaque
                  </label>
                  <div className="plan-card-actions">
                    <button type="button" onClick={() => setEditingIndex(null)}>
                      Concluir
                    </button>
                    <button type="button" className="danger" onClick={() => removePlano(idx)}>
                      Remover
                    </button>
                  </div>
                </div>
              </>
            ) : (
              <>
                {plano.destaque ? <span className="plan-card-recommended-badge">Plano recomendado</span> : null}
                <h3 className="plan-card-title">{String(plano.nome || "Plano")}</h3>
                {plano.subtitulo ? (
                  <p className="plan-card-subtitle">{String(plano.subtitulo)}</p>
                ) : null}
                <div className="plan-card-value">
                  {formatValor(plano.valor, plano.complemento_valor)}
                </div>
                {beneficiosList(plano).length > 0 ? (
                  <ul className="plan-card-benefits">
                    {beneficiosList(plano).map((item, i) => (
                      <li key={i}>✔ {item}</li>
                    ))}
                  </ul>
                ) : null}
                <div className="plan-card-actions">
                  <button type="button" onClick={() => setEditingIndex(idx)}>
                    Editar
                  </button>
                  <button type="button" onClick={() => duplicatePlano(idx)}>
                    Duplicar
                  </button>
                  <button type="button" className="danger" onClick={() => removePlano(idx)}>
                    Remover
                  </button>
                </div>
              </>
            )}
          </div>
        ))}
      </div>
      )}
      {planos.length > 0 && (
        <button type="button" className="plans-add-btn" onClick={addPlano}>
          + Adicionar plano
        </button>
      )}
    </div>
  );
};

export default ProposalPlansEditor;
