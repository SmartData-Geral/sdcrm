import React, { useEffect, useMemo, useRef, useState } from "react";

type TemperaturaValue = "frio" | "morno" | "quente" | null;

interface TemperatureSelectProps {
  value: string | null;
  placeholder?: string;
  onChange: (next: TemperaturaValue) => void;
}

function getTempLabel(value: TemperaturaValue): string {
  if (value === "frio") return "Frio";
  if (value === "morno") return "Morno";
  if (value === "quente") return "Quente";
  return "Selecione";
}

function sanitizeValue(value: string | null): TemperaturaValue {
  if (!value) return null;
  const normalized = value.toLowerCase().trim();
  if (normalized === "frio" || normalized === "morno" || normalized === "quente") {
    return normalized;
  }
  return null;
}

const TemperatureSelect: React.FC<TemperatureSelectProps> = ({ value, placeholder = "Selecione", onChange }) => {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement | null>(null);
  const selected = useMemo(() => sanitizeValue(value), [value]);

  useEffect(() => {
    const handleOutside = (ev: MouseEvent) => {
      if (!rootRef.current) return;
      if (!rootRef.current.contains(ev.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handleOutside);
    return () => document.removeEventListener("mousedown", handleOutside);
  }, []);

  return (
    <div className="temp-select" ref={rootRef}>
      <button type="button" className="temp-select-trigger" onClick={() => setOpen((prev) => !prev)}>
        {selected ? (
          <>
            <span className={`temp-icon temp-icon--${selected}`} aria-hidden>
              {selected === "quente" ? "🔥" : selected === "morno" ? "◔" : "❄"}
            </span>
            <span>{getTempLabel(selected)}</span>
          </>
        ) : (
          <span>{placeholder}</span>
        )}
        <span className="temp-select-caret">▾</span>
      </button>
      {open && (
        <ul className="temp-select-list" role="listbox">
          <li>
            <button
              type="button"
              className="temp-select-item"
              onClick={() => {
                onChange(null);
                setOpen(false);
              }}
            >
              <span>{placeholder}</span>
            </button>
          </li>
          {(["frio", "morno", "quente"] as const).map((opt) => (
            <li key={opt}>
              <button
                type="button"
                className="temp-select-item"
                onClick={() => {
                  onChange(opt);
                  setOpen(false);
                }}
              >
                <span className={`temp-icon temp-icon--${opt}`} aria-hidden>
                  {opt === "quente" ? "🔥" : opt === "morno" ? "◔" : "❄"}
                </span>
                <span>{getTempLabel(opt)}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default TemperatureSelect;
