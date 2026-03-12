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

interface EmpresaItem {
  empId: number;
  empNome: string;
  empAtivo: boolean;
}

interface ListResponse {
  items: EmpresaItem[];
  total: number;
  page: number;
  page_size: number;
}

const EmpresasPage: React.FC = () => {
  const { api } = useAuth();
  const [items, setItems] = useState<EmpresaItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(10);
  const [total, setTotal] = useState(0);
  const [nomeFiltro, setNomeFiltro] = useState("");
  const [statusFiltro, setStatusFiltro] = useState<"todos" | "ativos" | "inativos">("ativos");
  const [selected, setSelected] = useState<EmpresaItem | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isInativarOpen, setIsInativarOpen] = useState(false);
  const [form, setForm] = useState({ empNome: "" });

  const load = async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = {
        gestao: 1,
        page,
        page_size: pageSize,
        status: statusFiltro,
      };
      if (nomeFiltro.trim()) params.nome = nomeFiltro.trim();
      const res = await api.get<ListResponse>("/empresas", { params });
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
    setForm({ empNome: "" });
    setIsModalOpen(true);
  };

  const openEdit = (row: EmpresaItem) => {
    setSelected(row);
    setForm({ empNome: row.empNome });
    setIsModalOpen(true);
  };

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    if (selected) {
      await api.put(`/empresas/${selected.empId}`, form);
    } else {
      await api.post("/empresas", form);
    }
    setIsModalOpen(false);
    await load();
  };

  const confirmInativar = (row: EmpresaItem) => {
    setSelected(row);
    setIsInativarOpen(true);
  };

  const inativar = async () => {
    if (selected) {
      await api.patch(`/empresas/${selected.empId}/inativar`);
      setIsInativarOpen(false);
      await load();
    }
  };

  const ativar = async (row: EmpresaItem) => {
    await api.patch(`/empresas/${row.empId}/ativar`);
    await load();
  };

  return (
    <Layout>
      <ListingToolbar
        actions={
          <button type="button" className="btn-primary" onClick={openCreate}>
            Nova empresa
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
            keyField="empId"
            data={items}
            columns={[
              { key: "empNome", header: "Nome" },
              {
                key: "empAtivo",
                header: "Status",
                render: (r) => (
                  <span className={`status-badge ${r.empAtivo ? "status-badge--active" : "status-badge--inactive"}`}>
                    {r.empAtivo ? "Ativo" : "Inativo"}
                  </span>
                ),
              },
              {
                key: "empId",
                header: "Ações",
                render: (r) => (
                  <div className="actions">
                    <ActionIconButton icon="edit" label="Editar" onClick={() => openEdit(r)} />
                    {r.empAtivo ? (
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
      <Modal isOpen={isModalOpen} title={selected ? "Editar empresa" : "Nova empresa"} onClose={() => setIsModalOpen(false)}>
        <form className="form-vertical" onSubmit={save}>
          <label>
            Nome
            <input
              type="text"
              value={form.empNome}
              onChange={(e) => setForm((f) => ({ ...f, empNome: e.target.value }))}
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
        message={`Inativar a empresa "${selected?.empNome}"?`}
        onCancel={() => setIsInativarOpen(false)}
        onConfirm={inativar}
      />
    </Layout>
  );
};

export default EmpresasPage;
