import React, { useEffect, useRef, useState } from "react";
import UserAvatar from "./UserAvatar";

interface AvatarOption {
  id: number;
  nome: string;
  avatarUrl?: string | null;
}

interface AvatarSelectProps {
  options: AvatarOption[];
  value: number | null;
  placeholder?: string;
  onChange: (next: number | null) => void;
}

const AvatarSelect: React.FC<AvatarSelectProps> = ({ options, value, placeholder = "Selecione", onChange }) => {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement | null>(null);
  const selected = options.find((o) => o.id === value) ?? null;

  useEffect(() => {
    const handleOutside = (ev: MouseEvent) => {
      if (!rootRef.current) return;
      if (!rootRef.current.contains(ev.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handleOutside);
    return () => document.removeEventListener("mousedown", handleOutside);
  }, []);

  return (
    <div className="avatar-select" ref={rootRef}>
      <button type="button" className="avatar-select-trigger" onClick={() => setOpen((v) => !v)}>
        {selected ? (
          <>
            <UserAvatar name={selected.nome} avatarUrl={selected.avatarUrl} size="sm" />
            <span>{selected.nome}</span>
          </>
        ) : (
          <span>{placeholder}</span>
        )}
        <span className="avatar-select-caret">▾</span>
      </button>
      {open && (
        <ul className="avatar-select-list" role="listbox">
          <li>
            <button type="button" className="avatar-select-item" onClick={() => { onChange(null); setOpen(false); }}>
              <span>{placeholder}</span>
            </button>
          </li>
          {options.map((opt) => (
            <li key={opt.id}>
              <button
                type="button"
                className="avatar-select-item"
                onClick={() => {
                  onChange(opt.id);
                  setOpen(false);
                }}
              >
                <UserAvatar name={opt.nome} avatarUrl={opt.avatarUrl} size="sm" />
                <span>{opt.nome}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default AvatarSelect;
