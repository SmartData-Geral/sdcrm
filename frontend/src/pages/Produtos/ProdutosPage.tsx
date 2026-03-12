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

interface ProdutoItem {
  proId: number;
  proNome: string;
  proCor?: string | null;
  proAtivo: boolean;
}

interface ListResponse {
  items: ProdutoItem[];
  total: number;
  page: number;
  page_size: number;
}

const ProdutosPage: React.FC = () => {
  const { api } = useAuth();
  const [items, setItems] = useState<ProdutoItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(10);
  const [total, setTotal] = useState(0);
  const [nomeFiltro, setNomeFiltro] = useState("");
  const [statusFiltro, setStatusFiltro] = useState<"todos" | "ativos" | "inativos">("ativos");
  const [selected, setSelected] = useState<ProdutoItem | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isInativarOpen, setIsInativarOpen] = useState(false);
  const [form, setForm] = useState({ proNome: "", proCor: "#3b82f6" });

  const load = async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { page, page_size: pageSize, status: statusFiltro };
      if (nomeFiltro.trim()) params.nome = nomeFiltro.trim();
      const res = await api.get<ListResponse>("/produtos", { params });
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
    setForm({ proNome: "", proCor: "#3b82f6" });
    setIsModalOpen(true);
  };

  const openEdit = (row: ProdutoItem) => {
    setSelected(row);
    setForm({ proNome: row.proNome, proCor: row.proCor ?? "#3b82f6" });
    setIsModalOpen(true);
  };

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    if (selected) {
      await api.put(`/produtos/${selected.proId}`, form);
    } else {
      await api.post("/produtos", form);
    }
    setIsModalOpen(false);
    await load();
  };

  const confirmInativar = (row: ProdutoItem) => {
    setSelected(row);
    setIsInativarOpen(true);
  };

  const inativar = async () => {
    if (selected) {
      await api.patch(`/produtos/${selected.proId}/inativar`);
      setIsInativarOpen(false);
      await load();
    }
  };

  const ativar = async (row: ProdutoItem) => {
    await api.patch(`/produtos/${row.proId}/ativar`);
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
            keyField="proId"
            data={items}
            columns={[
              { key: "proNome", header: "Nome" },
              {
                key: "proAtivo",
                header: "Status",
                render: (r) => (
                  <span className={`status-badge ${r.proAtivo ? "status-badge--active" : "status-badge--inactive"}`}>
                    {r.proAtivo ? "Ativo" : "Inativo"}
                  </span>
                ),
              },
              {
                key: "proId",
                header: "Ações",
                render: (r) => (
                  <div className="actions">
                    <ActionIconButton icon="edit" label="Editar" onClick={() => openEdit(r)} />
                    {r.proAtivo ? (
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
      <Modal isOpen={isModalOpen} title={selected ? "Editar produto" : "Novo produto"} onClose={() => setIsModalOpen(false)}>
        <form className="form-vertical" onSubmit={save}>
          <label>
            Nome
            <input
              type="text"
              value={form.proNome}
              onChange={(e) => setForm((f) => ({ ...f, proNome: e.target.value }))}
              required
            />
          </label>
          <label>
            Cor do badge
            <input
              type="color"
              value={form.proCor}
              onChange={(e) => setForm((f) => ({ ...f, proCor: e.target.value }))}
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
        message={`Inativar o produto "${selected?.proNome}"?`}
        onCancel={() => setIsInativarOpen(false)}
        onConfirm={inativar}
      />
    </Layout>
  );
};

export default ProdutosPage;
