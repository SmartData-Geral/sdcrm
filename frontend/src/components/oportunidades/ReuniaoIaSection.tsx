import React, { useEffect, useId, useMemo, useRef, useState } from "react";
import { useAuth } from "../../contexts/AuthContext";
import { LLM_MAX_FILES_PER_REQUEST } from "../../constants/llmUploads";
import { ReuniaoAnaliseItem } from "./reuniaoIaTypes";
import {
  OportunidadeIconButton,
  IcoSparkles,
  IcoLayers,
  IcoMessage,
  IcoList,
  IcoTrending,
  IcoThermo,
  IcoSpinner,
} from "./OportunidadeIconButton";

interface Props {
  opoId: number;
  onOpportunityRefresh: () => Promise<void>;
}

const FILE_ACCEPT =
  ".txt,.csv,.json,.pdf,.md,.log,.tsv,text/plain,text/csv,application/json,application/pdf";

const ReuniaoIaSection: React.FC<Props> = ({ opoId, onOpportunityRefresh }) => {
  const { api } = useAuth();
  const idArquivoTranscricao = useId();
  const idArquivosExtras = useId();
  const idTextoPanelBody = useId();
  const refArquivoTranscricao = useRef<HTMLInputElement>(null);
  const refArquivosExtras = useRef<HTMLInputElement>(null);
  const [transcricao, setTranscricao] = useState("");
  const [textoTranscricaoAberto, setTextoTranscricaoAberto] = useState(false);
  const [arquivosTranscricao, setArquivosTranscricao] = useState<File[]>([]);
  const [files, setFiles] = useState<File[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [applying, setApplying] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [analises, setAnalises] = useState<ReuniaoAnaliseItem[]>([]);
  const [selectedRanId, setSelectedRanId] = useState<number | null>(null);

  const selected = useMemo(
    () => analises.find((item) => item.ranId === selectedRanId) ?? analises[0] ?? null,
    [analises, selectedRanId]
  );

  const loadAnalises = async () => {
    setLoadingHistory(true);
    try {
      const res = await api.get<{ items: ReuniaoAnaliseItem[] }>(`/oportunidades/${opoId}/analises-reuniao`, {
        params: { page_size: 50 },
      });
      setAnalises(res.data.items ?? []);
      if (!selectedRanId && (res.data.items?.length ?? 0) > 0) {
        setSelectedRanId(res.data.items[0].ranId);
      }
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(detail || "Não foi possível carregar histórico de análises.");
    } finally {
      setLoadingHistory(false);
    }
  };

  useEffect(() => {
    void loadAnalises();
  }, [opoId]);

  const clearMessages = () => {
    setError(null);
    setSuccess(null);
  };

  const processarComIa = async () => {
    clearMessages();
    setProcessing(true);
    try {
      let ranId = selected?.ranId ?? null;

      if (transcricao.trim() || arquivosTranscricao.length > 0 || files.length > 0) {
        const totalArquivos = arquivosTranscricao.length + files.length;
        if (totalArquivos > LLM_MAX_FILES_PER_REQUEST) {
          setError(
            `Envie no máximo ${LLM_MAX_FILES_PER_REQUEST} arquivos no total (transcrição em arquivo + materiais complementares).`,
          );
          return;
        }
        const data = new FormData();
        data.append("ranTranscricao", transcricao);
        arquivosTranscricao.forEach((file) => data.append("arquivos_transcricao", file));
        files.forEach((file) => data.append("files", file));
        const created = await api.post<ReuniaoAnaliseItem>(`/oportunidades/${opoId}/analises-reuniao`, data, {
          headers: { "Content-Type": "multipart/form-data" },
        });
        ranId = created.data.ranId;
      }

      if (!ranId) {
        setError(
          "Informe a transcrição (texto e/ou arquivo), anexe materiais complementares ou selecione uma análise existente.",
        );
        return;
      }

      await api.post<ReuniaoAnaliseItem>(`/analises-reuniao/${ranId}/processar`);
      setSuccess("Análise processada com sucesso.");
      setTranscricao("");
      setArquivosTranscricao([]);
      setFiles([]);
      await loadAnalises();
      setSelectedRanId(ranId);
      await onOpportunityRefresh();
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(detail || "Falha ao processar análise com IA.");
    } finally {
      setProcessing(false);
    }
  };

  const aplicarCampo = async (endpoint: string, successMessage: string) => {
    if (!selected) return;
    clearMessages();
    setApplying(true);
    try {
      await api.patch(`/analises-reuniao/${selected.ranId}/${endpoint}`);
      setSuccess(successMessage);
      await onOpportunityRefresh();
      await loadAnalises();
      window.location.reload();
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(detail || "Não foi possível aplicar o campo na oportunidade.");
    } finally {
      setApplying(false);
    }
  };

  const aplicarTodas = async () => {
    if (!selected) return;
    clearMessages();
    setApplying(true);
    const steps: [string, string][] = [
      ["aplicar-observacoes", "Observações"],
      ["aplicar-dores-oportunidades", "Dores/oportunidades"],
      ["aplicar-lead-score", "Lead score"],
      ["aplicar-temperatura", "Temperatura"],
    ];
    const failed: string[] = [];
    try {
      for (const [endpoint, label] of steps) {
        try {
          await api.patch(`/analises-reuniao/${selected.ranId}/${endpoint}`);
        } catch (err: unknown) {
          const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
          failed.push(`${label}: ${typeof detail === "string" ? detail : "falha"}`);
        }
      }
      await onOpportunityRefresh();
      await loadAnalises();
      if (failed.length > 0) {
        setError(`Algumas ações não puderam ser aplicadas: ${failed.join(" | ")}`);
      } else {
        setSuccess("Todas as ações foram aplicadas na oportunidade.");
        window.location.reload();
      }
    } finally {
      setApplying(false);
    }
  };

  const limparArquivosTranscricao = () => {
    setArquivosTranscricao([]);
    if (refArquivoTranscricao.current) refArquivoTranscricao.current.value = "";
  };

  return (
    <section className="surface-card details-card">
      <h2 className="section-title section-title--panel">Reunião / IA</h2>

      <div className="reuniao-ia-block">
        <h3>Materiais da reunião</h3>
        <p className="field-hint" style={{ marginTop: 0 }}>
          <strong>Transcrição:</strong> use o campo de texto, o arquivo da transcrição ou os dois — o conteúdo do arquivo será
          unido ao texto quando ambos forem enviados.
        </p>

        <div className="reuniao-ia-texto-panel">
          <button
            type="button"
            className="reuniao-ia-texto-panel__header"
            aria-expanded={textoTranscricaoAberto}
            aria-controls={idTextoPanelBody}
            onClick={() => setTextoTranscricaoAberto((v) => !v)}
          >
            <span className="reuniao-ia-texto-panel__title">Transcrição (colar texto)</span>
            <span className={`reuniao-ia-texto-panel__chevron${textoTranscricaoAberto ? " is-open" : ""}`} aria-hidden>
              ▼
            </span>
          </button>
          {!textoTranscricaoAberto && transcricao.trim() ? (
            <p className="reuniao-ia-texto-panel__resumo field-hint">
              {transcricao.length.toLocaleString("pt-BR")} caracteres colados —{" "}
              <button type="button" className="btn-link" onClick={() => setTextoTranscricaoAberto(true)}>
                expandir campo
              </button>
            </p>
          ) : null}
          <div className="reuniao-ia-texto-panel__body" id={idTextoPanelBody} hidden={!textoTranscricaoAberto}>
            <textarea
              className="reuniao-ia-textarea-exp"
              rows={8}
              value={transcricao}
              onChange={(e) => setTranscricao(e.target.value)}
              placeholder="Cole aqui a transcrição da reunião comercial (opcional se enviar arquivo)..."
              aria-label="Transcrição em texto"
            />
          </div>
        </div>

        <div className="reuniao-file-field">
          <span className="reuniao-file-field__label" id={`${idArquivoTranscricao}-label`}>
            Transcrição (arquivo)
          </span>
          <div className="reuniao-file-field__row" role="group" aria-labelledby={`${idArquivoTranscricao}-label`}>
            <input
              ref={refArquivoTranscricao}
              id={idArquivoTranscricao}
              type="file"
              multiple
              className="reuniao-file-input-native"
              accept={FILE_ACCEPT}
              onChange={(e) => setArquivosTranscricao(Array.from(e.target.files ?? []))}
            />
            <label htmlFor={idArquivoTranscricao} className="reuniao-file-picker-btn">
              Escolher arquivos
            </label>
            <span className="reuniao-file-field__name">
              {arquivosTranscricao.length === 0 ? (
                "Nenhum arquivo selecionado"
              ) : (
                <>
                  <strong>{arquivosTranscricao.length}</strong> arquivo(s): {arquivosTranscricao.map((f) => f.name).join(", ")}{" "}
                  <button type="button" className="btn-link" onClick={limparArquivosTranscricao}>
                    remover todos
                  </button>
                </>
              )}
            </span>
          </div>
          <span className="field-hint">
            Um ou vários arquivos de transcrição (.txt, .csv, .json, .pdf, .md, etc.); são unidos ao texto colado na ordem de
            envio. Com os complementares da reunião, no máximo {LLM_MAX_FILES_PER_REQUEST} arquivos por envio.
          </span>
        </div>

        <div className="reuniao-file-field">
          <span className="reuniao-file-field__label" id={`${idArquivosExtras}-label`}>
            Materiais complementares (opcional)
          </span>
          <div className="reuniao-file-field__row" role="group" aria-labelledby={`${idArquivosExtras}-label`}>
            <input
              ref={refArquivosExtras}
              id={idArquivosExtras}
              type="file"
              multiple
              className="reuniao-file-input-native"
              accept={FILE_ACCEPT}
              onChange={(e) => setFiles(Array.from(e.target.files ?? []))}
            />
            <label htmlFor={idArquivosExtras} className="reuniao-file-picker-btn">
              Escolher arquivos
            </label>
            <span className="reuniao-file-field__name">
              {files.length === 0
                ? "Nenhum arquivo selecionado"
                : `${files.length} arquivo(s): ${files.map((f) => f.name).join(", ")}`}
            </span>
          </div>
          <span className="field-hint">
            Anexos extras além da transcrição (ex.: proposta, lista de requisitos). Pode selecionar vários. Formatos: .txt, .csv,
            .json, .pdf, etc. Limite combinado transcrição (arquivo) + estes arquivos: {LLM_MAX_FILES_PER_REQUEST} por envio.
          </span>
        </div>
      </div>

      <div className="reuniao-ia-actions">
        <OportunidadeIconButton
          variant="outline-brand"
          label={processing ? "Processando com IA" : "Processar com IA"}
          icon={processing ? <IcoSpinner /> : <IcoSparkles />}
          onClick={() => void processarComIa()}
          disabled={processing}
        />
      </div>

      {error ? <p className="reuniao-ia-error">{error}</p> : null}
      {success ? <p className="reuniao-ia-success">{success}</p> : null}

      <div className="reuniao-ia-block">
        <h3>Resultado da análise</h3>
        {!selected ? (
          <p className="muted-text">Nenhuma análise selecionada.</p>
        ) : (
          <div className="reuniao-ia-result-grid">
            <div><strong>Status:</strong> {selected.ranStatus}</div>
            <div><strong>Resumo:</strong> {selected.ranResumo || "-"}</div>
            <div><strong>Feedback IA:</strong> {selected.ranFeedbackIa || "-"}</div>
            <div><strong>Lead score sugerido:</strong> {selected.ranLeadScoreSugerido ?? "-"}</div>
            <div><strong>Temperatura sugerida:</strong> {selected.ranTemperaturaSugerida || "-"}</div>
            <div><strong>Dores/oportunidades:</strong> {selected.ranDoresOportunidadesSugeridas || "-"}</div>
            <div><strong>Observações:</strong> {selected.ranObservacoesSugeridas || "-"}</div>
            <div><strong>Próximos passos:</strong> {selected.ranProximosPassosSugeridos || "-"}</div>
          </div>
        )}
      </div>

      <div className="reuniao-ia-block">
        <h3>Ações rápidas</h3>
        <p className="field-hint" style={{ marginTop: 0 }}>
          Ao aplicar, a página será recarregada para exibir os campos atualizados na oportunidade.
        </p>
        <div className="reuniao-ia-quick-actions reuniao-ia-quick-actions--all">
          <OportunidadeIconButton
            variant="outline-brand"
            label={applying ? "Aplicando todas as sugestões na oportunidade" : "Aplicar todas as sugestões na oportunidade"}
            icon={applying ? <IcoSpinner /> : <IcoLayers />}
            disabled={!selected || applying}
            onClick={() => void aplicarTodas()}
          />
        </div>
        <div className="reuniao-ia-quick-actions">
          <OportunidadeIconButton
            variant="subtle"
            label="Aplicar observações sugeridas na oportunidade"
            icon={<IcoMessage />}
            disabled={!selected || applying}
            onClick={() => void aplicarCampo("aplicar-observacoes", "Observações aplicadas na oportunidade.")}
          />
          <OportunidadeIconButton
            variant="subtle"
            label="Aplicar dores e oportunidades sugeridas"
            icon={<IcoList />}
            disabled={!selected || applying}
            onClick={() => void aplicarCampo("aplicar-dores-oportunidades", "Dores/oportunidades aplicadas na oportunidade.")}
          />
          <OportunidadeIconButton
            variant="subtle"
            label="Aplicar lead score sugerido"
            icon={<IcoTrending />}
            disabled={!selected || applying}
            onClick={() => void aplicarCampo("aplicar-lead-score", "Lead score aplicado na oportunidade.")}
          />
          <OportunidadeIconButton
            variant="subtle"
            label="Aplicar temperatura sugerida"
            icon={<IcoThermo />}
            disabled={!selected || applying}
            onClick={() => void aplicarCampo("aplicar-temperatura", "Temperatura aplicada na oportunidade.")}
          />
        </div>
      </div>

      <div className="reuniao-ia-block">
        <h3>Histórico</h3>
        {loadingHistory ? (
          <p className="muted-text">Carregando histórico...</p>
        ) : analises.length === 0 ? (
          <p className="muted-text">Nenhuma análise registrada para esta oportunidade.</p>
        ) : (
          <ul className="reuniao-ia-history-list">
            {analises.map((item) => (
              <li key={item.ranId}>
                <button
                  type="button"
                  className={selected?.ranId === item.ranId ? "is-active" : ""}
                  onClick={() => setSelectedRanId(item.ranId)}
                >
                  #{item.ranId} - {new Date(item.ranDataCriacao).toLocaleString("pt-BR")} - {item.ranStatus}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
};

export default ReuniaoIaSection;
