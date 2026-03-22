import React, { useEffect, useId, useMemo, useRef, useState } from "react";
import Modal from "../Modal";
import {
  OportunidadeIconButton,
  IcoSave,
  IcoSpinner,
  IcoLayers,
  IcoPublish,
  IcoLink,
  IcoExternalLink,
} from "../oportunidades/OportunidadeIconButton";
import ProposalPlansEditor from "./ProposalPlansEditor";
import ProposalProjectValueEditor from "./ProposalProjectValueEditor";
import ProposalPublicPage from "./ProposalPublicPage";
import ProposalScopeEditor from "./ProposalScopeEditor";
import ProposalDifferentialsEditor from "./ProposalDifferentialsEditor";
import { PropostaEventoItem, PropostaItem, PropostaTemplateItem, PropostaVersaoItem, TipoProposta } from "./types";
import { getPublicProposalUrl } from "../../utils/api";
import { useAuth } from "../../contexts/AuthContext";

interface UsuarioOption {
  usuId: number;
  usuNome: string;
  usuWhatsapp?: string | null;
}

interface Props {
  proposta: PropostaItem;
  templates: PropostaTemplateItem[];
  usuarios: UsuarioOption[];
  versoes: PropostaVersaoItem[];
  eventos: PropostaEventoItem[];
  responsavelOportunidadeId: number | null;
  onSave: (payload: Partial<PropostaItem>) => Promise<void>;
  onPublish: () => Promise<void>;
  onSaveAsTemplate: (payload: {
    ptlNome: string;
    ptlTipoSolucao: string | null;
    ptlTipoProposta: TipoProposta;
    ptlAtivo: boolean;
    ptlPadrao: boolean;
  }) => Promise<void>;
  onCopyLink: () => Promise<void>;
}

const tabs = ["dados", "conteudo", "escopo", "valores", "preview", "publicacao"] as const;
type EditorTab = (typeof tabs)[number];

