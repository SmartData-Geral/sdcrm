import React, { useCallback, useEffect, useState } from "react";
import { useAuth } from "../../contexts/AuthContext";
import { OportunidadeIconButton, IcoSparkles, IcoSpinner, IcoX } from "./OportunidadeIconButton";

export interface SmartAgenteMsg {
  osmId: number;
  osmRole: "user" | "assistant";
  osmContent: string;
  osmDataCriacao: string;
}

interface ChatResponse {
  user: SmartAgenteMsg;
  assistant: SmartAgenteMsg;
}

interface Props {
  opoId: number;
  chatDisabled?: boolean;
}

const SmartAgenteIaSection: React.FC<Props> = ({ opoId, chatDisabled = false }) => {
  const { api } = useAuth();
  const [messages, setMessages] = useState<SmartAgenteMsg[]>([]);
  const [loadingList, setLoadingList] = useState(true);
  const [draft, setDraft] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadMessages = useCallback(async () => {
    setLoadingList(true);
    setError(null);
    try {
      const res = await api.get<{ items: SmartAgenteMsg[]; total: number }>(
        `/oportunidades/${opoId}/smart-agente/messages`,
        { params: { page_size: 500 } },
      );
      setMessages(res.data.items ?? []);
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(detail || "Não foi possível carregar o histórico do chat.");
      setMessages([]);
    } finally {
      setLoadingList(false);
    }
  }, [api, opoId]);

  useEffect(() => {
    void loadMessages();
  }, [loadMessages]);

  const clearChat = async () => {
    if (chatDisabled || loading) return;
    setError(null);
    try {
      await api.delete(`/oportunidades/${opoId}/smart-agente/messages`);
      setMessages([]);
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(detail || "Falha ao limpar o histórico.");
    }
  };

  const send = async () => {
    const text = draft.trim();
    if (!text || chatDisabled || loading) return;
    setError(null);
    setDraft("");
    setLoading(true);
    try {
      const res = await api.post<ChatResponse>(`/oportunidades/${opoId}/smart-agente/chat`, {
        message: text,
      });
      setMessages((prev) => [...prev, res.data.user, res.data.assistant]);
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(detail || "Falha ao consultar o Smart Agent.");
      setDraft(text);
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="surface-card smart-agente-ia-block" aria-labelledby="smart-agent-heading">
      <div className="smart-agente-ia-block__header">
        <div className="smart-agente-ia-block__title-row">
          <span className="smart-agente-ia-block__badge" aria-hidden>
            <IcoSparkles />
          </span>
          <div>
            <h2 className="smart-agente-ia-block__title" id="smart-agent-heading">
              Smart Agent
            </h2>
            <p className="smart-agente-ia-block__subtitle">
              Chat desta oportunidade com histórico salvo no CRM. Somente usuários com acesso à oportunidade veem esta conversa.
            </p>
          </div>
        </div>
        <OportunidadeIconButton
          type="button"
          variant="subtle"
          label="Limpar histórico do chat"
          icon={<IcoX />}
          onClick={() => void clearChat()}
          disabled={chatDisabled || loading || loadingList || messages.length === 0}
        />
      </div>

      {chatDisabled ? (
        <p className="smart-agente-ia-block__closed-hint muted-text">
          Oportunidade fechada (ganho, perdido ou stand-by). Você pode ver o histórico, mas não enviar novas mensagens ao Smart Agent.
        </p>
      ) : null}

      <div className="smart-agente-ia-block__thread" role="log" aria-live="polite" aria-relevant="additions">
        {loadingList ? (
          <p className="muted-text smart-agente-ia-block__empty">Carregando histórico…</p>
        ) : messages.length === 0 ? (
          <p className="muted-text smart-agente-ia-block__empty">
            Nenhuma mensagem ainda. Envie uma pergunta ou peça sugestões para avançar o lead (objeções, próximos passos,
            mensagem para o cliente).
          </p>
        ) : (
          <ul className="smart-agente-ia-block__messages">
            {messages.map((m) => (
              <li key={m.osmId} className={`smart-agente-ia-msg smart-agente-ia-msg--${m.osmRole}`}>
                <span className="smart-agente-ia-msg__role">{m.osmRole === "user" ? "Você" : "Smart Agent"}</span>
                <div className="smart-agente-ia-msg__bubble">{m.osmContent}</div>
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
          disabled={chatDisabled || loading || loadingList}
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
            disabled={chatDisabled || loading || loadingList || !draft.trim()}
          />
        </div>
      </div>
    </section>
  );
};

export default SmartAgenteIaSection;
