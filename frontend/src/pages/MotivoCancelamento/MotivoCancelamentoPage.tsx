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

interface MotivoCancelamentoItem {
  mcaId: number;
  mcaNome: string;
  mcaAtivo: boolean;
}

interface ListResponse {
  items: MotivoCancelamentoItem[];
  total: number;
  page: number;
  page_size: number;
}

const MotivoCancelamentoPage: React.FC = () => {
  const { api } = useAuth();
  const [items, setItems] = useState<MotivoCancelamentoItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(10);
  const [total, setTotal] = useState(0);
  const [nomeFiltro, setNomeFiltro] = useState("");
  const [statusFiltro, setStatusFiltro] = useState<"todos" | "ativos" | "inativos">("ativos");
  const [selected, setSelected] = useState<MotivoCancelamentoItem | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isInativarOpen, setIsInativarOpen] = useState(false);
  const [form, setForm] = useState({ mcaNome: "" });

  const load = async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { page, page_size: pageSize, status: statusFiltro };
      if (nomeFiltro.trim()) params.nome = nomeFiltro.trim();
      const res = await api.get<ListResponse>("/motivos-cancelamento", { params });
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
    setForm({ mcaNome: "" });
    setIsModalOpen(true);
  };

  const openEdit = (row: MotivoCancelamentoItem) => {
    setSelected(row);
    setForm({ mcaNome: row.mcaNome });
    setIsModalOpen(true);
  };

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    if (selected) {
      await api.put(`/motivos-cancelamento/${selected.mcaId}`, form);
    } else {
      await api.post("/motivos-cancelamento", form);
    }
    setIsModalOpen(false);
    await load();
  };

  const confirmInativar = (row: MotivoCancelamentoItem) => {
    setSelected(row);
    setIsInativarOpen(true);
  };

  const inativar = async () => {
    if (selected) {
      await api.patch(`/motivos-cancelamento/${selected.mcaId}/inativar`);
      setIsInativarOpen(false);
      await load();
    }
  };

  const ativar = async (row: MotivoCancelamentoItem) => {
    await api.patch(`/motivos-cancelamento/${row.mcaId}/ativar`);
    await load();
  };

  return (
    <Layout>
      <ListingToolbar
        actions={
          <button type="button" className="btn-primary" onClick={openCreate}>
            Novo
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
            keyField="mcaId"
            data={items}
            columns={[
              { key: "mcaNome", header: "Nome" },
              {
                key: "mcaAtivo",
                header: "Status",
                render: (r) => (
                  <span className={`status-badge ${r.mcaAtivo ? "status-badge--active" : "status-badge--inactive"}`}>
                    {r.mcaAtivo ? "Ativo" : "Inativo"}
                  </span>
                ),
              },
              {
                key: "mcaId",
                header: "Ações",
                render: (r) => (
                  <div className="actions">
                    <ActionIconButton icon="edit" label="Editar" onClick={() => openEdit(r)} />
                    {r.mcaAtivo ? (
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
      <Modal isOpen={isModalOpen} title={selected ? "Editar" : "Novo"} onClose={() => setIsModalOpen(false)}>
        <form className="form-vertical" onSubmit={save}>
          <label>
            Nome
            <input
              type="text"
              value={form.mcaNome}
              onChange={(e) => setForm((f) => ({ ...f, mcaNome: e.target.value }))}
              required
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
        message={`Inativar "${selected?.mcaNome}"?`}
        onCancel={() => setIsInativarOpen(false)}
        onConfirm={inativar}
      />
    </Layout>
  );
};

export default MotivoCancelamentoPage;
