import React from "react";

interface Props {
  value: Record<string, unknown>;
  onChange: (next: Record<string, unknown>) => void;
}

const keys = [
  { id: "setup", label: "Setup" },
  { id: "prazo", label: "Prazo" },
  { id: "garantia", label: "Garantia" },
  { id: "manutencao_mensal", label: "Manutenção mensal" },
  { id: "melhorias_opcionais", label: "Melhorias opcionais" },
];

const ProposalProjectValueEditor: React.FC<Props> = ({ value, onChange }) => {
  const updateItem = (itemKey: string, patch: Record<string, unknown>) => {
    const current = ((value[itemKey] as Record<string, unknown>) ?? {}) as Record<string, unknown>;
    onChange({ ...value, [itemKey]: { ...current, ...patch } });
  };

  return (
    <div className="proposal-editor-block">
      <h4>Valores de Projeto</h4>
      <div className="proposal-editor-stack">
        {keys.map((key) => {
          const row = ((value[key.id] as Record<string, unknown>) ?? {}) as Record<string, unknown>;
          return (
            <div key={key.id} className="proposal-editor-card">
              <div className="proposal-editor-row">
                <strong>{key.label}</strong>
                <label className="checkbox-inline">
                  <input
                    type="checkbox"
                    checked={Boolean(row.visivel)}
                    onChange={(e) => updateItem(key.id, { visivel: e.target.checked })}
                  />
                  Exibir
                </label>
              </div>
              <label>
                Label
                <input value={String(row.label ?? key.label)} onChange={(e) => updateItem(key.id, { label: e.target.value })} />
              </label>
              <label>
                Valor
                <input value={String(row.valor ?? "")} onChange={(e) => updateItem(key.id, { valor: e.target.value })} />
              </label>
              <label>
                Complemento
                <input
                  value={String(row.complemento ?? "")}
                  onChange={(e) => updateItem(key.id, { complemento: e.target.value })}
                />
              </label>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default ProposalProjectValueEditor;