const ProposalEditor: React.FC<Props> = ({
  proposta,
  templates,
  usuarios,
  versoes,
  eventos,
  responsavelOportunidadeId,
  onSave,
  onPublish,
  onSaveAsTemplate,
  onCopyLink,
}) => {
  const { api } = useAuth();
  const idImgApresentacao = useId();
  const idImgClientes = useId();
  const responsavelDefault = proposta.prpUsuResponsavelId ?? responsavelOportunidadeId ?? null;
  const [tab, setTab] = useState<EditorTab>("dados");
  const [saving, setSaving] = useState(false);
  const [uploadingContextImage, setUploadingContextImage] = useState(false);
  const [savedJustNow, setSavedJustNow] = useState(false);
  const [showPublishConfirm, setShowPublishConfirm] = useState(false);
  const [showTemplateModal, setShowTemplateModal] = useState(false);
  const [templateForm, setTemplateForm] = useState({
    ptlNome: "",
    ptlTipoSolucao: "",
    ptlTipoProposta: proposta.prpTipo as TipoProposta,
    ptlAtivo: true,
    ptlPadrao: false,
  });
  const [form, setForm] = useState({
    prpTitulo: proposta.prpTitulo,
    prpTipo: proposta.prpTipo as TipoProposta,
    prpTplId: proposta.prpTplId,
    prpUsuResponsavelId: responsavelDefault,
    prpNomeContato: proposta.prpNomeContato ?? "",
    prpEmailContato: proposta.prpEmailContato ?? "",
    prpWhatsappContato: proposta.prpWhatsappContato ?? "",
    prpObservacaoInterna: proposta.prpObservacaoInterna ?? "",
    prpJsonConfiguracao: (proposta.prpJsonConfiguracao ?? {}) as Record<string, unknown>,
  });
  const initialFormRef = useRef(JSON.stringify(form));

  useEffect(() => {
    const defaultResp = proposta.prpUsuResponsavelId ?? responsavelOportunidadeId ?? null;
    const next = {
      prpTitulo: proposta.prpTitulo,
      prpTipo: proposta.prpTipo as TipoProposta,
      prpTplId: proposta.prpTplId,
      prpUsuResponsavelId: defaultResp,
      prpNomeContato: proposta.prpNomeContato ?? "",
      prpEmailContato: proposta.prpEmailContato ?? "",
      prpWhatsappContato: proposta.prpWhatsappContato ?? "",
      prpObservacaoInterna: proposta.prpObservacaoInterna ?? "",
      prpJsonConfiguracao: (proposta.prpJsonConfiguracao ?? {}) as Record<string, unknown>,
    };
    setForm(next);
    initialFormRef.current = JSON.stringify(next);
  }, [proposta.prpId, proposta.prpTitulo, proposta.prpTipo, proposta.prpTplId, proposta.prpUsuResponsavelId, responsavelOportunidadeId, proposta.prpNomeContato, proposta.prpEmailContato, proposta.prpWhatsappContato, proposta.prpObservacaoInterna, proposta.prpJsonConfiguracao]);

  const config = form.prpJsonConfiguracao;
  const isDirty = useMemo(() => JSON.stringify(form) !== initialFormRef.current, [form]);

  const progress = useMemo(() => {
    const hero = (config.hero as Record<string, unknown>) ?? {};
    const apresentacao = (config.apresentacao as Record<string, unknown>) ?? {};
    const escopo = (config.escopo_inicial as Record<string, unknown>) ?? {};
    const cards = Array.isArray(escopo.cards) ? escopo.cards : [];
    const valoresPlanos = (config.valores_planos as Record<string, unknown>) ?? {};
    const planos = Array.isArray(valoresPlanos.planos) ? valoresPlanos.planos : [];
    const valoresProjeto = (config.valores_projeto as Record<string, unknown>) ?? {};
    const hasDados = Boolean(form.prpTitulo?.trim());
    const hasConteudo = Boolean(
      String(hero.titulo ?? "").trim() || String(hero.subtitulo ?? "").trim() || String(apresentacao.texto ?? "").trim()
    );
    const hasEscopo = cards.length > 0;
    const hasValores =
      form.prpTipo === "projeto" || form.prpTipo === "hibrida"
        ? Object.keys(valoresProjeto).length > 0
        : form.prpTipo === "planos" || form.prpTipo === "hibrida"
          ? planos.length > 0
          : false;
    return { hasDados, hasConteudo, hasEscopo, hasValores };
  }, [config, form.prpTitulo, form.prpTipo]);

  const progressPct = useMemo(() => {
    let n = 0;
    if (progress.hasDados) n += 25;
    if (progress.hasConteudo) n += 25;
    if (progress.hasEscopo) n += 25;
    if (progress.hasValores) n += 25;
    return n;
  }, [progress]);

  const statusBadgeClass = useMemo(() => {
    const s = (proposta.prpStatus || "").toLowerCase();
    if (/rascunho|draft/.test(s)) return "status-badge--rascunho";
    if (/publicad/.test(s)) return "status-badge--publicada";
    if (/visualizad/.test(s)) return "status-badge--visualizada";
    if (/aceit/.test(s)) return "status-badge--aceita";
    if (/arquivad/.test(s)) return "status-badge--arquivada";
    return "status-badge--default";
  }, [proposta.prpStatus]);

  const updateConfig = (key: string, value: unknown) => {
    setForm((prev) => ({
      ...prev,
      prpJsonConfiguracao: {
        ...prev.prpJsonConfiguracao,
        [key]: value,
      },
    }));
  };

  const handleContextImageUpload = async (file: File | null) => {
    if (!file) return;
    setUploadingContextImage(true);
    try {
      const data = new FormData();
      data.append("file", file);
      const res = await api.post<{ imageUrl?: string }>("/propostas/apresentacao/imagem/upload", data, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      const payload = res.data;
      if (!payload.imageUrl) throw new Error("Resposta inválida do upload");
      updateConfig("apresentacao", {
        ...((config.apresentacao as Record<string, unknown>) ?? {}),
        imagemUrl: payload.imageUrl,
      });
    } catch (err) {
      console.error(err);
      window.alert("Não foi possível enviar a imagem. Use PNG ou JPG.");
    } finally {
      setUploadingContextImage(false);
    }
  };

  const handleClientesImageUpload = async (file: File | null) => {
    if (!file) return;
    try {
      const data = new FormData();
      data.append("file", file);
      const res = await api.post<{ imageUrl?: string }>("/propostas/clientes/imagem/upload", data, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      const payload = res.data;
      if (!payload.imageUrl) throw new Error("Resposta inválida do upload");
      updateConfig("clientes", {
        ...((config.clientes as Record<string, unknown>) ?? {}),
        imagemUrl: payload.imageUrl,
      });
    } catch (err) {
      console.error(err);
      window.alert("Não foi possível enviar a imagem de clientes. Use PNG ou JPG.");
    }
  };

  const filteredTemplates = useMemo(
    () => templates.filter((t) => t.ptlTipoProposta === form.prpTipo || t.ptlTipoProposta === "hibrida"),
    [templates, form.prpTipo],
  );

  const save = async () => {
    setSaving(true);
    try {
      await onSave(form);
      initialFormRef.current = JSON.stringify(form);
      setSavedJustNow(true);
      setTimeout(() => setSavedJustNow(false), 3000);
    } finally {
      setSaving(false);
    }
  };

  const eventoLabel = (e: PropostaEventoItem) => {
    const t = (e.pevTipo || "").toLowerCase();
    if (t.includes("visualiz") || t.includes("view")) return { icon: "👁", label: "Visualização" };
    if (t.includes("link") || t.includes("abert")) return { icon: "🔗", label: "Link aberto" };
    if (t.includes("aceit") || t.includes("accept")) return { icon: "✔", label: "Proposta aceita" };
    return { icon: "•", label: e.pevTipo || "Evento" };
  };

  const stepLabels: Record<EditorTab, string> = {
    dados: "Dados Gerais",
    conteudo: "Conteúdo Base",
    escopo: "Escopo Inicial",
    valores: "Valores",
    preview: "Preview",
    publicacao: "Publicação",
  };

  const handlePublishClick = () => setShowPublishConfirm(true);
  const handlePublishConfirm = async () => {
    setShowPublishConfirm(false);
    await onPublish();
  };
  const openSaveTemplateModal = () => {
    setTemplateForm({
      ptlNome: `Template - ${form.prpTitulo}`,
      ptlTipoSolucao: "",
      ptlTipoProposta: form.prpTipo,
      ptlAtivo: true,
      ptlPadrao: false,
    });
    setShowTemplateModal(true);
  };
  const handleSaveTemplate = async (e: React.FormEvent) => {
    e.preventDefault();
    await onSaveAsTemplate({
      ptlNome: templateForm.ptlNome,
      ptlTipoSolucao: templateForm.ptlTipoSolucao || null,
      ptlTipoProposta: templateForm.ptlTipoProposta,
      ptlAtivo: templateForm.ptlAtivo,
      ptlPadrao: templateForm.ptlPadrao,
    });
    setShowTemplateModal(false);
  };

  return (
    <div className="proposal-editor-root">
      <div className="proposal-progress-bar surface-card">
        <div className="proposal-progress-checklist">
          <span className={progress.hasDados ? "proposal-progress-done" : "proposal-progress-pending"}>
            {progress.hasDados ? "✔" : "◻"} Dados
          </span>
          <span className={progress.hasConteudo ? "proposal-progress-done" : "proposal-progress-pending"}>
            {progress.hasConteudo ? "✔" : "◻"} Conteúdo
          </span>
          <span className={progress.hasEscopo ? "proposal-progress-done" : "proposal-progress-pending"}>
            {progress.hasEscopo ? "✔" : "◻"} Escopo
          </span>
          <span className={progress.hasValores ? "proposal-progress-done" : "proposal-progress-pending"}>
            {progress.hasValores ? "✔" : "◻"} Valores
          </span>
          <span className="proposal-progress-pending">◻ Publicação</span>
        </div>
        <p className="proposal-progress-text">Proposta {progressPct}% completa</p>
      </div>

      <div className="proposal-editor-steps" role="tablist">
        {tabs.map((t, i) => (
          <div key={t} className="proposal-editor-step">
            {i > 0 && (
              <span
                className={`proposal-editor-step-connector ${tabs.indexOf(tab) > i ? "is-done" : ""}`}
                aria-hidden
              />
            )}
            <button
              type="button"
              role="tab"
              aria-selected={tab === t}
              className={`proposal-editor-step-btn ${tab === t ? "is-active" : ""}`}
              onClick={() => setTab(t)}
            >
              {stepLabels[t]}
            </button>
          </div>
        ))}
      </div>

      <div className="proposal-editor-content surface-card">
        {tab === "dados" && (
          <>
            <section className="proposal-editor-section">
              <h3 className="proposal-editor-section-title">Informações da proposta</h3>
              <p className="proposal-editor-section-hint">Título, tipo e template que definem esta proposta.</p>
              <div className="form-grid">
                <label className="form-field form-field--full">
                  <span className="form-label">Título</span>
                  <input value={form.prpTitulo} onChange={(e) => setForm((prev) => ({ ...prev, prpTitulo: e.target.value }))} />
                </label>
                <label className="form-field">
                  <span className="form-label">Tipo</span>
                  <select
                    value={form.prpTipo}
                    onChange={(e) => setForm((prev) => ({ ...prev, prpTipo: e.target.value as TipoProposta }))}
                  >
                    <option value="projeto">Projeto</option>
                    <option value="planos">Planos</option>
                    <option value="hibrida">Híbrida</option>
                  </select>
                </label>
                <label className="form-field">
                  <span className="form-label">Template</span>
                  <select
                    value={form.prpTplId ?? ""}
                    onChange={(e) => setForm((prev) => ({ ...prev, prpTplId: e.target.value ? Number(e.target.value) : null }))}
                  >
                    <option value="">Sem template</option>
                    {filteredTemplates.map((tpl) => (
                      <option key={tpl.ptlId} value={tpl.ptlId}>
                        {tpl.ptlNome}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
            </section>
            <section className="proposal-editor-section">
              <h3 className="proposal-editor-section-title">Contato do cliente</h3>
              <p className="proposal-editor-section-hint">Dados do contato que receberá ou visualizará a proposta.</p>
              <div className="form-grid">
                <label className="form-field form-field--full">
                  <span className="form-label">Nome</span>
                  <input
                    value={form.prpNomeContato}
                    onChange={(e) => setForm((prev) => ({ ...prev, prpNomeContato: e.target.value }))}
                  />
                </label>
                <label className="form-field">
                  <span className="form-label">Email</span>
                  <input
                    type="email"
                    value={form.prpEmailContato}
                    onChange={(e) => setForm((prev) => ({ ...prev, prpEmailContato: e.target.value }))}
                  />
                </label>
                <label className="form-field">
                  <span className="form-label">WhatsApp</span>
                  <input
                    value={form.prpWhatsappContato}
                    onChange={(e) => setForm((prev) => ({ ...prev, prpWhatsappContato: e.target.value }))}
                  />
                </label>
              </div>
            </section>
            <section className="proposal-editor-section">
              <h3 className="proposal-editor-section-title">Informações internas</h3>
              <p className="proposal-editor-section-hint">Responsável e observações apenas para uso interno.</p>
              <div className="form-grid">
                <label className="form-field">
                  <span className="form-label">Responsável</span>
                  <select
                    value={form.prpUsuResponsavelId ?? ""}
                    onChange={(e) => setForm((prev) => ({ ...prev, prpUsuResponsavelId: e.target.value ? Number(e.target.value) : null }))}
                  >
                    <option value="">Sem responsável</option>
                    {usuarios.map((u) => (
                      <option key={u.usuId} value={u.usuId}>
                        {u.usuNome}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="form-field form-field--full">
                  <span className="form-label">Observação interna</span>
                  <textarea
                    rows={3}
                    value={form.prpObservacaoInterna}
                    onChange={(e) => setForm((prev) => ({ ...prev, prpObservacaoInterna: e.target.value }))}
                  />
                </label>
              </div>
            </section>
          </>
        )}

        {tab === "conteudo" && (
          <>
            <section className="proposal-editor-section">
              <h3 className="proposal-editor-section-title">Conteúdo base</h3>
              <p className="proposal-editor-section-hint">
                Título, subtítulo e apresentação visual em duas colunas que aparecem no topo da proposta.
              </p>
              <div className="proposal-editor-stack">
                <label>
                  Hero - Título
                  <input
                    value={String(((config.hero as Record<string, unknown>) ?? {}).titulo ?? "")}
                    onChange={(e) =>
                      updateConfig("hero", {
                        ...((config.hero as Record<string, unknown>) ?? {}),
                        titulo: e.target.value,
                      })
                    }
                  />
                </label>
                <label>
                  Hero - Subtítulo
                  <input
                    value={String(((config.hero as Record<string, unknown>) ?? {}).subtitulo ?? "")}
                    onChange={(e) =>
                      updateConfig("hero", {
                        ...((config.hero as Record<string, unknown>) ?? {}),
                        subtitulo: e.target.value,
                      })
                    }
                  />
                </label>
                <label>
                  Apresentação - Título
                  <input
                    value={String(((config.apresentacao as Record<string, unknown>) ?? {}).titulo ?? "")}
                    onChange={(e) =>
                      updateConfig("apresentacao", {
                        ...((config.apresentacao as Record<string, unknown>) ?? {}),
                        titulo: e.target.value,
                      })
                    }
                  />
                </label>
                <label>
                  Apresentação - Badge (opcional)
                  <input
                    value={String(((config.apresentacao as Record<string, unknown>) ?? {}).badge ?? "")}
                    onChange={(e) =>
                      updateConfig("apresentacao", {
                        ...((config.apresentacao as Record<string, unknown>) ?? {}),
                        badge: e.target.value,
                      })
                    }
                  />
                </label>
                <label>
                  Apresentação - Descrição
                  <textarea
                    rows={4}
                    value={String(((config.apresentacao as Record<string, unknown>) ?? {}).texto ?? "")}
                    onChange={(e) =>
                      updateConfig("apresentacao", {
                        ...((config.apresentacao as Record<string, unknown>) ?? {}),
                        texto: e.target.value,
                      })
                    }
                  />
                </label>
                <label>
                  Apresentação - Pontos (um por linha)
                  <textarea
                    rows={3}
                    value={Array.isArray(((config.apresentacao as Record<string, unknown>) ?? {}).pontos)
                      ? ((config.apresentacao as Record<string, unknown>).pontos as unknown[]).map((p) => String(p ?? "")).join("\n")
                      : ""}
                    onChange={(e) =>
                      updateConfig("apresentacao", {
                        ...((config.apresentacao as Record<string, unknown>) ?? {}),
                        pontos: e.target.value
                          .split("\n")
                          .map((line) => line.trim())
                          .filter((line) => line.length > 0),
                      })
                    }
                  />
                </label>
                <label>
                  Apresentação - Imagem (URL opcional)
                  <input
                    value={String(((config.apresentacao as Record<string, unknown>) ?? {}).imagemUrl ?? "")}
                    onChange={(e) =>
                      updateConfig("apresentacao", {
                        ...((config.apresentacao as Record<string, unknown>) ?? {}),
                        imagemUrl: e.target.value,
                      })
                    }
                  />
                </label>
                <div className="reuniao-file-field">
                  <span className="reuniao-file-field__label" id={`${idImgApresentacao}-lbl`}>
                    Apresentação — upload de imagem (.png / .jpg)
                  </span>
                  <div className="reuniao-file-field__row" aria-labelledby={`${idImgApresentacao}-lbl`}>
                    <input
                      id={idImgApresentacao}
                      type="file"
                      accept="image/png,image/jpeg"
                      className="reuniao-file-input-native"
                      onChange={(e) => void handleContextImageUpload(e.target.files?.[0] ?? null)}
                    />
                    <label htmlFor={idImgApresentacao} className="reuniao-file-picker-btn">
                      Escolher imagem
                    </label>
                    <span className="reuniao-file-field__name">
                      {uploadingContextImage ? "Enviando…" : "PNG ou JPG"}
                    </span>
                  </div>
                </div>
              </div>
            </section>
            <section className="proposal-editor-section">
              <h3 className="proposal-editor-section-title">Diferenciais</h3>
              <p className="proposal-editor-section-hint">
                Cards de diferenciais competitivos, com ícones, exibidos na proposta pública.
              </p>
              <ProposalDifferentialsEditor
                value={((config.metodologia as Record<string, unknown>) ?? {}) as Record<string, unknown>}
                onChange={(next) => updateConfig("metodologia", next)}
              />
            </section>
            <section className="proposal-editor-section">
              <h3 className="proposal-editor-section-title">Clientes</h3>
              <p className="proposal-editor-section-hint">
                Título, subtítulo e imagem em destaque dos clientes na proposta pública.
              </p>
              <div className="proposal-editor-stack">
                <label>
                  Clientes - Título
                  <input
                    value={String(((config.clientes as Record<string, unknown>) ?? {}).titulo ?? "")}
                    onChange={(e) =>
                      updateConfig("clientes", {
                        ...((config.clientes as Record<string, unknown>) ?? {}),
                        titulo: e.target.value,
                      })
                    }
                  />
                </label>
                <label>
                  Clientes - Subtítulo
                  <input
                    value={String(((config.clientes as Record<string, unknown>) ?? {}).subtitulo ?? "")}
                    onChange={(e) =>
                      updateConfig("clientes", {
                        ...((config.clientes as Record<string, unknown>) ?? {}),
                        subtitulo: e.target.value,
                      })
                    }
                  />
                </label>
                <label>
                  Clientes - Imagem (URL opcional)
                  <input
                    value={String(((config.clientes as Record<string, unknown>) ?? {}).imagemUrl ?? "")}
                    onChange={(e) =>
                      updateConfig("clientes", {
                        ...((config.clientes as Record<string, unknown>) ?? {}),
                        imagemUrl: e.target.value,
                      })
                    }
                  />
                  <span className="field-hint">
                    Use uma imagem ilustrativa ou composição com logos dos clientes, seguindo o padrão visual da landing page.
                  </span>
                </label>
                <div className="reuniao-file-field">
                  <span className="reuniao-file-field__label" id={`${idImgClientes}-lbl`}>
                    Clientes — upload de imagem (.png / .jpg)
                  </span>
                  <div className="reuniao-file-field__row" aria-labelledby={`${idImgClientes}-lbl`}>
                    <input
                      id={idImgClientes}
                      type="file"
                      accept="image/png,image/jpeg"
                      className="reuniao-file-input-native"
                      onChange={(e) => void handleClientesImageUpload(e.target.files?.[0] ?? null)}
                    />
                    <label htmlFor={idImgClientes} className="reuniao-file-picker-btn">
                      Escolher imagem
                    </label>
                    <span className="reuniao-file-field__name">PNG ou JPG</span>
                  </div>
                </div>
              </div>
            </section>
          </>
        )}

        {tab === "escopo" && (
          <ProposalScopeEditor
            propostaId={proposta.prpId}
            value={((config.escopo_inicial as Record<string, unknown>) ?? { visivel: true, cards: [] }) as Record<string, unknown>}
            onChange={(next) => updateConfig("escopo_inicial", next)}
          />
        )}

        {tab === "valores" && (
          <div className="proposal-editor-stack">
            {(form.prpTipo === "projeto" || form.prpTipo === "hibrida") && (
              <ProposalProjectValueEditor
                value={((config.valores_projeto as Record<string, unknown>) ?? {}) as Record<string, unknown>}
                onChange={(next) => updateConfig("valores_projeto", next)}
              />
            )}
            {(form.prpTipo === "planos" || form.prpTipo === "hibrida") && (
              <section className="proposal-editor-section">
                <h3 className="proposal-editor-section-title">Planos recorrentes</h3>
                <p className="proposal-editor-section-hint">
                  Título, subtítulo e planos que serão exibidos na seção de valores em planos.
                </p>
                <div className="proposal-editor-stack">
                  <label>
                    Valores (planos) - Título da seção (página pública)
                    <input
                      value={String(((config.valores_planos as Record<string, unknown>) ?? {}).titulo ?? "")}
                      onChange={(e) =>
                        updateConfig("valores_planos", {
                          ...((config.valores_planos as Record<string, unknown>) ?? {}),
                          titulo: e.target.value,
                        })
                      }
                    />
                  </label>
                  <label>
                    Valores (planos) - Subtítulo da seção (página pública)
                    <input
                      value={String(((config.valores_planos as Record<string, unknown>) ?? {}).subtitulo ?? "")}
                      onChange={(e) =>
                        updateConfig("valores_planos", {
                          ...((config.valores_planos as Record<string, unknown>) ?? {}),
                          subtitulo: e.target.value,
                        })
                      }
                    />
                  </label>
                </div>
                <ProposalPlansEditor
                  planos={(((config.valores_planos as Record<string, unknown>) ?? {}).planos as Array<Record<string, unknown>>) ?? []}
                  onChange={(next) =>
                    updateConfig("valores_planos", {
                      ...((config.valores_planos as Record<string, unknown>) ?? {}),
                      planos: next,
                    })
                  }
                />
              </section>
            )}
          </div>
        )}

        {tab === "preview" && (
          <div className="proposal-preview-tab">
            <div className="proposal-preview-tab-header">
              <h3 className="section-title section-title--panel">Preview da proposta</h3>
              <p className="proposal-preview-tab-subtitle">Assim o cliente visualizará esta página.</p>
            </div>
            <div className="proposal-preview-outer">
              <div className="proposal-preview-landing">
                <ProposalPublicPage token={proposta.prpTokenPublico} isPreview />
              </div>
            </div>
          </div>
        )}

        {tab === "publicacao" && (
          <div className="proposal-publicacao-tab">
            <section className="proposal-publicacao-section">
              <h3 className="proposal-editor-section-title">Link da proposta</h3>
              <p className="proposal-editor-section-hint">Compartilhe o link com o cliente para visualização ou aceite.</p>
              <div className="proposal-publicacao-link-actions">
                <OportunidadeIconButton variant="subtle" label="Copiar link da proposta" icon={<IcoLink />} onClick={onCopyLink} />
                <OportunidadeIconButton
                  variant="outline-brand"
                  label="Abrir página pública da proposta em nova aba"
                  icon={<IcoExternalLink />}
                  onClick={() => window.open(getPublicProposalUrl(proposta.prpTokenPublico), "_blank")}
                />
              </div>
            </section>
            <section className="proposal-publicacao-section">
              <h3 className="proposal-editor-section-title">Status da proposta</h3>
              <p className="proposal-editor-section-hint">Status e versão atual da proposta.</p>
              <div className="proposal-publicacao-status">
                <p className="muted-text" style={{ margin: 0 }}>
                  Status: <span className={`status-badge ${statusBadgeClass}`}>{proposta.prpStatus}</span>
                </p>
                <p className="muted-text" style={{ margin: 0 }}>
                  Versão atual: <strong>{proposta.prpVersaoAtual ?? "—"}</strong>
                </p>
                <button type="button" className="btn-outline-brand proposta-editor-inline-action" onClick={handlePublishClick}>
                  <span className="proposta-editor-inline-action__ico" aria-hidden>
                    <IcoPublish />
                  </span>
                  Publicar proposta
                </button>
              </div>
            </section>
            <section className="proposal-publicacao-section versoes-section">
              <h3 className="proposal-editor-section-title">Versões da proposta</h3>
              {versoes.length === 0 ? (
                <p className="muted-text">Nenhuma versão registrada.</p>
              ) : (
                <ul className="versoes-list">
                  {versoes.map((v) => (
                    <li key={v.prvId} className="versao-card">
                      <div className="versao-card-info">
                        <h4>Versão {v.prvNumero}</h4>
                        <p className="versao-card-meta">
                          {v.prvPublicada ? "Publicada" : "Rascunho"}
                          {v.prvDataPublicacao
                            ? ` em ${new Date(v.prvDataPublicacao).toLocaleDateString("pt-BR", {
                                day: "2-digit",
                                month: "2-digit",
                                year: "numeric",
                              })}`
                            : ""}
                        </p>
                      </div>
                      <div className="versao-card-actions">
                        <button
                          type="button"
                          onClick={() => window.open(getPublicProposalUrl(proposta.prpTokenPublico), "_blank")}
                        >
                          Ver versão
                        </button>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </section>
            <section className="proposal-publicacao-section eventos-section">
              <h3 className="proposal-editor-section-title">Eventos públicos</h3>
              {eventos.length === 0 ? (
                <p className="muted-text">Nenhum evento registrado.</p>
              ) : (
                <ul className="eventos-timeline">
                  {eventos.map((e) => {
                    const { icon, label } = eventoLabel(e);
                    return (
                      <li key={e.pevId}>
                        <span className="eventos-timeline-icon">{icon}</span>
                        <span className="eventos-timeline-label">{label}</span>
                        <div className="eventos-timeline-date">
                          {new Date(e.pevDataEvento).toLocaleString("pt-BR", {
                            day: "2-digit",
                            month: "2-digit",
                            year: "numeric",
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </div>
                      </li>
                    );
                  })}
                </ul>
              )}
            </section>
          </div>
        )}
      </div>

      <div className="proposal-editor-actions-bar">
        <div className="proposal-editor-actions-status">
          {savedJustNow && <span className="proposal-status proposal-status--saved">Proposta salva</span>}
          {isDirty && !savedJustNow && <span className="proposal-status proposal-status--dirty">Alterações não salvas</span>}
        </div>
        <div className="proposal-editor-actions-buttons">
          <button type="button" className="btn-subtle proposta-editor-text-action" onClick={openSaveTemplateModal}>
            <span className="proposta-editor-text-action__ico" aria-hidden>
              <IcoLayers />
            </span>
            Salvar como template
          </button>
          <OportunidadeIconButton
            variant="outline-brand"
            label={saving ? "Salvando proposta" : "Salvar alterações da proposta"}
            icon={saving ? <IcoSpinner /> : <IcoSave />}
            onClick={() => void save()}
            disabled={saving}
          />
          <OportunidadeIconButton
            variant="outline-brand"
            label="Publicar proposta"
            icon={<IcoPublish />}
            onClick={handlePublishClick}
          />
        </div>
      </div>

      {showPublishConfirm && (
        <div className="modal-backdrop" onClick={() => setShowPublishConfirm(false)}>
          <div className="modal proposal-publish-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Publicar proposta</h2>
              <button type="button" aria-label="Fechar" onClick={() => setShowPublishConfirm(false)}>×</button>
            </div>
            <div className="modal-body">
              <p>Tem certeza que deseja publicar esta proposta?</p>
              <p className="muted-text" style={{ marginTop: "0.5rem" }}>
                Uma nova versão será criada e o link público ficará disponível para o cliente.
              </p>
              <div className="modal-actions" style={{ marginTop: "1.25rem" }}>
                <button type="button" onClick={() => setShowPublishConfirm(false)}>
                  Cancelar
                </button>
                <button type="button" className="btn-primary" onClick={handlePublishConfirm}>
                  Publicar proposta
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
      <Modal isOpen={showTemplateModal} title="Salvar como template" onClose={() => setShowTemplateModal(false)}>
        <form className="form-vertical" onSubmit={handleSaveTemplate}>
          <label>
            Nome do template
            <input
              value={templateForm.ptlNome}
              onChange={(e) => setTemplateForm((prev) => ({ ...prev, ptlNome: e.target.value }))}
              required
            />
          </label>
          <label>
            Produto / solução
            <input
              value={templateForm.ptlTipoSolucao}
              onChange={(e) => setTemplateForm((prev) => ({ ...prev, ptlTipoSolucao: e.target.value }))}
              placeholder="Ex.: CRM, BI, Automação"
            />
          </label>
          <label>
            Tipo da proposta
            <select
              value={templateForm.ptlTipoProposta}
              onChange={(e) => setTemplateForm((prev) => ({ ...prev, ptlTipoProposta: e.target.value as TipoProposta }))}
            >
              <option value="projeto">Projeto</option>
              <option value="planos">Planos</option>
              <option value="hibrida">Híbrida</option>
            </select>
          </label>
          <label className="checkbox-inline">
            <input
              type="checkbox"
              checked={templateForm.ptlAtivo}
              onChange={(e) => setTemplateForm((prev) => ({ ...prev, ptlAtivo: e.target.checked }))}
            />
            Ativo
          </label>
          <label className="checkbox-inline">
            <input
              type="checkbox"
              checked={templateForm.ptlPadrao}
              onChange={(e) => setTemplateForm((prev) => ({ ...prev, ptlPadrao: e.target.checked }))}
            />
            Template padrão
          </label>
          <div className="modal-actions">
            <button type="button" onClick={() => setShowTemplateModal(false)}>
              Cancelar
            </button>
            <button type="submit" className="btn-primary">
              Salvar template
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};

export default ProposalEditor;

