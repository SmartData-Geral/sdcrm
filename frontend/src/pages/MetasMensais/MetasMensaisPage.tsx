import React, { useCallback, useEffect, useMemo, useState } from "react";
import Layout from "../../components/Layout";
import { DataTable } from "../../components/DataTable";
import Loader from "../../components/Loader";
import ConfirmDialog from "../../components/ConfirmDialog";
import Modal from "../../components/Modal";
import ActionIconButton from "../../components/ActionIconButton";
import ListingToolbar from "../../components/ListingToolbar";
import ListingTableCard from "../../components/ListingTableCard";
import { useAuth } from "../../contexts/AuthContext";

interface MetaRow {
  cmmId: number;
  cmmMesReferencia: string;
  cmmQtdRecebimento: number;
  cmmTaxaConversao: number | string;
  cmmMrrMedio: number | string;
  cmmQtdFechamento: number;
  cmmMrrIncremental: number | string;
  cmmValorProjeto: number | string;
}

interface ResumoResponse {
  items: MetaRow[];
  ano: number;
}

function num(v: number | string): number {
  if (typeof v === "number") return v;
  return Number.parseFloat(v);
}

function truncFechamentos(qRec: number, taxa: number): number {
  return Math.trunc(qRec * taxa);
}

function formatCurrencyBRL(value: number) {
  return value.toLocaleString("pt-BR", { style: "currency", currency: "BRL", minimumFractionDigits: 2 });
}

function formatPercentRate(rate: number) {
  return `${(rate * 100).toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}%`;
}

function formatPeriodoPt(isoDate: string) {
  const [y, m] = isoDate.slice(0, 10).split("-");
  if (!y || !m) return isoDate;
  return `01/${m}/${y}`;
}

function isoPrimeiroDoMes(monthValue: string): string {
  return `${monthValue}-01`;
}

function monthInputFromIso(isoDate: string): string {
  return isoDate.slice(0, 7);
}

function mesLabelChart(isoDate: string) {
  const [y, m] = isoDate.slice(0, 10).split("-");
  if (!y || !m) return "";
  const shortY = y.slice(2);
  return `${m}/${shortY}`;
}

function fillFormFromRow(row: MetaRow) {
  return {
    formMes: monthInputFromIso(row.cmmMesReferencia),
    formQtdRec: String(row.cmmQtdRecebimento),
    formTaxa: String(num(row.cmmTaxaConversao)),
    formMrr: String(num(row.cmmMrrMedio)),
    formProjeto: String(num(row.cmmValorProjeto ?? 0)),
  };
}

type ModalMode = "create" | "edit" | "duplicate";

