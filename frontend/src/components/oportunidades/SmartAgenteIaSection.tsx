import React, { useCallback, useState } from "react";
import { useAuth } from "../../contexts/AuthContext";
import { OportunidadeIconButton, IcoSparkles, IcoSpinner, IcoX } from "./OportunidadeIconButton";

export type SmartChatRole = "user" | "assistant";

export interface SmartChatMessage {
  role: SmartChatRole;
  content: string;
}

interface Props {
  opoId: number;
  chatDisabled?: boolean;
}

const SmartAgenteIaSection: React.FC<Props> = ({ opoId, chatDisabled = false }) => {
  const { api } = useAuth();
  const [messages, setMessages] = useState<SmartChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const clearChat = useCallback(() => {
    setMessages([]);
    setDraft("");
    setError(null);
  }, []);

  const send = async () => {
    const text = draft.trim();
    if (!text || chatDisabled || loading) return;
    setError(null);
    const nextThread: SmartChatMessage[] = [...messages, { role: "user", content: text }];
    setMessages(nextThread);
    setDraft("");
    setLoading(true);
    try {
      const res = await api.post<{ message: string }>(`/oportunidades/${opoId}/smart-agente/chat`, {
        messages: nextThread,
      });
      const reply = (res.data.message || "").trim();
      setMessages((prev) => [...prev, { role: "assistant", content: reply || "(Sem resposta.)" }]);
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(detail || "Falha ao consultar o Smart Agente.");
      setMessages((prev) => prev.slice(0, -1));
      setDraft(text);
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="surface-card smart-agente-ia-block" aria-labelledby="smart-agente-ia-heading">
      <div className="smart-agente-ia-block__header">
        <div className="smart-agente-ia-block__title-row">
          <span className="smart-agente-ia-block__badge" aria-hidden>
            <IcoSparkles />
          </span>
          <div>
            <h2 className="smart-agente-ia-block__title" id="smart-agente-ia-heading">
              Smart Agente AI
            </h2>
            <p className="smart-agente-ia-block__subtitle">
              Assistente com contexto desta oportunidade (CRM, reuniões e propostas). A conversa não é salva no servidor.
            </p>
          </div>
        </div>
        <OportunidadeIconButton
          type="button"
          variant="subtle"
          label="Limpar conversa"
          icon={<IcoX />}
          onClick={clearChat}
          disabled={loading || messages.length === 0}
        />
      </div>

      {chatDisabled ? (
        <p className="smart-agente-ia-block__closed-hint muted-text">
          Oportunidade fechada (ganho, perdido ou stand-by). O chat está desativado.
        </p>
      ) : null}

      <div className="smart-agente-ia-block__thread" role="log" aria-live="polite" aria-relevant="additions">
        {messages.length === 0 ? (
          <p className="muted-text smart-agente-ia-block__empty">
            Envie uma pergunta ou peça sugestões para avançar o lead (objeções, próximos passos, mensagem para o cliente).
          </p>
        ) : (
          <ul className="smart-agente-ia-block__messages">
            {messages.map((m, idx) => (
              <li
                key={`${idx}-${m.role}`}
                className={`smart-agente-ia-msg smart-agente-ia-msg--${m.role}`}
              >
                <span className="smart-agente-ia-msg__role">{m.role === "user" ? "Você" : "Agente"}</span>
                <div className="smart-agente-ia-msg__bubble">{m.content}</div>
              </li>
            ))}
          </ul>
        )}
      </div>

      {error ? <p className="form-error smart-agente-ia-block__error">{error}</p> : null}

      <div className="smart-agente-ia-block__composer">
        <textarea
          className="smart-agente-ia-block__input"
          rows={3}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Ex.: Como responder se o cliente achar o escopo grande demais?"
          disabled={chatDisabled || loading}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              void send();
            }
          }}
        />
        <div className="smart-agente-ia-block__composer-actions">
          <OportunidadeIconButton
            type="button"
            variant="outline-brand"
            label="Enviar"
            icon={loading ? <IcoSpinner /> : <IcoSparkles />}
            onClick={() => void send()}
            disabled={chatDisabled || loading || !draft.trim()}
          />
        </div>
      </div>
    </section>
  );
};

export default SmartAgenteIaSection;
