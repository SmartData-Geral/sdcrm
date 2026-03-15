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

interface ComoConheceuItem {
  ccoId: number;
  ccoNome: string;
  ccoGrupo?: string | null;
  ccoAtivo: boolean;
}

interface ListResponse {
  items: ComoConheceuItem[];
  total: number;
  page: number;
  page_size: number;
}

const ComoConheceuPage: React.FC = () => {
  const { api } = useAuth();
  const [items, setItems] = useState<ComoConheceuItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(10);
  const [total, setTotal] = useState(0);
  const [nomeFiltro, setNomeFiltro] = useState("");
  const [statusFiltro, setStatusFiltro] = useState<"todos" | "ativos" | "inativos">("ativos");
  const [selected, setSelected] = useState<ComoConheceuItem | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isInativarOpen, setIsInativarOpen] = useState(false);
  const [form, setForm] = useState({ ccoNome: "", ccoGrupo: "" });

  const load = async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { page, page_size: pageSize, status: statusFiltro };
      if (nomeFiltro.trim()) params.nome = nomeFiltro.trim();
      const res = await api.get<ListResponse>("/como-conheceu", { params });
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
    setForm({ ccoNome: "", ccoGrupo: "" });
    setIsModalOpen(true);
  };

  const openEdit = (row: ComoConheceuItem) => {
    setSelected(row);
    setForm({ ccoNome: row.ccoNome, ccoGrupo: row.ccoGrupo ?? "" });
    setIsModalOpen(true);
  };

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    const payload = {
      ...form,
      ccoGrupo: form.ccoGrupo.trim() || null,
    };
    if (selected) {
      await api.put(`/como-conheceu/${selected.ccoId}`, payload);
    } else {
      await api.post("/como-conheceu", payload);
    }
    setIsModalOpen(false);
    await load();
  };

  const confirmInativar = (row: ComoConheceuItem) => {
    setSelected(row);
    setIsInativarOpen(true);
  };

  const inativar = async () => {
    if (selected) {
      await api.patch(`/como-conheceu/${selected.ccoId}/inativar`);
      setIsInativarOpen(false);
      await load();
    }
  };

  const ativar = async (row: ComoConheceuItem) => {
    await api.patch(`/como-conheceu/${row.ccoId}/ativar`);
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
            keyField="ccoId"
            data={items}
            columns={[
              { key: "ccoNome", header: "Nome" },
              {
                key: "ccoGrupo",
                header: "Grupo",
                render: (r) => r.ccoGrupo || "-",
              },
              {
                key: "ccoAtivo",
                header: "Status",
                render: (r) => (
                  <span className={`status-badge ${r.ccoAtivo ? "status-badge--active" : "status-badge--inactive"}`}>
                    {r.ccoAtivo ? "Ativo" : "Inativo"}
                  </span>
                ),
              },
              {
                key: "ccoId",
                header: "Ações",
                render: (r) => (
                  <div className="actions">
                    <ActionIconButton icon="edit" label="Editar" onClick={() => openEdit(r)} />
                    {r.ccoAtivo ? (
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
              value={form.ccoNome}
              onChange={(e) => setForm((f) => ({ ...f, ccoNome: e.target.value }))}
              required
            />
          </label>
          <label>
            Grupo
            <input
              type="text"
              value={form.ccoGrupo}
              onChange={(e) => setForm((f) => ({ ...f, ccoGrupo: e.target.value }))}
              maxLength={100}
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
        message={`Inativar "${selected?.ccoNome}"?`}
        onCancel={() => setIsInativarOpen(false)}
        onConfirm={inativar}
      />
    </Layout>
  );
};

export default ComoConheceuPage;
