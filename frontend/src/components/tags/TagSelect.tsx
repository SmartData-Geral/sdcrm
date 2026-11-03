import React, { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import TagBadge, { TagResumo } from "./TagBadge";

interface TagSelectProps {
  options: TagResumo[];
  value: TagResumo[];
  onChange: (tagIds: number[]) => Promise<void>;
}

const TagSelect: React.FC<TagSelectProps> = ({ options, value, onChange }) => {
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [erro, setErro] = useState(false);
  const rootRef = useRef<HTMLDivElement | null>(null);
  const selectedIds = new Set(value.map((t) => t.tagId));

  useEffect(() => {
    const handleOutside = (ev: MouseEvent) => {
      if (!rootRef.current) return;
      if (!rootRef.current.contains(ev.target as Node)) setOpen(false);
    };
    const handleEscape = (ev: KeyboardEvent) => {
      if (ev.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", handleOutside);
    document.addEventListener("keydown", handleEscape);
    return () => {
      document.removeEventListener("mousedown", handleOutside);
      document.removeEventListener("keydown", handleEscape);
    };
  }, []);

  const toggle = async (tagId: number) => {
    const next = new Set(selectedIds);
    if (next.has(tagId)) next.delete(tagId);
    else next.add(tagId);
    setSaving(true);
    setErro(false);
    try {
      await onChange([...next]);
    } catch {
      setErro(true);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="tag-select" ref={rootRef}>
      {value.map((t) => (
        <TagBadge key={t.tagId} nome={t.tagNome} cor={t.tagCor} />
      ))}
      <button
        type="button"
        className="tag-select-trigger"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        + Tag
      </button>
      {erro && <span className="error-text">Não foi possível salvar as tags.</span>}
      {open && (
        <div className="tag-select-list">
          {options.length === 0 ? (
            <p className="tag-select-empty">
              Nenhuma tag cadastrada. <Link to="/cadastros/tags">Cadastrar tags</Link>
            </p>
          ) : (
            options.map((opt) => (
              <button
                key={opt.tagId}
                type="button"
                className="tag-select-item"
                aria-pressed={selectedIds.has(opt.tagId)}
                disabled={saving}
                onClick={() => void toggle(opt.tagId)}
              >
                <TagBadge nome={opt.tagNome} cor={opt.tagCor} />
                {selectedIds.has(opt.tagId) && <span className="tag-select-check" aria-hidden>✓</span>}
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
};

export default TagSelect;
