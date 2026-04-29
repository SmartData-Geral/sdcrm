import React, { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams, useLocation } from "react-router-dom";
import Layout from "../../components/Layout";
import Loader from "../../components/Loader";
import ActionIconButton from "../../components/ActionIconButton";
import Modal from "../../components/Modal";
import { useAuth } from "../../contexts/AuthContext";
import ContratoPreviewPanel from "../../components/contratos/ContratoPreviewPanel";

import { ContratoClausula, ContratoItem, ContratoItem as ContratoItemType } from "../../components/contratos/wizardTypes";
import { ContratoModeloItem } from "../../components/contratos/types";

type Step = 1 | 2 | 3 | 4;

interface ContratoModeloListResponse {
  items: ContratoModeloItem[];
  total: number;
  page: number;
  page_size: number;
}

/** Dados vindos da API após inativar o contrato anterior; pré-preenchem o passo 2. */
type ContratoNovoPrefill = ContratoItem;

const ContratoNovoPage: React.FC = () => {
  const { api } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const params = useParams<{ opoId?: string }>();
  const opoId = params.opoId ? Number(params.opoId) : null;

  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState<Step>(1);

  const [models, setModels] = useState<ContratoModeloItem[]>([]);
  const [selectedModelId, setSelectedModelId] = useState<number | null>(null);
  const [modelFallbackHint, setModelFallbackHint] = useState<string | null>(null);

  const [contractId, setContractId] = useState<number | null>(null);
  const [tokenPublico, setTokenPublico] = useState<string | null>(null);
  const [clauses, setClauses] = useState<ContratoClausula[]>([]);
  const [clausesLoading, setClausesLoading] = useState(false);

  const [expandedClauseId, setExpandedClauseId] = useState<number | null>(null);
  const [clauseDraft, setClauseDraft] = useState<{ cclTitulo: string; cclTexto: string } | null>(null);
  const [savingClauseId, setSavingClauseId] = useState<number | null>(null);

  const [dados, setDados] = useState({
    ctrRazaoSocial: "",
    ctrCnpj: "",
    ctrEndereco: "",
    ctrResponsavelNome: "",
    ctrResponsavelCpf: "",
    ctrObjetoContrato: "",
    ctrValorContrato: "" as number | "",
    ctrDataInicio: "",
    ctrPrazoConclusao: "90 (noventa) dias",
    ctrDiasPagamento: 30 as number | "",
    ctrDiasAntecedenciaRescisao: 30 as number | "",
    ctrValorManutencao: 390 as number | "",
    ctrHorasMelhoriasMensais: 8 as number | "",
  });

  const [savingAsVar, setSavingAsVar] = useState(false);
  const [varNameDraft, setVarNameDraft] = useState("");
  const [isVarModalOpen, setIsVarModalOpen] = useState(false);
  const [varForClauseId, setVarForClauseId] = useState<number | null>(null);

  const stepTitle = useMemo(() => {
    if (step === 1) return "1) Modelo base";
    if (step === 2) return "2) Dados do contrato";
    if (step === 3) return "3) Cláusulas (snapshot)";
    return "4) Finalização";
  }, [step]);

  const dadosFromContratoPrefill = (prefill: ContratoNovoPrefill) => {
    const di =
      typeof prefill.ctrDataInicio === "string"
        ? prefill.ctrDataInicio.slice(0, 10)
        : "";
    return {
      ctrRazaoSocial: prefill.ctrRazaoSocial ?? "",
      ctrCnpj: prefill.ctrCnpj ?? "",
      ctrEndereco: prefill.ctrEndereco ?? "",
      ctrResponsavelNome: prefill.ctrResponsavelNome ?? "",
      ctrResponsavelCpf: prefill.ctrResponsavelCpf ?? "",
      ctrObjetoContrato: prefill.ctrObjetoContrato ?? "",
      ctrValorContrato: prefill.ctrValorContrato ?? ("" as number | ""),
      ctrDataInicio: di,
      ctrPrazoConclusao: (prefill.ctrPrazoConclusao ?? "90 (noventa) dias").trim() || "90 (noventa) dias",
      ctrDiasPagamento: typeof prefill.ctrDiasPagamento === "number" ? prefill.ctrDiasPagamento : ("" as number | ""),
      ctrDiasAntecedenciaRescisao:
        typeof prefill.ctrDiasAntecedenciaRescisao === "number" ? prefill.ctrDiasAntecedenciaRescisao : ("" as number | ""),
      ctrValorManutencao:
        typeof prefill.ctrValorManutencao === "number" ? prefill.ctrValorManutencao : ("" as number | ""),
      ctrHorasMelhoriasMensais:
        typeof prefill.ctrHorasMelhoriasMensais === "number" ? prefill.ctrHorasMelhoriasMensais : ("" as number | ""),
    };
  };

  const loadModelsInitial = async (navStateSnapshot: unknown) => {
    const parsed = navStateSnapshot as { prefillContrato?: ContratoNovoPrefill } | undefined;
    const ctrIdCandidate = parsed?.prefillContrato?.ctrId;
    const prefill =
      parsed?.prefillContrato != null && typeof ctrIdCandidate === "number"
        ? parsed.prefillContrato
        : undefined;

    const res = await api.get<ContratoModeloListResponse>("/contratos-modelo", { params: { page_size: 100, page: 1 } });
    const items = res.data.items ?? [];
    setModels(items);

    if (prefill && opoId) {
      setSelectedModelId(prefill.ctrCtmId);
      setDados(dadosFromContratoPrefill(prefill));
      setModelFallbackHint("Campos recuperados do contrato anterior.");
      setStep(2);
      navigate(".", { replace: true, state: {} });
      return;
    }

    const ativos = items.filter((m) => m.ctmAtivo);
    if (ativos.length > 0) {
      const sorted = [...ativos].sort(
        (a, b) => new Date(b.ctmDataCriacao).getTime() - new Date(a.ctmDataCriacao).getTime()
      );
      setSelectedModelId(sorted[0].ctmId);
      setModelFallbackHint("Modelo base recomendado (último ativo) selecionado automaticamente.");
    }
  };

  const loadClauses = async (ctrId: number) => {
    setClausesLoading(true);
    try {
      const res = await api.get<ContratoClausula[]>(`/contratos/${ctrId}/clausulas`);
      setClauses(res.data ?? []);
    } finally {
      setClausesLoading(false);
    }
  };

  useEffect(() => {
    const navStateSnapshot = location.state;
    void loadModelsInitial(navStateSnapshot);
    // Somente navegações distintas; não dependemos de `location.state` após o navigate replace nos pré-preencidos.
    // eslint-disable-next-line react-hooks/exhaustive-deps -- location.state intencionalmente omitido das deps
  }, [location.key, opoId]);

  const onToggleUtilizar = async (clause: ContratoClausula, utilizar: boolean) => {
    if (!contractId) return;
    const res = utilizar
      ? await api.patch<ContratoClausula>(`/contratos/${contractId}/clausulas/${clause.cclId}/utilizar`)
      : await api.patch<ContratoClausula>(`/contratos/${contractId}/clausulas/${clause.cclId}/nao-utilizar`);
    setClauses((prev) => prev.map((x) => (x.cclId === clause.cclId ? res.data : x)));
  };

  const onSelectVersion = async (clause: ContratoClausula, cmvId: number | null) => {
    if (!contractId) return;
    const res = await api.put<ContratoClausula>(`/contratos/${contractId}/clausulas/${clause.cclId}`, {
      cclCmvId: cmvId,
    });
    setClauses((prev) => prev.map((x) => (x.cclId === clause.cclId ? res.data : x)));
    if (expandedClauseId === clause.cclId) {
      setClauseDraft({ cclTitulo: res.data.cclTitulo, cclTexto: res.data.cclTexto });
    }
  };

  const saveClauseEdits = async (clauseId: number) => {
    if (!contractId || !clauseDraft) return;
    setSavingClauseId(clauseId);
    try {
      const res = await api.put<ContratoClausula>(`/contratos/${contractId}/clausulas/${clauseId}`, {
        cclTitulo: clauseDraft.cclTitulo.trim(),
        cclTexto: clauseDraft.cclTexto,
      });
      setClauses((prev) => prev.map((x) => (x.cclId === clauseId ? res.data : x)));
      setExpandedClauseId(null);
      setClauseDraft(null);
    } finally {
      setSavingClauseId(null);
    }
  };

  const openClauseEdit = (c: ContratoClausula) => {
    setExpandedClauseId(c.cclId);
    setClauseDraft({ cclTitulo: c.cclTitulo, cclTexto: c.cclTexto });
  };

  const openSaveAsVariation = (clauseId: number) => {
    setVarForClauseId(clauseId);
    setVarNameDraft("");
    setIsVarModalOpen(true);
  };

  const saveAsVariation = async () => {
    if (!contractId || varForClauseId == null) return;
    setSavingAsVar(true);
    try {
      const res = await api.post<ContratoClausula>(
        `/contratos/${contractId}/clausulas/${varForClauseId}/salvar-como-variacao`,
        { cmvNome: varNameDraft.trim() ? varNameDraft.trim() : null }
      );
      setClauses((prev) => prev.map((x) => (x.cclId === varForClauseId ? res.data : x)));
      setIsVarModalOpen(false);
    } finally {
      setSavingAsVar(false);
    }
  };

  const createContractAndLoad = async () => {
    if (selectedModelId == null) return alert("Selecione um modelo de contrato.");

    if (!dados.ctrRazaoSocial.trim()) return alert("Informe a razão social.");
    if (!dados.ctrCnpj.trim()) return alert("Informe o CNPJ.");
    if (!dados.ctrEndereco.trim()) return alert("Informe o endereço.");
    if (!dados.ctrResponsavelNome.trim()) return alert("Informe o nome do responsável.");
    if (!dados.ctrResponsavelCpf.trim()) return alert("Informe o CPF do responsável.");
    if (!dados.ctrObjetoContrato.trim()) return alert("Informe o objeto do contrato.");
    if (dados.ctrValorContrato === "" || Number(dados.ctrValorContrato) <= 0) return alert("Informe o valor do contrato.");
    if (!dados.ctrDataInicio) return alert("Informe a data de início.");
    if (!dados.ctrPrazoConclusao.trim()) return alert("Informe o prazo de conclusão.");
    if (dados.ctrDiasPagamento === "" || Number(dados.ctrDiasPagamento) < 0) return alert("Informe os dias para o primeiro pagamento.");
    if (dados.ctrDiasAntecedenciaRescisao === "" || Number(dados.ctrDiasAntecedenciaRescisao) < 0) {
      return alert("Informe os dias de antecedência para rescisão.");
    }
    if (dados.ctrValorManutencao === "" || Number(dados.ctrValorManutencao) < 0) return alert("Informe o valor da manutenção.");
    if (dados.ctrHorasMelhoriasMensais === "" || Number(dados.ctrHorasMelhoriasMensais) < 0) {
      return alert("Informe as horas de melhorias mensais (valor inteiro, ex.: 8).");
    }

    setLoading(true);
    try {
      const payload = {
        ctrCtmId: selectedModelId,
        ctrOpoId: opoId,
        ctrNome: `Contrato - ${opoId ? `Oportunidade #${opoId}` : "Avulso"}`,
        ctrRazaoSocial: dados.ctrRazaoSocial,
        ctrCnpj: dados.ctrCnpj,
        ctrEndereco: dados.ctrEndereco,
        ctrResponsavelNome: dados.ctrResponsavelNome,
        ctrResponsavelCpf: dados.ctrResponsavelCpf,
        ctrObjetoContrato: dados.ctrObjetoContrato,
        ctrValorContrato: Number(dados.ctrValorContrato),
        ctrDataInicio: dados.ctrDataInicio,
        ctrPrazoConclusao: dados.ctrPrazoConclusao.trim(),
        ctrDiasPagamento: Number(dados.ctrDiasPagamento),
        ctrDiasAntecedenciaRescisao: Number(dados.ctrDiasAntecedenciaRescisao),
        ctrValorManutencao: Number(dados.ctrValorManutencao),
        ctrHorasMelhoriasMensais: Number(dados.ctrHorasMelhoriasMensais),
      };

      const res = opoId
        ? await api.post<ContratoItem>(`/oportunidades/${opoId}/contrato`, payload)
        : await api.post<ContratoItem>(`/contratos`, { ...payload, ctrOpoId: null });

      setContractId(res.data.ctrId);
      setTokenPublico(res.data.ctrTokenPublico ?? null);
      await loadClauses(res.data.ctrId);
      setStep(3);
    } catch (e: any) {
      alert(e?.response?.data?.detail ?? "Erro ao criar contrato");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Layout>
      {loading ? <Loader /> : null}

      <section className="surface-card details-card" style={{ marginTop: "1rem" }}>
        <h2 className="section-title section-title--panel">{stepTitle}</h2>

        {step === 1 && (
          <div className="form-vertical">
            {modelFallbackHint ? <p className="muted-text">{modelFallbackHint}</p> : null}
            <label>
              Modelo de contrato
              <select
                value={selectedModelId ?? ""}
                onChange={(e) => {
                  const v = e.target.value ? Number(e.target.value) : null;
                  setSelectedModelId(v);
                  setModelFallbackHint(null);
                }}
              >
                <option value="">Selecione</option>
                {models
                  .filter((m) => m.ctmAtivo)
                  .map((m) => (
                    <option key={m.ctmId} value={m.ctmId}>
                      {m.ctmNome}
                    </option>
                  ))}
              </select>
            </label>

            <div className="modal-actions" style={{ marginTop: "1rem" }}>
              <button type="button" className="btn-primary" onClick={() => setStep(2)} disabled={selectedModelId == null}>
                Continuar
              </button>
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="form-vertical">
            <label>
              Razão social
              <input value={dados.ctrRazaoSocial} onChange={(e) => setDados((d) => ({ ...d, ctrRazaoSocial: e.target.value }))} required />
            </label>
            <label>
              CNPJ
              <input value={dados.ctrCnpj} onChange={(e) => setDados((d) => ({ ...d, ctrCnpj: e.target.value }))} required />
            </label>
            <label>
              Endereço
              <input value={dados.ctrEndereco} onChange={(e) => setDados((d) => ({ ...d, ctrEndereco: e.target.value }))} required />
            </label>
            <label>
              Nome do responsável
              <input value={dados.ctrResponsavelNome} onChange={(e) => setDados((d) => ({ ...d, ctrResponsavelNome: e.target.value }))} required />
            </label>
            <label>
              CPF do responsável
              <input value={dados.ctrResponsavelCpf} onChange={(e) => setDados((d) => ({ ...d, ctrResponsavelCpf: e.target.value }))} required />
            </label>

            <label>
              Objeto do contrato
              <textarea rows={4} value={dados.ctrObjetoContrato} onChange={(e) => setDados((d) => ({ ...d, ctrObjetoContrato: e.target.value }))} required />
            </label>
            <label>
              Valor do contrato
              <input
                type="number"
                step="0.01"
                min="0"
                value={dados.ctrValorContrato}
                onChange={(e) => setDados((d) => ({ ...d, ctrValorContrato: e.target.value === "" ? "" : Number(e.target.value) }))}
                required
              />
            </label>
            <label>
              Data de início
              <input type="date" value={dados.ctrDataInicio} onChange={(e) => setDados((d) => ({ ...d, ctrDataInicio: e.target.value }))} required />
            </label>
            <label>
              Prazo de conclusão (texto nas cláusulas)
              <input
                value={dados.ctrPrazoConclusao}
                onChange={(e) => setDados((d) => ({ ...d, ctrPrazoConclusao: e.target.value }))}
                required
              />
            </label>
            <label>
              Dias para o primeiro pagamento
              <input
                type="number"
                min={0}
                max={3660}
                value={dados.ctrDiasPagamento}
                onChange={(e) =>
                  setDados((d) => ({
                    ...d,
                    ctrDiasPagamento: e.target.value === "" ? "" : Number(e.target.value),
                  }))
                }
                required
              />
            </label>
            <label>
              Dias de antecedência para rescisão
              <input
                type="number"
                min={0}
                max={3660}
                value={dados.ctrDiasAntecedenciaRescisao}
                onChange={(e) =>
                  setDados((d) => ({
                    ...d,
                    ctrDiasAntecedenciaRescisao: e.target.value === "" ? "" : Number(e.target.value),
                  }))
                }
                required
              />
            </label>
            <label>
              Valor da manutenção
              <input
                type="number"
                step="0.01"
                min="0"
                value={dados.ctrValorManutencao}
                onChange={(e) =>
                  setDados((d) => ({
                    ...d,
                    ctrValorManutencao: e.target.value === "" ? "" : Number(e.target.value),
                  }))
                }
                required
              />
            </label>
            <label>
              Horas de melhorias mensais
              <span className="muted-text" style={{ display: "block", fontWeight: 400, fontSize: "0.9em", marginBottom: 6 }}>
                Usada nos textos do modelo como macro <code>{"{{horas_melhorias_mensais}}"}</code> (número inteiro).
              </span>
              <input
                type="number"
                min={0}
                max={744}
                step={1}
                value={dados.ctrHorasMelhoriasMensais}
                onChange={(e) =>
                  setDados((d) => ({
                    ...d,
                    ctrHorasMelhoriasMensais: e.target.value === "" ? "" : Number(e.target.value),
                  }))
                }
                required
              />
            </label>

            <div className="modal-actions" style={{ marginTop: "1rem", display: "flex", justifyContent: "space-between" }}>
              <button type="button" onClick={() => setStep(1)}>
                Voltar
              </button>
              <button type="button" className="btn-primary" onClick={() => void createContractAndLoad()} disabled={loading}>
                Criar contrato e carregar cláusulas
              </button>
            </div>
          </div>
        )}

        {step === 3 && (
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
              <p className="muted-text" style={{ margin: 0 }}>
                Para cada cláusula: ative/desative, escolha versão (padrão ou variação) e edite snapshot (título/texto) sem alterar o modelo.
              </p>
              <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                <button
                  type="button"
                  onClick={() => contractId && navigate(`/contratos/${contractId}/editor?step=2`)}
                  disabled={!contractId}
                >
                  Dados do contrato
                </button>
                <button type="button" className="btn-primary" onClick={() => setStep(4)} disabled={!contractId}>
                  Preview e finalização
                </button>
              </div>
            </div>

            {clausesLoading ? <Loader /> : null}
            {!clausesLoading && clauses.length === 0 ? <p className="muted-text">Nenhuma cláusula disponível.</p> : null}

            {!clausesLoading && clauses.length > 0 ? (
              <div className="clause-list" style={{ marginTop: 16 }}>
                {clauses
                  .slice()
                  .sort((a, b) => {
                    const ao = a.cclUtilizar ? a.cclOrdemFinal : a.cclOrdemBase;
                    const bo = b.cclUtilizar ? b.cclOrdemFinal : b.cclOrdemBase;
                    return ao - bo;
                  })
                  .map((c, idx) => {
                    const isExpanded = expandedClauseId === c.cclId;
                    const selectedCmvId = c.cclCmvId ?? null;

                    return (
                      <div
                        key={c.cclId}
                        className={`clause-card ${!c.cclAtivo || !c.cclUtilizar ? "clause-card--inactive" : ""}`}
                      >
                        <div className="clause-card-top" style={{ display: "flex", gap: 10, alignItems: "center" }}>
                          <span className="clause-order-badge" aria-hidden>
                            {c.cclUtilizar ? c.cclOrdemFinal : "-"}
                          </span>

                          <label className="checkbox-inline" style={{ margin: 0 }}>
                            <input type="checkbox" checked={c.cclUtilizar} onChange={(e) => void onToggleUtilizar(c, e.target.checked)} />
                            Usar
                          </label>

                          <div style={{ flex: 1 }}>
                            <div style={{ fontWeight: 700 }}>{c.cclTitulo}</div>
                            <div className="muted-text" style={{ fontSize: 12, marginTop: 4 }}>
                              Versão
                              <select
                                value={selectedCmvId ?? ""}
                                onChange={(e) => {
                                  const v = e.target.value ? Number(e.target.value) : null;
                                  void onSelectVersion(c, v);
                                }}
                                style={{ marginTop: 6 }}
                              >
                                <option value="">Padrão</option>
                                {(c.variacoes ?? []).filter((v) => v.cmvAtivo).map((v) => (
                                  <option key={v.cmvId} value={v.cmvId}>
                                    {v.cmvTitulo ?? v.cmvNome ?? `Variação #${v.cmvId}`}
                                  </option>
                                ))}
                              </select>
                            </div>
                          </div>

                          <div className="actions" style={{ display: "flex", gap: 8 }}>
                            <ActionIconButton icon="edit" label={isExpanded ? "Fechar" : "Editar"} onClick={() => (isExpanded ? setExpandedClauseId(null) : openClauseEdit(c))} />
                          </div>
                        </div>

                        {isExpanded && (
                          <div className="clause-card-body" style={{ marginTop: 12 }}>
                            <div className="form-vertical">
                              <label>
                                Título
                                <input value={clauseDraft?.cclTitulo ?? ""} onChange={(e) => setClauseDraft((d) => (d ? { ...d, cclTitulo: e.target.value } : d))} required />
                              </label>
                              <label>
                                Texto (placeholders suportados)
                                <textarea value={clauseDraft?.cclTexto ?? ""} onChange={(e) => setClauseDraft((d) => (d ? { ...d, cclTexto: e.target.value } : d))} required rows={6} />
                              </label>
                            </div>

                            <div style={{ display: "flex", justifyContent: "space-between", marginTop: 10, gap: 10 }}>
                              <button type="button" className="btn-primary" onClick={() => void saveClauseEdits(c.cclId)} disabled={savingClauseId === c.cclId}>
                                Salvar
                              </button>
                              <button type="button" onClick={() => openSaveAsVariation(c.cclId)}>
                                Salvar como variação
                              </button>
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
              </div>
            ) : null}
          </div>
        )}

        {step === 4 && (
          <div>
            <p className="muted-text" style={{ marginTop: 0 }}>
              Preview HTML, geração de PDF e link público refletem os dados e cláusulas atuais. Após alterar dados ou cláusulas, gere o HTML ou o PDF de novo.
            </p>
            <div className="modal-actions" style={{ display: "flex", flexWrap: "wrap", gap: 10, justifyContent: "space-between" }}>
              <button type="button" onClick={() => setStep(3)}>
                Voltar para cláusulas
              </button>
              <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                <button
                  type="button"
                  className="btn-primary"
                  onClick={() => contractId && navigate(`/contratos/${contractId}/editor?step=2`)}
                >
                  Editar dados do contrato
                </button>
                <button type="button" onClick={() => contractId && navigate(`/contratos/${contractId}/editor`)}>
                  Ir ao editor de cláusulas
                </button>
              </div>
            </div>

            {contractId ? <ContratoPreviewPanel contratoId={contractId} tokenPublico={tokenPublico} /> : null}
          </div>
        )}
      </section>

      <Modal isOpen={isVarModalOpen} title="Salvar como variação" onClose={() => setIsVarModalOpen(false)}>
        <form
          className="form-vertical"
          onSubmit={(e) => {
            e.preventDefault();
            void saveAsVariation();
          }}
        >
          <label>
            Nome da variação (opcional)
            <input value={varNameDraft} onChange={(e) => setVarNameDraft(e.target.value)} />
          </label>
          <div className="modal-actions">
            <button type="button" onClick={() => setIsVarModalOpen(false)}>
              Cancelar
            </button>
            <button type="submit" className="btn-primary" disabled={savingAsVar}>
              {savingAsVar ? "Salvando..." : "Salvar variação"}
            </button>
          </div>
        </form>
      </Modal>
    </Layout>
  );
};

export default ContratoNovoPage;

