import React, { useEffect, useMemo, useState } from "react";
import Layout from "../../components/Layout";
import Loader from "../../components/Loader";
import Modal from "../../components/Modal";
import ActionIconButton from "../../components/ActionIconButton";
import ListingToolbar from "../../components/ListingToolbar";
import ListingTableCard from "../../components/ListingTableCard";
import { DataTable } from "../../components/DataTable";
import PaginationBar from "../../components/PaginationBar";
import { useAuth } from "../../contexts/AuthContext";
import ConfirmDialog from "../../components/ConfirmDialog";

import {
  ContratoModeloClausulaItem,
  ContratoModeloClausulaVariacaoItem,
  ContratoModeloItem,
} from "../../components/contratos/types";

interface ContratoModeloListResponse {
  items: ContratoModeloItem[];
  total: number;
  page: number;
  page_size: number;
}

interface VariacaoListResponse {
  items: ContratoModeloClausulaVariacaoItem[];
}

const ContratosCadastrosPage: React.FC = () => {
  const { api } = useAuth();

  const [loading, setLoading] = useState(false);
  const [models, setModels] = useState<ContratoModeloItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const pageSize = 10;

  const [selectedModel, setSelectedModel] = useState<ContratoModeloItem | null>(null);
  const [clauses, setClauses] = useState<ContratoModeloClausulaItem[]>([]);
  const [clausesLoading, setClausesLoading] = useState(false);

  const [expandedClauseId, setExpandedClauseId] = useState<number | null>(null);
  const [clauseDraft, setClauseDraft] = useState<Pick<
    ContratoModeloClausulaItem,
    "cmcTitulo" | "cmcTextoPadrao" | "cmcUtilizarPadrao" | "cmcAtivo"
  > | null>(null);

  const [variacoesPorClausula, setVariacoesPorClausula] = useState<Record<number, ContratoModeloClausulaVariacaoItem[]>>(
    {}
  );
  const [variacoesLoading, setVariacoesLoading] = useState<Record<number, boolean>>({});

  // Model modal
  const [isModelModalOpen, setIsModelModalOpen] = useState(false);
  const [modelModalSelected, setModelModalSelected] = useState<ContratoModeloItem | null>(null);
  const [modelForm, setModelForm] = useState({
    ctmNome: "",
    ctmDescricao: "",
    ctmAtivo: true,
  });

  // Clause in-card create
  const [isNewClauseModalOpen, setIsNewClauseModalOpen] = useState(false);
  const [newClauseForm, setNewClauseForm] = useState({
    cmcTitulo: "",
    cmcTextoPadrao: "",
    cmcUtilizarPadrao: true,
    cmcAtivo: true,
  });

  // Variation modal
  const [isVarModalOpen, setIsVarModalOpen] = useState(false);
  const [variationEditingId, setVariationEditingId] = useState<number | null>(null);
  const [variationCmcId, setVariationCmcId] = useState<number | null>(null);
  const [varForm, setVarForm] = useState({
    cmvNome: "",
    cmvTitulo: "",
    cmvTexto: "",
    cmvAtivo: true,
  });

  // Inactivate confirmation
  const [confirmDialogOpen, setConfirmDialogOpen] = useState(false);
  const [confirmTarget, setConfirmTarget] = useState<{ kind: "modelo" | "clausula" | "variacao"; id: number } | null>(null);

  const activeClauses = useMemo(() => clauses.filter((c) => c.cmcAtivo), [clauses]);
  const inactiveClauses = useMemo(() => clauses.filter((c) => !c.cmcAtivo), [clauses]);

  const [draggingId, setDraggingId] = useState<number | null>(null);

  const loadModels = async () => {
    setLoading(true);
    try {
      const res = await api.get<ContratoModeloListResponse>("/contratos-modelo", {
        params: { page, page_size: pageSize },
      });
      setModels(res.data.items ?? []);
      setTotal(res.data.total ?? 0);
    } finally {
      setLoading(false);
    }
  };

  const loadClauses = async (modelId: number) => {
    setClausesLoading(true);
    try {
      const res = await api.get<ContratoModeloClausulaItem[]>(`/contratos-modelo/${modelId}/clausulas`);
      setClauses(res.data ?? []);
      setExpandedClauseId(null);
      setClauseDraft(null);
      setVariacoesPorClausula({});
    } finally {
      setClausesLoading(false);
    }
  };

  const loadVariacoes = async (cmcId: number) => {
    setVariacoesLoading((prev) => ({ ...prev, [cmcId]: true }));
    try {
      const res = await api.get<VariacaoListResponse>(`/clausulas-modelo/${cmcId}/variacoes`);
      setVariacoesPorClausula((prev) => ({
        ...prev,
        [cmcId]: res.data.items ?? [],
      }));
    } finally {
      setVariacoesLoading((prev) => ({ ...prev, [cmcId]: false }));
    }
  };

  useEffect(() => {
    void loadModels();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page]);

  useEffect(() => {
    if (selectedModel?.ctmId) {
      void loadClauses(selectedModel.ctmId);
    } else {
      setClauses([]);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedModel?.ctmId]);

  const openCreateModel = () => {
    setModelModalSelected(null);
    setModelForm({ ctmNome: "", ctmDescricao: "", ctmAtivo: true });
    setIsModelModalOpen(true);
  };

  const openEditModel = (m: ContratoModeloItem) => {
    setModelModalSelected(m);
    setModelForm({
      ctmNome: m.ctmNome ?? "",
      ctmDescricao: m.ctmDescricao ?? "",
      ctmAtivo: m.ctmAtivo,
    });
    setIsModelModalOpen(true);
  };

  const saveModel = async (e: React.FormEvent) => {
    e.preventDefault();
    const payload = {
      ctmNome: modelForm.ctmNome.trim(),
      ctmDescricao: modelForm.ctmDescricao.trim() ? modelForm.ctmDescricao.trim() : null,
      ctmAtivo: modelForm.ctmAtivo,
    };
    if (!payload.ctmNome) return;
    if (modelModalSelected) {
      await api.put(`/contratos-modelo/${modelModalSelected.ctmId}`, payload);
    } else {
      await api.post("/contratos-modelo", payload);
    }
    setIsModelModalOpen(false);
    await loadModels();
  };

  const openNewClause = () => {
    setNewClauseForm({
      cmcTitulo: "",
      cmcTextoPadrao: "",
      cmcUtilizarPadrao: true,
      cmcAtivo: true,
    });
    setIsNewClauseModalOpen(true);
  };

  const saveNewClause = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedModel) return;
    const payload = {
      cmcTitulo: newClauseForm.cmcTitulo.trim(),
      cmcTextoPadrao: newClauseForm.cmcTextoPadrao,
      cmcUtilizarPadrao: newClauseForm.cmcUtilizarPadrao,
      cmcAtivo: newClauseForm.cmcAtivo,
      cmcOrdem: null,
    };
    await api.post(`/contratos-modelo/${selectedModel.ctmId}/clausulas`, payload);
    setIsNewClauseModalOpen(false);
    await loadClauses(selectedModel.ctmId);
  };

  const toggleModelActive = (m: ContratoModeloItem) => {
    setConfirmTarget({ kind: "modelo", id: m.ctmId });
    setConfirmDialogOpen(true);
  };

  const runConfirm = async () => {
    if (!confirmTarget) return;
    if (confirmTarget.kind === "modelo") {
      const m = models.find((x) => x.ctmId === confirmTarget.id);
      if (!m) return;
      await api.patch(`/contratos-modelo/${m.ctmId}/${m.ctmAtivo ? "inativar" : "ativar"}`);
    } else if (confirmTarget.kind === "clausula") {
      const c = clauses.find((x) => x.cmcId === confirmTarget.id);
      if (!c) return;
      await api.patch(`/clausulas-modelo/${c.cmcId}/${c.cmcAtivo ? "inativar" : "ativar"}`);
    } else if (confirmTarget.kind === "variacao") {
      const allVars = Object.values(variacoesPorClausula).flat();
      const v = allVars.find((x) => x.cmvId === confirmTarget.id);
      if (!v) return;
      await api.patch(`/variacoes-clausula/${v.cmvId}/${v.cmvAtivo ? "inativar" : "ativar"}`);
    }
    setConfirmDialogOpen(false);
    setConfirmTarget(null);
    if (selectedModel?.ctmId) await loadClauses(selectedModel.ctmId);
  };

  const onExpandClause = async (c: ContratoModeloClausulaItem) => {
    setExpandedClauseId(c.cmcId);
    setClauseDraft({
      cmcTitulo: c.cmcTitulo,
      cmcTextoPadrao: c.cmcTextoPadrao,
      cmcUtilizarPadrao: c.cmcUtilizarPadrao,
      cmcAtivo: c.cmcAtivo,
    });
    if (!variacoesPorClausula[c.cmcId] && !variacoesLoading[c.cmcId]) {
      await loadVariacoes(c.cmcId);
    }
  };

  const saveClauseDraft = async (cmcId: number) => {
    if (!clauseDraft) return;
    await api.put(`/clausulas-modelo/${cmcId}`, {
      cmcTitulo: clauseDraft.cmcTitulo.trim(),
      cmcTextoPadrao: clauseDraft.cmcTextoPadrao,
      cmcUtilizarPadrao: clauseDraft.cmcUtilizarPadrao,
      cmcAtivo: clauseDraft.cmcAtivo,
    });
    if (selectedModel?.ctmId) await loadClauses(selectedModel.ctmId);
  };

  const openCreateVariation = (cmcId: number) => {
    setVariationEditingId(null);
    setVariationCmcId(cmcId);
    setVarForm({ cmvNome: "", cmvTitulo: "", cmvTexto: "", cmvAtivo: true });
    setIsVarModalOpen(true);
  };

  const openEditVariation = (cmcId: number, v: ContratoModeloClausulaVariacaoItem) => {
    setVariationEditingId(v.cmvId);
    setVariationCmcId(cmcId);
    setVarForm({
      cmvNome: v.cmvNome ?? "",
      cmvTitulo: v.cmvTitulo ?? "",
      cmvTexto: v.cmvTexto,
      cmvAtivo: v.cmvAtivo,
    });
    setIsVarModalOpen(true);
  };

  const saveVariation = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!variationCmcId) return;
    const payload = {
      cmvNome: varForm.cmvNome.trim() ? varForm.cmvNome.trim() : null,
      cmvTitulo: varForm.cmvTitulo.trim() ? varForm.cmvTitulo.trim() : null,
      cmvTexto: varForm.cmvTexto,
      cmvAtivo: varForm.cmvAtivo,
    };
    if (!payload.cmvTexto.trim()) return;
    if (variationEditingId) {
      await api.put(`/variacoes-clausula/${variationEditingId}`, payload);
    } else {
      await api.post(`/clausulas-modelo/${variationCmcId}/variacoes`, payload);
    }
    setIsVarModalOpen(false);
    if (variationCmcId) await loadVariacoes(variationCmcId);
  };

  const dragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const onDropReorder = async (overId: number) => {
    if (!draggingId || !selectedModel) return;
    if (draggingId === overId) return;

    const fromIdx = activeClauses.findIndex((c) => c.cmcId === draggingId);
    const toIdx = activeClauses.findIndex((c) => c.cmcId === overId);
    if (fromIdx < 0 || toIdx < 0) return;

    const newOrder = [...activeClauses];
    const [moved] = newOrder.splice(fromIdx, 1);
    newOrder.splice(toIdx, 0, moved);

    // Atualiza cmcOrdem para todos ativos, evitando empates de ordem.
    for (let idx = 0; idx < newOrder.length; idx++) {
      const c = newOrder[idx];
      // eslint-disable-next-line no-await-in-loop
      await api.patch(`/clausulas-modelo/${c.cmcId}/reordenar`, { cmcOrdem: idx + 1 });
    }
    setDraggingId(null);
    await loadClauses(selectedModel.ctmId);
  };

  return (
    <Layout>
      <ListingToolbar
        actions={
          <button type="button" className="btn-primary" onClick={openCreateModel}>
            Novo modelo de contrato
          </button>
        }
        filters={<p className="muted-text">Modelos base com cláusulas e variações (drag-and-drop na ordem base).</p>}
      />

      {loading ? (
        <Loader />
      ) : (
        <ListingTableCard
          footer={
            <PaginationBar page={page} pageSize={pageSize} total={total} onPageChange={(next) => setPage(next)} />
          }
        >
          <DataTable
            keyField="ctmId"
            data={models}
            columns={[
              { key: "ctmNome", header: "Nome" },
              {
                key: "ctmAtivo",
                header: "Status",
                render: (r) => (
                  <span className={`status-badge ${r.ctmAtivo ? "status-badge--active" : "status-badge--inactive"}`}>
                    {r.ctmAtivo ? "Ativo" : "Inativo"}
                  </span>
                ),
              },
              {
                key: "ctmId",
                header: "Ações",
                render: (r) => (
                  <div className="actions">
                    <ActionIconButton icon="view" label="Abrir" onClick={() => setSelectedModel(r)} />
                    <ActionIconButton icon="edit" label="Editar" onClick={() => openEditModel(r)} />
                    <ActionIconButton
                      icon={r.ctmAtivo ? "deactivate" : "activate"}
                      label={r.ctmAtivo ? "Inativar" : "Ativar"}
                      tone={r.ctmAtivo ? "danger" : "success"}
                      onClick={() => toggleModelActive(r)}
                    />
                  </div>
                ),
              },
            ]}
          />
        </ListingTableCard>
      )}

      <section className="surface-card details-card" style={{ marginTop: "1.25rem" }}>
        <h2 className="section-title section-title--panel">Modelo de contrato</h2>

        {!selectedModel ? (
          <p className="muted-text">Selecione um modelo para gerenciar suas cláusulas e variações.</p>
        ) : (
          <div className="details-grid" style={{ gridTemplateColumns: "1.1fr 0.9fr" }}>
            <div>
              <div className="details-actions" style={{ display: "flex", justifyContent: "space-between", gap: "1rem" }}>
                <div>
                  <strong>{selectedModel.ctmNome}</strong>
                  <div className="muted-text" style={{ marginTop: 6 }}>
                    {selectedModel.ctmDescricao || "Sem descrição"}
                  </div>
                </div>
                <div style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
                  <button type="button" className="btn-primary" onClick={openNewClause}>
                    Nova cláusula
                  </button>
                </div>
              </div>

              {clausesLoading ? (
                <Loader />
              ) : (
                <>
                  <div style={{ marginTop: 16 }}>
                    <h3 className="muted-text" style={{ marginBottom: 10 }}>
                      Cláusulas ativas (ordem base)
                    </h3>
                    {activeClauses.length === 0 ? (
                      <p className="muted-text">Nenhuma cláusula ativa no modelo.</p>
                    ) : (
                      <div className="clause-list">
                        {activeClauses.map((c, idx) => (
                          <div
                            key={c.cmcId}
                            className={`clause-card ${expandedClauseId === c.cmcId ? "is-expanded" : ""}`}
                            draggable
                            onDragStart={() => setDraggingId(c.cmcId)}
                            onDragOver={dragOver}
                            onDrop={() => void onDropReorder(c.cmcId)}
                          >
                            <div className="clause-card-top" style={{ display: "flex", gap: 10, alignItems: "center" }}>
                              <span className="clause-order-badge" aria-hidden>
                                {idx + 1}
                              </span>
                              <ActionIconButton
                                icon="edit"
                                label="Editar e visualizar variações"
                                onClick={() => void onExpandClause(c)}
                              />
                              <div style={{ flex: 1 }}>
                                <div style={{ fontWeight: 700 }}>{c.cmcTitulo}</div>
                                <div className="muted-text" style={{ fontSize: 12, marginTop: 4 }}>
                                  Variáveis: {variacoesLoading[c.cmcId] ? "carregando..." : (variacoesPorClausula[c.cmcId]?.length ?? 0)} variação(ões)
                                </div>
                              </div>
                              <label className="checkbox-inline" style={{ margin: 0 }}>
                                <input
                                  type="checkbox"
                                  checked={c.cmcUtilizarPadrao}
                                  onChange={async (e) => {
                                    await api.put(`/clausulas-modelo/${c.cmcId}`, { cmcUtilizarPadrao: e.target.checked });
                                    await loadClauses(selectedModel.ctmId);
                                  }}
                                />
                                Usar por padrão
                              </label>
                            </div>

                            {expandedClauseId === c.cmcId && clauseDraft && (
                              <div className="clause-card-body" style={{ marginTop: 12 }}>
                                <div className="form-vertical">
                                  <label>
                                    Título
                                    <input
                                      type="text"
                                      value={clauseDraft.cmcTitulo}
                                      onChange={(e) => setClauseDraft((d) => (d ? { ...d, cmcTitulo: e.target.value } : d))}
                                      required
                                    />
                                  </label>
                                  <label>
                                    Texto padrão (pode conter placeholders)
                                    <textarea
                                      rows={6}
                                      value={clauseDraft.cmcTextoPadrao}
                                      onChange={(e) =>
                                        setClauseDraft((d) => (d ? { ...d, cmcTextoPadrao: e.target.value } : d))
                                      }
                                      required
                                    />
                                  </label>
                                  <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
                                    <button
                                      type="button"
                                      className="btn-primary"
                                      onClick={() => void saveClauseDraft(c.cmcId)}
                                    >
                                      Salvar
                                    </button>
                                  </div>
                                </div>

                                <hr style={{ margin: "14px 0" }} />

                                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                                  <h4 style={{ margin: 0 }}>Variações</h4>
                                  <button type="button" className="btn-primary" onClick={() => openCreateVariation(c.cmcId)}>
                                    Nova variação
                                  </button>
                                </div>

                                {variacoesLoading[c.cmcId] ? (
                                  <Loader />
                                ) : (
                                  <div style={{ marginTop: 12 }}>
                                    {(variacoesPorClausula[c.cmcId] ?? []).length === 0 ? (
                                      <p className="muted-text">Nenhuma variação criada ainda.</p>
                                    ) : (
                                      <div className="variation-list">
                                        {(variacoesPorClausula[c.cmcId] ?? []).map((v) => (
                                          <div key={v.cmvId} className="variation-row">
                                            <div style={{ flex: 1 }}>
                                              <div style={{ fontWeight: 700 }}>
                                                {v.cmvTitulo || v.cmvNome || `Variação #${v.cmvId}`}
                                              </div>
                                              <div className="muted-text" style={{ fontSize: 12, marginTop: 4 }}>
                                                {v.cmvAtivo ? "Ativa" : "Inativa"}
                                              </div>
                                            </div>
                                            <div className="actions" style={{ display: "flex", gap: 8 }}>
                                              <ActionIconButton
                                                icon="edit"
                                                label="Editar variação"
                                                onClick={() => openEditVariation(c.cmcId, v)}
                                              />
                                              <ActionIconButton
                                                icon={v.cmvAtivo ? "deactivate" : "activate"}
                                                label={v.cmvAtivo ? "Inativar" : "Ativar"}
                                                tone={v.cmvAtivo ? "danger" : "success"}
                                                onClick={() => {
                                                  setConfirmTarget({ kind: "variacao", id: v.cmvId });
                                                  setConfirmDialogOpen(true);
                                                }}
                                              />
                                            </div>
                                          </div>
                                        ))}
                                      </div>
                                    )}
                                  </div>
                                )}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {inactiveClauses.length > 0 && (
                    <div style={{ marginTop: 24 }}>
                      <h3 className="muted-text" style={{ marginBottom: 10 }}>
                        Cláusulas inativas
                      </h3>
                      <div className="inactive-clauses">
                        {inactiveClauses.map((c) => (
                          <div key={c.cmcId} className="clause-card clause-card--inactive">
                            <div className="clause-card-top" style={{ display: "flex", gap: 10, alignItems: "center" }}>
                              <span className="clause-order-badge" aria-hidden>
                                {c.cmcOrdem}
                              </span>
                              <ActionIconButton icon="edit" label="Editar" onClick={() => void onExpandClause(c)} />
                              <div style={{ flex: 1 }}>
                                <div style={{ fontWeight: 700 }}>{c.cmcTitulo}</div>
                                <div className="muted-text" style={{ fontSize: 12, marginTop: 4 }}>
                                  Inativa
                                </div>
                              </div>
                              <label className="checkbox-inline" style={{ margin: 0 }}>
                                <input
                                  type="checkbox"
                                  checked={c.cmcUtilizarPadrao}
                                  onChange={async (e) => {
                                    await api.put(`/clausulas-modelo/${c.cmcId}`, { cmcUtilizarPadrao: e.target.checked });
                                    await loadClauses(selectedModel.ctmId);
                                  }}
                                />
                                Usar por padrão
                              </label>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>

            <aside>
              <div className="muted-text" style={{ marginBottom: 10 }}>
                {
                  "Dica: placeholders do texto suportam `{{razao_social}}`, `{{cnpj}}`, `{{endereco}}` etc."
                }
              </div>
              <div className="surface-card details-card">
                <h3 style={{ marginTop: 0 }}>Estado do modelo</h3>
                <div className="info-grid" style={{ gridTemplateColumns: "1fr", gap: 10 }}>
                  <div className="info-item">
                    <span className="info-label">Ativo</span>
                    <span>{selectedModel.ctmAtivo ? "Sim" : "Não"}</span>
                  </div>
                  <div className="info-item">
                    <span className="info-label">Cláusulas</span>
                    <span>
                      {activeClauses.length} ativas / {inactiveClauses.length} inativas
                    </span>
                  </div>
                </div>
              </div>
            </aside>
          </div>
        )}
      </section>

      <Modal isOpen={isModelModalOpen} title={modelModalSelected ? "Editar modelo de contrato" : "Novo modelo de contrato"} onClose={() => setIsModelModalOpen(false)}>
        <form className="form-vertical" onSubmit={saveModel}>
          <label>
            Nome
            <input
              type="text"
              value={modelForm.ctmNome}
              onChange={(e) => setModelForm((f) => ({ ...f, ctmNome: e.target.value }))}
              required
            />
          </label>
          <label>
            Descrição
            <textarea
              rows={3}
              value={modelForm.ctmDescricao}
              onChange={(e) => setModelForm((f) => ({ ...f, ctmDescricao: e.target.value }))}
            />
          </label>
          <label className="checkbox-inline">
            <input type="checkbox" checked={modelForm.ctmAtivo} onChange={(e) => setModelForm((f) => ({ ...f, ctmAtivo: e.target.checked }))} />
            Ativo
          </label>
          <div className="modal-actions">
            <button type="button" onClick={() => setIsModelModalOpen(false)}>
              Cancelar
            </button>
            <button type="submit" className="btn-primary">
              Salvar
            </button>
          </div>
        </form>
      </Modal>

      <Modal isOpen={isNewClauseModalOpen} title="Nova cláusula" onClose={() => setIsNewClauseModalOpen(false)}>
        <form className="form-vertical" onSubmit={saveNewClause}>
          <label>
            Título
            <input type="text" value={newClauseForm.cmcTitulo} onChange={(e) => setNewClauseForm((f) => ({ ...f, cmcTitulo: e.target.value }))} required />
          </label>
          <label>
            Texto padrão (placeholders suportados)
            <textarea rows={6} value={newClauseForm.cmcTextoPadrao} onChange={(e) => setNewClauseForm((f) => ({ ...f, cmcTextoPadrao: e.target.value }))} required />
          </label>
          <label className="checkbox-inline">
            <input type="checkbox" checked={newClauseForm.cmcUtilizarPadrao} onChange={(e) => setNewClauseForm((f) => ({ ...f, cmcUtilizarPadrao: e.target.checked }))} />
            Usar por padrão
          </label>
          <label className="checkbox-inline">
            <input type="checkbox" checked={newClauseForm.cmcAtivo} onChange={(e) => setNewClauseForm((f) => ({ ...f, cmcAtivo: e.target.checked }))} />
            Ativa
          </label>
          <div className="modal-actions">
            <button type="button" onClick={() => setIsNewClauseModalOpen(false)}>
              Cancelar
            </button>
            <button type="submit" className="btn-primary">
              Criar
            </button>
          </div>
        </form>
      </Modal>

      <Modal isOpen={isVarModalOpen} title={variationEditingId ? "Editar variação" : "Nova variação"} onClose={() => setIsVarModalOpen(false)}>
        <form className="form-vertical" onSubmit={saveVariation}>
          <label>
            Nome (opcional)
            <input type="text" value={varForm.cmvNome} onChange={(e) => setVarForm((f) => ({ ...f, cmvNome: e.target.value }))} />
          </label>
          <label>
            Título (opcional)
            <input type="text" value={varForm.cmvTitulo} onChange={(e) => setVarForm((f) => ({ ...f, cmvTitulo: e.target.value }))} />
          </label>
          <label>
            Texto
            <textarea rows={6} value={varForm.cmvTexto} onChange={(e) => setVarForm((f) => ({ ...f, cmvTexto: e.target.value }))} required />
          </label>
          <label className="checkbox-inline">
            <input type="checkbox" checked={varForm.cmvAtivo} onChange={(e) => setVarForm((f) => ({ ...f, cmvAtivo: e.target.checked }))} />
            Ativa
          </label>
          <div className="modal-actions">
            <button type="button" onClick={() => setIsVarModalOpen(false)}>
              Cancelar
            </button>
            <button type="submit" className="btn-primary">
              Salvar
            </button>
          </div>
        </form>
      </Modal>

      <ConfirmDialog
        isOpen={confirmDialogOpen}
        title="Confirmação"
        message="Deseja alternar o status deste item?"
        onCancel={() => {
          setConfirmDialogOpen(false);
          setConfirmTarget(null);
        }}
        onConfirm={() => void runConfirm()}
      />
    </Layout>
  );
};

export default ContratosCadastrosPage;