const MetasMensaisPage: React.FC = () => {
  const { api } = useAuth();
  const anoAtual = new Date().getFullYear();
  const [ano, setAno] = useState(anoAtual);
  const [items, setItems] = useState<MetaRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<MetaRow | null>(null);
  const [modalMode, setModalMode] = useState<ModalMode>("create");
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isDeleteOpen, setIsDeleteOpen] = useState(false);
  const [formMes, setFormMes] = useState(`${anoAtual}-01`);
  const [formQtdRec, setFormQtdRec] = useState("12");
  const [formTaxa, setFormTaxa] = useState("0.30");
  const [formMrr, setFormMrr] = useState("3000");
  const [formProjeto, setFormProjeto] = useState("0");

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.get<ResumoResponse>("/crm/metas-mensais/resumo", { params: { ano } });
      setItems(res.data.items ?? []);
    } catch {
      setError("Não foi possível carregar as metas. Verifique sua conexão e tente novamente.");
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, [api, ano]);

  useEffect(() => {
    void load();
  }, [load]);

  const preview = useMemo(() => {
    const q = Number.parseInt(formQtdRec, 10) || 0;
    const taxa = Number.parseFloat(formTaxa.replace(",", ".")) || 0;
    const mrr = Number.parseFloat(formMrr.replace(",", ".")) || 0;
    const qfe = truncFechamentos(q, taxa);
    const mir = qfe * mrr;
    return { qfe, mir };
  }, [formQtdRec, formTaxa, formMrr]);

  const maxIncremental = useMemo(
    () => (items.length ? Math.max(...items.map((row) => num(row.cmmMrrIncremental))) : 0),
    [items]
  );

  const closeModal = () => {
    setIsModalOpen(false);
    setModalMode("create");
    setSelected(null);
  };

  const openCreate = () => {
    setModalMode("create");
    setSelected(null);
    setFormMes(`${ano}-01`);
    setFormQtdRec("12");
    setFormTaxa("0.30");
    setFormMrr("3000");
    setFormProjeto("0");
    setIsModalOpen(true);
  };

  const openEdit = (row: MetaRow) => {
    setModalMode("edit");
    setSelected(row);
    const f = fillFormFromRow(row);
    setFormMes(f.formMes);
    setFormQtdRec(f.formQtdRec);
    setFormTaxa(f.formTaxa);
    setFormMrr(f.formMrr);
    setFormProjeto(f.formProjeto);
    setIsModalOpen(true);
  };

  const openDuplicate = (row: MetaRow) => {
    setModalMode("duplicate");
    setSelected(null);
    const f = fillFormFromRow(row);
    setFormMes(f.formMes);
    setFormQtdRec(f.formQtdRec);
    setFormTaxa(f.formTaxa);
    setFormMrr(f.formMrr);
    setFormProjeto(f.formProjeto);
    setIsModalOpen(true);
  };

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    const qRec = Number.parseInt(formQtdRec, 10);
    const taxa = Number.parseFloat(String(formTaxa).replace(",", "."));
    const mrr = Number.parseFloat(String(formMrr).replace(",", "."));
    const projeto = Number.parseFloat(String(formProjeto || "0").replace(",", "."));
    if (Number.isNaN(qRec) || qRec < 0) return;
    if (Number.isNaN(taxa) || taxa < 0 || taxa > 1) return;
    if (Number.isNaN(mrr) || mrr < 0) return;
    if (Number.isNaN(projeto) || projeto < 0) return;

    const bodyBase = {
      cmmMesReferencia: isoPrimeiroDoMes(formMes),
      cmmQtdRecebimento: qRec,
      cmmTaxaConversao: taxa,
      cmmMrrMedio: mrr,
      cmmValorProjeto: projeto,
    };

    try {
      if (modalMode === "edit" && selected) {
        await api.put(`/crm/metas-mensais/${selected.cmmId}`, bodyBase);
      } else {
        await api.post("/crm/metas-mensais", bodyBase);
      }
      closeModal();
      await load();
    } catch (err: unknown) {
      const msg =
        typeof err === "object" &&
        err !== null &&
        "response" in err &&
        typeof (err as { response?: { data?: { detail?: unknown } } }).response?.data?.detail === "string"
          ? String((err as { response: { data: { detail: string } } }).response.data.detail)
          : "Não foi possível salvar. Verifique se já existe meta para o mês.";
      window.alert(msg);
    }
  };

  const confirmDelete = (row: MetaRow) => {
    setSelected(row);
    setIsDeleteOpen(true);
  };

  const doDelete = async () => {
    if (!selected) return;
    try {
      await api.delete(`/crm/metas-mensais/${selected.cmmId}`);
      setIsDeleteOpen(false);
      setSelected(null);
      await load();
    } catch {
      window.alert("Não foi possível excluir a meta.");
    }
  };

  const anoOptions = useMemo(() => {
    const out: number[] = [];
    for (let y = anoAtual - 3; y <= anoAtual + 7; y += 1) out.push(y);
    return out;
  }, [anoAtual]);

  return (
    <Layout>
      <ListingToolbar
        actions={
          <button type="button" className="btn-primary" onClick={openCreate}>
            Nova meta
          </button>
        }
        filters={
          <label style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <span>Ano</span>
            <select value={ano} onChange={(e) => setAno(Number(e.target.value))}>
              {anoOptions.map((y) => (
                <option key={y} value={y}>
                  {y}
                </option>
              ))}
            </select>
          </label>
        }
      />

      {error && (
        <section className="surface-card" style={{ marginBottom: "0.85rem" }}>
          <p className="error-text">{error}</p>
        </section>
      )}

      <section className="dashboard-charts-grid" style={{ marginBottom: "0.85rem" }}>
        <article className="surface-card chart-card" style={{ gridColumn: "1 / -1" }}>
          <div className="chart-card-header">
            <h2>MRR incremental (meta) por mês — {ano}</h2>
          </div>
          <div className="chart-card-body">
            {items.length === 0 ? (
              <p className="empty-state-text">Nenhuma meta cadastrada para este ano.</p>
            ) : (
              <div className="chart chart--bars-vertical">
                {items.map((item) => {
                  const valor = num(item.cmmMrrIncremental);
                  const basePercent = maxIncremental > 0 ? (valor / maxIncremental) * 100 : 0;
                  const heightPercent = basePercent > 0 ? 20 + basePercent * 0.75 : 0;
                  return (
                    <div key={item.cmmId} className="chart-bar-vertical">
                      <div className="chart-bar-vertical-bar" style={{ height: `${heightPercent}%` }}>
                        <span className="chart-bar-vertical-value">{formatCurrencyBRL(valor)}</span>
                      </div>
                      <span className="chart-bar-vertical-label">{mesLabelChart(item.cmmMesReferencia)}</span>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </article>
      </section>

      {loading ? (
        <Loader />
      ) : (
        <ListingTableCard>
          <DataTable
            keyField="cmmId"
            data={items}
            columns={[
              {
                key: "cmmMesReferencia",
                header: "Período",
                render: (r) => formatPeriodoPt(r.cmmMesReferencia),
              },
              { key: "cmmQtdRecebimento", header: "Qtd. recebimento" },
              {
                key: "cmmTaxaConversao",
                header: "Taxa conv.",
                render: (r) => formatPercentRate(num(r.cmmTaxaConversao)),
              },
              {
                key: "cmmMrrMedio",
                header: "MRR médio",
                render: (r) => formatCurrencyBRL(num(r.cmmMrrMedio)),
              },
              { key: "cmmQtdFechamento", header: "Qtd. fechamento" },
              {
                key: "cmmMrrIncremental",
                header: "MRR incremental",
                render: (r) => formatCurrencyBRL(num(r.cmmMrrIncremental)),
              },
              {
                key: "cmmValorProjeto",
                header: "Valor de projeto",
                render: (r) => formatCurrencyBRL(num(r.cmmValorProjeto ?? 0)),
              },
              {
                key: "cmmId",
                header: "Ações",
                render: (r) => (
                  <div className="actions">
                    <ActionIconButton icon="edit" label="Editar" onClick={() => openEdit(r)} />
                    <ActionIconButton icon="duplicate" label="Duplicar" onClick={() => openDuplicate(r)} />
                    <ActionIconButton icon="delete" label="Excluir" tone="danger" onClick={() => confirmDelete(r)} />
                  </div>
                ),
              },
            ]}
          />
        </ListingTableCard>
      )}

      <Modal
        isOpen={isModalOpen}
        title={
          modalMode === "edit"
            ? "Editar meta mensal"
            : modalMode === "duplicate"
              ? "Duplicar meta mensal"
              : "Nova meta mensal"
        }
        onClose={closeModal}
      >
        <form className="form-vertical" onSubmit={save}>
          {modalMode === "duplicate" && (
            <p className="empty-state-text" style={{ marginBottom: "0.75rem", textAlign: "left" }}>
              Dados copiados da meta selecionada. Ajuste o mês ou os valores e salve para criar um novo registro.
            </p>
          )}
          <label>
            Mês de referência
            <input type="month" required value={formMes} onChange={(e) => setFormMes(e.target.value)} />
            <small style={{ display: "block", marginTop: "0.25rem", opacity: 0.75 }}>
              Sempre gravado como o primeiro dia do mês.
            </small>
          </label>
          <label>
            Quantidade de recebimento
            <input
              type="number"
              min={0}
              step={1}
              required
              value={formQtdRec}
              onChange={(e) => setFormQtdRec(e.target.value)}
            />
          </label>
          <label>
            Taxa de conversão (0 a 1)
            <input
              type="text"
              inputMode="decimal"
              placeholder="Ex.: 0,35 ou 0.35"
              required
              value={formTaxa}
              onChange={(e) => setFormTaxa(e.target.value)}
            />
          </label>
          <label>
            MRR médio (R$)
            <input
              type="text"
              inputMode="decimal"
              required
              value={formMrr}
              onChange={(e) => setFormMrr(e.target.value)}
            />
          </label>
          <label>
            Meta de valor de projeto (R$)
            <input
              type="text"
              inputMode="decimal"
              placeholder="Ex.: 20000 ou 20000,00"
              value={formProjeto}
              onChange={(e) => setFormProjeto(e.target.value)}
            />
            <small style={{ display: "block", marginTop: "0.25rem", opacity: 0.75 }}>
              Vendas pontuais fechadas como projeto. Valor informado direto, sem cálculo pelo funil.
            </small>
          </label>
          <div style={{ padding: "0.75rem 1rem", borderRadius: "8px", background: "#f8fafc", border: "1px solid #e2e8f0" }}>
            <strong>Calculado no salvamento:</strong>
            <div className="form-inline" style={{ marginTop: "0.5rem", gap: "1rem" }}>
              <span>Qtd. fechamento: {preview.qfe}</span>
              <span>MRR incremental: {formatCurrencyBRL(preview.mir)}</span>
            </div>
          </div>
          <div className="modal-actions">
            <button type="button" onClick={closeModal}>
              Cancelar
            </button>
            <button type="submit" className="btn-primary">
              Salvar
            </button>
          </div>
        </form>
      </Modal>

      <ConfirmDialog
        isOpen={isDeleteOpen}
        message={`Excluir a meta de ${selected ? formatPeriodoPt(selected.cmmMesReferencia) : ""}?`}
        onCancel={() => setIsDeleteOpen(false)}
        onConfirm={doDelete}
      />
    </Layout>
  );
};

export default MetasMensaisPage;
