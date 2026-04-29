import React, { useEffect, useMemo, useState } from "react";
import { useLocation, useParams } from "react-router-dom";
import Layout from "../../components/Layout";
import Loader from "../../components/Loader";
import ActionIconButton from "../../components/ActionIconButton";
import Modal from "../../components/Modal";
import { useAuth } from "../../contexts/AuthContext";
import ContratoPreviewPanel from "../../components/contratos/ContratoPreviewPanel";

import { ContratoClausula, ContratoItem } from "../../components/contratos/wizardTypes";

type Step = 2 | 3 | 4;

function computeStepFromLocationSearch(search: string): Step {
  const raw = new URLSearchParams(search).get("step");
  if (!raw) return 3;
  const r = raw.trim().toLowerCase();
  if (r === "2" || r === "dados" || r === "cadastro") return 2;
  if (r === "4" || r === "finalizacao" || r === "preview") return 4;
  return 3;
}

const ContratoEditorPage: React.FC = () => {
  const { api } = useAuth();
  const location = useLocation();
  const params = useParams<{ ctrId: string }>();
  const ctrId = params.ctrId ? Number(params.ctrId) : null;

  const [loading, setLoading] = useState(true);
  const [step, setStep] = useState<Step>(() => computeStepFromLocationSearch(location.search));

  const [contrato, setContrato] = useState<ContratoItem | null>(null);
  const [clauses, setClauses] = useState<ContratoClausula[]>([]);
  const [clausesLoading, setClausesLoading] = useState(false);

  const [dadosDraft, setDadosDraft] = useState({
    ctrNome: "",
    ctrRazaoSocial: "",
    ctrCnpj: "",
    ctrEndereco: "",
    ctrResponsavelNome: "",
    ctrResponsavelCpf: "",
    ctrObjetoContrato: "",
    ctrValorContrato: "" as number | "",
    ctrDataInicio: "",
    ctrPrazoConclusao: "",
    ctrDiasPagamento: "" as number | "",
    ctrDiasAntecedenciaRescisao: "" as number | "",
    ctrValorManutencao: "" as number | "",
    ctrHorasMelhoriasMensais: "" as number | "",
  });

  const [expandedClauseId, setExpandedClauseId] = useState<number | null>(null);
  const [clauseDraft, setClauseDraft] = useState<{ cclTitulo: string; cclTexto: string } | null>(null);
  const [savingClauseId, setSavingClauseId] = useState<number | null>(null);

  const [savingAsVar, setSavingAsVar] = useState(false);
  const [varNameDraft, setVarNameDraft] = useState("");
  const [isVarModalOpen, setIsVarModalOpen] = useState(false);
  const [varForClauseId, setVarForClauseId] = useState<number | null>(null);

  const loadContrato = async () => {
    if (!ctrId) return;
    setLoading(true);
    try {
      const res = await api.get<ContratoItem>(`/contratos/${ctrId}`);
      setContrato(res.data);
      setDadosDraft({
        ctrNome: res.data.ctrNome ?? "",
        ctrRazaoSocial: res.data.ctrRazaoSocial ?? "",
        ctrCnpj: res.data.ctrCnpj ?? "",
        ctrEndereco: res.data.ctrEndereco ?? "",
        ctrResponsavelNome: res.data.ctrResponsavelNome ?? "",
        ctrResponsavelCpf: res.data.ctrResponsavelCpf ?? "",
        ctrObjetoContrato: res.data.ctrObjetoContrato ?? "",
        ctrValorContrato: res.data.ctrValorContrato ?? "",
        ctrDataInicio: res.data.ctrDataInicio ?? "",
        ctrPrazoConclusao: res.data.ctrPrazoConclusao ?? "",
        ctrDiasPagamento: res.data.ctrDiasPagamento ?? "",
        ctrDiasAntecedenciaRescisao: res.data.ctrDiasAntecedenciaRescisao ?? "",
        ctrValorManutencao: res.data.ctrValorManutencao ?? "",
        ctrHorasMelhoriasMensais: res.data.ctrHorasMelhoriasMensais ?? "",
      });

      setClausesLoading(true);
      const clausesRes = await api.get<ContratoClausula[]>(`/contratos/${ctrId}/clausulas`);
      setClauses(clausesRes.data ?? []);
    } finally {
      setClausesLoading(false);
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadContrato();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ctrId]);

  useEffect(() => {
    const p = new URLSearchParams(location.search);
    if (!p.has("step")) return;
    setStep(computeStepFromLocationSearch(location.search));
  }, [location.search]);

  const stepTitle = useMemo(() => {
    if (step === 2) return "2) Dados do contrato";
    if (step === 3) return "3) Cláusulas (snapshot)";
    return "4) Finalização";
  }, [step]);

  const saveDados = async () => {
    if (!ctrId) return;
    await api.put<ContratoItem>(`/contratos/${ctrId}`, {
      ctrNome: dadosDraft.ctrNome,
      ctrRazaoSocial: dadosDraft.ctrRazaoSocial,
      ctrCnpj: dadosDraft.ctrCnpj,
      ctrEndereco: dadosDraft.ctrEndereco,
      ctrResponsavelNome: dadosDraft.ctrResponsavelNome,
      ctrResponsavelCpf: dadosDraft.ctrResponsavelCpf,
      ctrObjetoContrato: dadosDraft.ctrObjetoContrato,
      ctrValorContrato: Number(dadosDraft.ctrValorContrato),
      ctrDataInicio: dadosDraft.ctrDataInicio,
      ctrPrazoConclusao: dadosDraft.ctrPrazoConclusao.trim(),
      ctrDiasPagamento: Number(dadosDraft.ctrDiasPagamento),
      ctrDiasAntecedenciaRescisao: Number(dadosDraft.ctrDiasAntecedenciaRescisao),
      ctrValorManutencao: Number(dadosDraft.ctrValorManutencao),
      ctrHorasMelhoriasMensais: Number(dadosDraft.ctrHorasMelhoriasMensais),
    });
    await loadContrato();
    alert("Dados do contrato atualizados.");
  };

  const onToggleUtilizar = async (clause: ContratoClausula, utilizar: boolean) => {
    if (!ctrId) return;
    const res = utilizar
      ? await api.patch<ContratoClausula>(`/contratos/${ctrId}/clausulas/${clause.cclId}/utilizar`)
      : await api.patch<ContratoClausula>(`/contratos/${ctrId}/clausulas/${clause.cclId}/nao-utilizar`);
    setClauses((prev) => prev.map((x) => (x.cclId === clause.cclId ? res.data : x)));
  };

  const onSelectVersion = async (clause: ContratoClausula, cmvId: number | null) => {
    if (!ctrId) return;
    const res = await api.put<ContratoClausula>(`/contratos/${ctrId}/clausulas/${clause.cclId}`, {
      cclCmvId: cmvId,
    });
    setClauses((prev) => prev.map((x) => (x.cclId === clause.cclId ? res.data : x)));
    if (expandedClauseId === clause.cclId) {
      setClauseDraft({ cclTitulo: res.data.cclTitulo, cclTexto: res.data.cclTexto });
    }
  };

  const openClauseEdit = (c: ContratoClausula) => {
    setExpandedClauseId(c.cclId);
    setClauseDraft({ cclTitulo: c.cclTitulo, cclTexto: c.cclTexto });
  };

  const saveClauseEdits = async (clauseId: number) => {
    if (!ctrId || !clauseDraft) return;
    setSavingClauseId(clauseId);
    try {
      const res = await api.put<ContratoClausula>(`/contratos/${ctrId}/clausulas/${clauseId}`, {
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

  const openSaveAsVariation = (clauseId: number) => {
    setVarForClauseId(clauseId);
    setVarNameDraft("");
    setIsVarModalOpen(true);
  };

  const saveAsVariation = async () => {
    if (!ctrId || varForClauseId == null) return;
    setSavingAsVar(true);
    try {
      const res = await api.post<ContratoClausula>(
        `/contratos/${ctrId}/clausulas/${varForClauseId}/salvar-como-variacao`,
        { cmvNome: varNameDraft.trim() ? varNameDraft.trim() : null }
      );
      setClauses((prev) => prev.map((x) => (x.cclId === varForClauseId ? res.data : x)));
      setIsVarModalOpen(false);
    } finally {
      setSavingAsVar(false);
    }
  };

  return (
    <Layout>
      {loading ? <Loader /> : null}

      <section className="surface-card details-card" style={{ marginTop: "1rem" }}>
        <h2 className="section-title section-title--panel">{stepTitle}</h2>

        {step === 2 && (
          <div className="form-vertical">
            <label>
              Nome do contrato
              <input value={dadosDraft.ctrNome} onChange={(e) => setDadosDraft((d) => ({ ...d, ctrNome: e.target.value }))} />
            </label>
            <label>
              Razão social
              <input value={dadosDraft.ctrRazaoSocial} onChange={(e) => setDadosDraft((d) => ({ ...d, ctrRazaoSocial: e.target.value }))} />
            </label>
            <label>
              CNPJ
              <input value={dadosDraft.ctrCnpj} onChange={(e) => setDadosDraft((d) => ({ ...d, ctrCnpj: e.target.value }))} />
            </label>
            <label>
              Endereço
              <input value={dadosDraft.ctrEndereco} onChange={(e) => setDadosDraft((d) => ({ ...d, ctrEndereco: e.target.value }))} />
            </label>
            <label>
              Responsável (nome)
              <input value={dadosDraft.ctrResponsavelNome} onChange={(e) => setDadosDraft((d) => ({ ...d, ctrResponsavelNome: e.target.value }))} />
            </label>
            <label>
              Responsável (CPF)
              <input value={dadosDraft.ctrResponsavelCpf} onChange={(e) => setDadosDraft((d) => ({ ...d, ctrResponsavelCpf: e.target.value }))} />
            </label>
            <label>
              Objeto do contrato
              <textarea rows={4} value={dadosDraft.ctrObjetoContrato} onChange={(e) => setDadosDraft((d) => ({ ...d, ctrObjetoContrato: e.target.value }))} />
            </label>
            <label>
              Valor do contrato
              <input
                type="number"
                step="0.01"
                min="0"
                value={dadosDraft.ctrValorContrato}
                onChange={(e) => setDadosDraft((d) => ({ ...d, ctrValorContrato: e.target.value === "" ? "" : Number(e.target.value) }))}
              />
            </label>
            <label>
              Data de início
              <input type="date" value={dadosDraft.ctrDataInicio} onChange={(e) => setDadosDraft((d) => ({ ...d, ctrDataInicio: e.target.value }))} />
            </label>
            <label>
              Prazo de conclusão (texto para as cláusulas, ex.: 90 dias)
              <input
                value={dadosDraft.ctrPrazoConclusao}
                onChange={(e) => setDadosDraft((d) => ({ ...d, ctrPrazoConclusao: e.target.value }))}
              />
            </label>
            <label>
              Dias para o primeiro pagamento (após a assinatura)
              <input
                type="number"
                min={0}
                max={3660}
                value={dadosDraft.ctrDiasPagamento}
                onChange={(e) =>
                  setDadosDraft((d) => ({
                    ...d,
                    ctrDiasPagamento: e.target.value === "" ? "" : Number(e.target.value),
                  }))
                }
              />
            </label>
            <label>
              Dias de antecedência para rescisão (notice)
              <input
                type="number"
                min={0}
                max={3660}
                value={dadosDraft.ctrDiasAntecedenciaRescisao}
                onChange={(e) =>
                  setDadosDraft((d) => ({
                    ...d,
                    ctrDiasAntecedenciaRescisao: e.target.value === "" ? "" : Number(e.target.value),
                  }))
                }
              />
            </label>
            <label>
              Valor da manutenção (mensal ou conforme modelo)
              <input
                type="number"
                step="0.01"
                min="0"
                value={dadosDraft.ctrValorManutencao}
                onChange={(e) =>
                  setDadosDraft((d) => ({
                    ...d,
                    ctrValorManutencao: e.target.value === "" ? "" : Number(e.target.value),
                  }))
                }
              />
            </label>
            <label>
              Horas de melhorias mensais
              <span className="muted-text" style={{ display: "block", fontWeight: 400, fontSize: "0.9em", marginBottom: 6 }}>
                Macro no texto: <code>{"{{horas_melhorias_mensais}}"}</code>
              </span>
              <input
                type="number"
                min={0}
                max={744}
                step={1}
                value={dadosDraft.ctrHorasMelhoriasMensais}
                onChange={(e) =>
                  setDadosDraft((d) => ({
                    ...d,
                    ctrHorasMelhoriasMensais: e.target.value === "" ? "" : Number(e.target.value),
                  }))
                }
              />
            </label>

            <div className="modal-actions" style={{ marginTop: "1rem", display: "flex", justifyContent: "space-between" }}>
              <button type="button" onClick={() => setStep(3)}>
                Voltar
              </button>
              <button type="button" className="btn-primary" onClick={() => void saveDados()}>
                Salvar dados
              </button>
            </div>
          </div>
        )}

        {step === 3 && (
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
              <p className="muted-text" style={{ margin: 0 }}>
                Ajuste cláusulas do snapshot. Selecionar uma variação atualiza o texto do snapshot; edições posteriores permanecem independentes do modelo.
              </p>
              <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                <button type="button" onClick={() => setStep(2)} disabled={!ctrId}>
                  Dados do contrato
                </button>
                <button type="button" className="btn-primary" onClick={() => setStep(4)} disabled={!ctrId}>
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
                                Texto
                                <textarea value={clauseDraft?.cclTexto ?? ""} onChange={(e) => setClauseDraft((d) => (d ? { ...d, cclTexto: e.target.value } : d))} rows={6} required />
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
                <button type="button" className="btn-primary" onClick={() => setStep(2)}>
                  Editar dados do contrato
                </button>
              </div>
            </div>

            {ctrId && (
              <ContratoPreviewPanel contratoId={ctrId} tokenPublico={contrato?.ctrTokenPublico} />
            )}
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

export default ContratoEditorPage;

