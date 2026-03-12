import React, { useEffect, useState } from "react";
import Layout from "../../components/Layout";
import { DataTable } from "../../components/DataTable";
import Loader from "../../components/Loader";
import ConfirmDialog from "../../components/ConfirmDialog";
import Modal from "../../components/Modal";
import ActionIconButton from "../../components/ActionIconButton";
import ListingToolbar from "../../components/ListingToolbar";
import ListingTableCard from "../../components/ListingTableCard";
import PaginationBar from "../../components/PaginationBar";
import { useAuth } from "../../contexts/AuthContext";

interface EtapaKanbanItem {
  etkId: number;
  etkNome: string;
  etkOrdem: number;
  etkPipeline: string;
  etkCor: string | null;
  etkAtivo: boolean;
}

interface ListResponse {
  items: EtapaKanbanItem[];
  total: number;
  page: number;
  page_size: number;
}

const EtapasKanbanPage: React.FC = () => {
  const { api } = useAuth();
  const [items, setItems] = useState<EtapaKanbanItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(10);
  const [total, setTotal] = useState(0);
  const [nomeFiltro, setNomeFiltro] = useState("");
  const [statusFiltro, setStatusFiltro] = useState<"todos" | "ativos" | "inativos">("ativos");
  const [selected, setSelected] = useState<EtapaKanbanItem | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isInativarOpen, setIsInativarOpen] = useState(false);
  const [form, setForm] = useState({ etkNome: "", etkOrdem: 0, etkPipeline: "default", etkCor: "" });

  const load = async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { page, page_size: pageSize, status: statusFiltro };
      if (nomeFiltro.trim()) params.nome = nomeFiltro.trim();
      const res = await api.get<ListResponse>("/etapas-kanban", { params });
      setItems(res.data.items);
      setTotal(res.data.total);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, [page, nomeFiltro, statusFiltro]);

  const openCreate = () => {
    setSelected(null);
    setForm({ etkNome: "", etkOrdem: items.length + 1, etkPipeline: "default", etkCor: "" });
    setIsModalOpen(true);
  };

  const openEdit = (row: EtapaKanbanItem) => {
    setSelected(row);
    setForm({
      etkNome: row.etkNome,
      etkOrdem: row.etkOrdem,
      etkPipeline: row.etkPipeline,
      etkCor: row.etkCor ?? "",
    });
    setIsModalOpen(true);
  };

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    const payload = {
      etkNome: form.etkNome,
      etkOrdem: form.etkOrdem,
      etkPipeline: form.etkPipeline || "default",
      etkCor: form.etkCor || null,
    };
    if (selected) {
      await api.put(`/etapas-kanban/${selected.etkId}`, payload);
    } else {
      await api.post("/etapas-kanban", payload);
    }
    setIsModalOpen(false);
    await load();
  };

  const confirmInativar = (row: EtapaKanbanItem) => {
    setSelected(row);
    setIsInativarOpen(true);
  };

  const inativar = async () => {
    if (selected) {
      await api.patch(`/etapas-kanban/${selected.etkId}/inativar`);
      setIsInativarOpen(false);
      await load();
    }
  };

  const ativar = async (row: EtapaKanbanItem) => {
    await api.patch(`/etapas-kanban/${row.etkId}/ativar`);
    await load();
  };

  return (
    <Layout>
      <ListingToolbar
        actions={
          <button type="button" className="btn-primary" onClick={openCreate}>
            Nova etapa
          </button>
        }
        filters={
          <>
            <input
              type="text"
              placeholder="Filtrar por nome"
              value={nomeFiltro}
              onChange={(e) => {
                setPage(1);
                setNomeFiltro(e.target.value);
              }}
            />
            <select
              value={statusFiltro}
              onChange={(e) => {
                setPage(1);
                setStatusFiltro(e.target.value as typeof statusFiltro);
              }}
            >
              <option value="todos">Todos</option>
              <option value="ativos">Ativos</option>
              <option value="inativos">Inativos</option>
            </select>
          </>
        }
      />
      {loading ? (
        <Loader />
      ) : (
        <ListingTableCard
          footer={<PaginationBar page={page} pageSize={pageSize} total={total} onPageChange={(next) => setPage(next)} />}
        >
          <DataTable
            keyField="etkId"
            data={items}
            columns={[
              { key: "etkOrdem", header: "Ordem" },
              { key: "etkNome", header: "Nome" },
              { key: "etkPipeline", header: "Pipeline" },
              {
                key: "etkCor",
                header: "Cor",
                render: (r) =>
                  r.etkCor ? (
                    <span className="color-swatch" style={{ background: r.etkCor }} title={r.etkCor} />
                  ) : (
                    "-"
                  ),
              },
              {
                key: "etkAtivo",
                header: "Status",
                render: (r) => (
                  <span className={`status-badge ${r.etkAtivo ? "status-badge--active" : "status-badge--inactive"}`}>
                    {r.etkAtivo ? "Ativo" : "Inativo"}
                  </span>
                ),
              },
              {
                key: "etkId",
                header: "Ações",
                render: (r) => (
                  <div className="actions">
                    <ActionIconButton icon="edit" label="Editar" onClick={() => openEdit(r)} />
                    {r.etkAtivo ? (
                      <ActionIconButton
                        icon="deactivate"
                        label="Inativar"
                        tone="danger"
                        onClick={() => confirmInativar(r)}
                      />
                    ) : (
                      <ActionIconButton icon="activate" label="Ativar" tone="success" onClick={() => ativar(r)} />
                    )}
                  </div>
                ),
              },
            ]}
          />
        </ListingTableCard>
      )}
      <Modal isOpen={isModalOpen} title={selected ? "Editar etapa" : "Nova etapa"} onClose={() => setIsModalOpen(false)}>
        <form className="form-vertical" onSubmit={save}>
          <label>
            Nome
            <input
              type="text"
              value={form.etkNome}
              onChange={(e) => setForm((f) => ({ ...f, etkNome: e.target.value }))}
              required
            />
          </label>
          <label>
            Ordem
            <input
              type="number"
              min={1}
              value={form.etkOrdem}
              onChange={(e) => setForm((f) => ({ ...f, etkOrdem: Number(e.target.value) || 0 }))}
            />
          </label>
          <label>
            Pipeline
            <input
              type="text"
              value={form.etkPipeline}
              onChange={(e) => setForm((f) => ({ ...f, etkPipeline: e.target.value }))}
            />
          </label>
          <label>
            Cor (hex)
            <input
              type="text"
              placeholder="#000000"
              value={form.etkCor}
              onChange={(e) => setForm((f) => ({ ...f, etkCor: e.target.value }))}
            />
          </label>
          <div className="modal-actions">
            <button type="button" onClick={() => setIsModalOpen(false)}>
              Cancelar
            </button>
            <button type="submit">Salvar</button>
          </div>
        </form>
      </Modal>
      <ConfirmDialog
        isOpen={isInativarOpen}
        message={`Inativar a etapa "${selected?.etkNome}"?`}
        onCancel={() => setIsInativarOpen(false)}
        onConfirm={inativar}
      />
    </Layout>
  );
};

export default EtapasKanbanPage;
