import React from "react";

interface OptionalTextareaFieldProps {
  isOpen: boolean;
  onToggle: () => void;
  buttonLabel: string;
  label: string;
  value: string;
  onChange: (next: string) => void;
  placeholder?: string;
}

const OptionalTextareaField: React.FC<OptionalTextareaFieldProps> = ({
  isOpen,
  onToggle,
  buttonLabel,
  label,
  value,
  onChange,
  placeholder,
}) => {
  return (
    <div className="optional-field">
      {!isOpen ? (
        <button type="button" className="optional-field-toggle" onClick={onToggle}>
          {buttonLabel}
        </button>
      ) : (
        <>
          <div className="optional-field-header">
            <span className="optional-field-title">{label}</span>
            <button type="button" className="optional-field-toggle optional-field-toggle--small" onClick={onToggle}>
              Ocultar
            </button>
          </div>
          <textarea value={value} onChange={(e) => onChange(e.target.value)} rows={3} placeholder={placeholder} />
        </>
      )}
    </div>
  );
};

export default OptionalTextareaField;
