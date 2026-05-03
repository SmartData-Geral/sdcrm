import React, { useCallback, useState } from "react";
import Modal from "../Modal";
import { LLM_MAX_FILES_PER_REQUEST } from "../../constants/llmUploads";
import { useAuth } from "../../contexts/AuthContext";

interface Props {
  value: Record<string, unknown>;
  onChange: (next: Record<string, unknown>) => void;
  propostaId: number;
}

type SugestaoBloco = { titulo: string; subtitulo: string; itens: string[] };

type PreviewBloco = SugestaoBloco & {
  key: string;
  ignored: boolean;
  applied: boolean;
};

function newPreviewKey(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `b-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

const ProposalScopeEditor: React.FC<Props> = ({ value, onChange, propostaId }) => {
  const { api } = useAuth();
  const cards = (Array.isArray(value.cards) ? value.cards : []) as Array<Record<string, unknown>>;
  const [editingIndex, setEditingIndex] = useState<number | null>(null);

  const [showInputModal, setShowInputModal] = useState(false);
  const [showPreviewModal, setShowPreviewModal] = useState(false);
  const [pontosPrincipais, setPontosPrincipais] = useState("");
  const [observacoesAdicionais, setObservacoesAdicionais] = useState("");
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [generating, setGenerating] = useState(false);
  const [sugestaoError, setSugestaoError] = useState<string | null>(null);
  const [observacoesIa, setObservacoesIa] = useState("");
  const [previewBlocos, setPreviewBlocos] = useState<PreviewBloco[]>([]);
  const [editingPreviewKey, setEditingPreviewKey] = useState<string | null>(null);
  const [editDraft, setEditDraft] = useState<SugestaoBloco>({ titulo: "", subtitulo: "", itens: [] });

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

  const resetInputModal = useCallback(() => {
    setPontosPrincipais("");
    setObservacoesAdicionais("");
    setSelectedFiles([]);
    setSugestaoError(null);
  }, []);

  const openInputModal = () => {
    resetInputModal();
    setShowInputModal(true);
  };

  const closeInputModal = () => {
    if (generating) return;
    setShowInputModal(false);
    resetInputModal();
  };

  const handleGerarSugestao = async () => {
    setSugestaoError(null);
    if (selectedFiles.length > LLM_MAX_FILES_PER_REQUEST) {
      setSugestaoError(
        `Envie no máximo ${LLM_MAX_FILES_PER_REQUEST} arquivos por requisição (complementares à sugestão de escopo).`,
      );
      return;
    }
    setGenerating(true);
    try {
      const data = new FormData();
      data.append("pontos_principais", pontosPrincipais);
      data.append("observacoes_adicionais", observacoesAdicionais);
      selectedFiles.forEach((file) => data.append("files", file));

      const res = await api.post<{
        blocos?: Array<{ titulo?: string; subtitulo?: string; itens?: string[] }>;
        observacoes?: string;
      }>(`/propostas/${propostaId}/escopo/sugerir-ia`, data);

      const raw = res.data?.blocos ?? [];
      const mapped: PreviewBloco[] = raw.map((b) => ({
        key: newPreviewKey(),
        titulo: String(b.titulo ?? "").trim() || "Bloco sugerido",
        subtitulo: String(b.subtitulo ?? "").trim(),
        itens: Array.isArray(b.itens) ? b.itens.map((x) => String(x).trim()).filter(Boolean) : [],
        ignored: false,
        applied: false,
      }));

      setObservacoesIa(String(res.data?.observacoes ?? "").trim());
      setPreviewBlocos(mapped);
      setShowInputModal(false);
      setShowPreviewModal(true);
      resetInputModal();
    } catch (err: unknown) {
      console.error(err);
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setSugestaoError(
        typeof detail === "string"
          ? detail
          : "Não foi possível gerar a sugestão de escopo. Verifique os dados e tente novamente.",
      );
    } finally {
      setGenerating(false);
    }
  };

  const aplicarBloco = (key: string) => {
    const row = previewBlocos.find((b) => b.key === key);
    if (!row || row.applied || row.ignored) return;
    const nextCards = [
      ...cards,
      { titulo: row.titulo, subtitulo: row.subtitulo, itens: row.itens.length ? row.itens : ["Item a detalhar"] },
    ];
    onChange({ ...value, cards: nextCards });
    setPreviewBlocos((prev) => prev.map((b) => (b.key === key ? { ...b, applied: true } : b)));
  };

  const ignorarBloco = (key: string) => {
    setPreviewBlocos((prev) => prev.map((b) => (b.key === key ? { ...b, ignored: true } : b)));
  };

  const iniciarEdicaoPreview = (key: string) => {
    const row = previewBlocos.find((b) => b.key === key);
    if (!row || row.applied || row.ignored) return;
    setEditingPreviewKey(key);
    setEditDraft({
      titulo: row.titulo,
      subtitulo: row.subtitulo,
      itens: [...row.itens],
    });
  };

  const salvarEdicaoPreview = () => {
    if (!editingPreviewKey) return;
    const itens = editDraft.itens.map((s) => s.trim()).filter(Boolean);
    setPreviewBlocos((prev) =>
      prev.map((b) =>
        b.key === editingPreviewKey
          ? {
              ...b,
              titulo: editDraft.titulo.trim() || b.titulo,
              subtitulo: editDraft.subtitulo.trim(),
              itens: itens.length ? itens : b.itens,
            }
          : b,
      ),
    );
    setEditingPreviewKey(null);
  };

  const cancelarEdicaoPreview = () => {
    setEditingPreviewKey(null);
  };

  const fecharPreview = () => {
    setShowPreviewModal(false);
    setPreviewBlocos([]);
    setObservacoesIa("");
    setEditingPreviewKey(null);
  };

  return (
    <div className="proposal-editor-block">
      <div className="proposal-editor-row">
        <h4>Escopo inicial</h4>
      </div>
      <div className="scope-ai-panel">
        <div className="scope-ai-panel-header">
          <strong>Geração de escopo com IA</strong>
          <span className="field-hint">
            Use reuniões da oportunidade, textos e arquivos opcionais. A prévia não substitui o escopo — você aplica bloco a bloco.
          </span>
        </div>
        <div className="scope-ai-panel-actions">
          <button type="button" className="btn-outline-brand" onClick={openInputModal}>
            Gerar escopo com IA
          </button>
        </div>
      </div>

      <Modal isOpen={showInputModal} title="Gerar escopo com IA" onClose={closeInputModal}>
        <div className="scope-ai-modal-form">
          <label>
            Pontos principais para considerar
            <textarea
              rows={4}
              value={pontosPrincipais}
              onChange={(e) => setPontosPrincipais(e.target.value)}
              placeholder="Ex.: necessidade de BI operacional, integração com ERP X, prazo desejado..."
              disabled={generating}
            />
          </label>
          <label>
            Observações adicionais
            <textarea
              rows={3}
              value={observacoesAdicionais}
              onChange={(e) => setObservacoesAdicionais(e.target.value)}
              placeholder="Restrições, stakeholders, premissas..."
              disabled={generating}
            />
          </label>
          <label>
            Arquivos opcionais — pode anexar vários (txt, md, csv, json, pdf, jpg, png). Máximo {LLM_MAX_FILES_PER_REQUEST} por
            envio.
            <input
              type="file"
              multiple
              accept=".txt,.md,.csv,.json,.pdf,image/png,image/jpeg,.jpg,.jpeg,text/markdown"
              onChange={(e) => setSelectedFiles(Array.from(e.target.files ?? []))}
              disabled={generating}
            />
          </label>
          {selectedFiles.length > 0 ? (
            <span className="field-hint">{selectedFiles.length} arquivo(s) selecionado(s).</span>
          ) : null}
          {sugestaoError ? <p className="scope-ai-error">{sugestaoError}</p> : null}
          <div className="scope-ai-modal-footer">
            <button type="button" className="btn-secondary" onClick={closeInputModal} disabled={generating}>
              Cancelar
            </button>
            <button type="button" className="btn-outline-brand" onClick={() => void handleGerarSugestao()} disabled={generating}>
              {generating ? "Gerando sugestão..." : "Gerar sugestão"}
            </button>
          </div>
        </div>
      </Modal>

      <Modal isOpen={showPreviewModal} title="Prévia — sugestão de escopo" onClose={fecharPreview}>
        <div className="scope-ai-preview-body">
          {observacoesIa ? (
            <div className="scope-ai-preview-obs">
              <strong>Observações da IA</strong>
              <p>{observacoesIa}</p>
            </div>
          ) : null}
          {previewBlocos.length === 0 ? (
            <p className="field-hint">Nenhum bloco retornado.</p>
          ) : (
            <div className="scope-ai-preview-list">
              {previewBlocos.map((b) => (
                <div
                  key={b.key}
                  className={`scope-ai-preview-card ${b.ignored ? "is-ignored" : ""} ${b.applied ? "is-applied" : ""}`}
                >
                  {editingPreviewKey === b.key ? (
                    <div className="scope-ai-preview-edit">
                      <label>
                        Título
                        <input
                          value={editDraft.titulo}
                          onChange={(e) => setEditDraft((d) => ({ ...d, titulo: e.target.value }))}
                        />
                      </label>
                      <label>
                        Subtítulo
                        <input
                          value={editDraft.subtitulo}
                          onChange={(e) => setEditDraft((d) => ({ ...d, subtitulo: e.target.value }))}
                        />
                      </label>
                      <label>
                        Itens (um por linha)
                        <textarea
                          rows={5}
                          value={editDraft.itens.join("\n")}
                          onChange={(e) =>
                            setEditDraft((d) => ({
                              ...d,
                              itens: e.target.value.split("\n"),
                            }))
                          }
                        />
                      </label>
                      <div className="scope-ai-preview-block-actions">
                        <button type="button" className="btn-secondary" onClick={cancelarEdicaoPreview}>
                          Cancelar edição
                        </button>
                        <button type="button" className="btn-outline-brand" onClick={salvarEdicaoPreview}>
                          Salvar bloco
                        </button>
                      </div>
                    </div>
                  ) : (
                    <>
                      <h5 className="scope-ai-preview-card-title">{b.titulo}</h5>
                      {b.subtitulo ? <p className="scope-ai-preview-card-sub">{b.subtitulo}</p> : null}
                      <ul className="scope-ai-preview-card-items">
                        {b.itens.map((item, i) => (
                          <li key={i}>{item}</li>
                        ))}
                      </ul>
                      {b.applied ? (
                        <p className="scope-ai-preview-status">Aplicado ao escopo.</p>
                      ) : b.ignored ? (
                        <p className="scope-ai-preview-status scope-ai-preview-status--muted">Ignorado.</p>
                      ) : (
                        <div className="scope-ai-preview-block-actions">
                          <button type="button" className="btn-outline-brand" onClick={() => aplicarBloco(b.key)}>
                            Aplicar bloco
                          </button>
                          <button type="button" className="btn-secondary" onClick={() => iniciarEdicaoPreview(b.key)}>
                            Editar
                          </button>
                          <button type="button" className="btn-secondary danger" onClick={() => ignorarBloco(b.key)}>
                            Ignorar
                          </button>
                        </div>
                      )}
                    </>
                  )}
                </div>
              ))}
            </div>
          )}
          <div className="scope-ai-modal-footer">
            <button type="button" className="btn-outline-brand" onClick={fecharPreview}>
              Fechar
            </button>
          </div>
        </div>
      </Modal>

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
                    <span className="scope-card-drag" title="Mover (em breve)" aria-hidden>
                      ⋮⋮
                    </span>
                    <h3 className="scope-card-title">Editar bloco</h3>
                    <div className="scope-card-header-actions">
                      <button type="button" onClick={() => setEditingIndex(null)}>
                        Concluir
                      </button>
                      <button type="button" className="danger" onClick={() => removeCard(idx)}>
                        Remover
                      </button>
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
                    <span className="scope-card-drag" title="Mover (em breve)" aria-hidden>
                      ⋮⋮
                    </span>
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
                  {card.subtitulo ? <p className="scope-card-subtitle">{String(card.subtitulo)}</p> : null}
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
