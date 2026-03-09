import React, { useEffect, useState } from "react";
import Layout from "../../components/Layout";
import { DataTable } from "../../components/DataTable";
import Loader from "../../components/Loader";
import ConfirmDialog from "../../components/ConfirmDialog";
import Modal from "../../components/Modal";
import { useAuth } from "../../contexts/AuthContext";

interface Cliente {
  cliId: number;
  cliNome: string;
  cliEmail?: string | null;
  cliTelefone?: string | null;
  cliAtivo: boolean;
}

interface ClienteListResponse {
  items: Cliente[];
  total: number;
  page: number;
  page_size: number;
}

const ClientesPage: React.FC = () => {
  const { api } = useAuth();
  const [clientes, setClientes] = useState<Cliente[]>([]);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(10);
  const [total, setTotal] = useState(0);
  const [nomeFiltro, setNomeFiltro] = useState("");
  const [statusFiltro, setStatusFiltro] = useState<"todos" | "ativos" | "inativos">("ativos");
  const [selected, setSelected] = useState<Cliente | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isDeleteOpen, setIsDeleteOpen] = useState(false);
  const [form, setForm] = useState<{ cliNome: string; cliEmail: string; cliTelefone: string }>({
    cliNome: "",
    cliEmail: "",
    cliTelefone: ""
  });

  const loadClientes = async () => {
    setLoading(true);
    try {
      const params: any = { page, page_size: pageSize };
      if (nomeFiltro.trim()) {
        params.nome = nomeFiltro.trim();
      }
      params.status = statusFiltro;
      const res = await api.get<ClienteListResponse>("/clientes", { params });
      setClientes(res.data.items);
      setTotal(res.data.total);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadClientes();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, nomeFiltro, statusFiltro]);

  const openCreate = () => {
    setSelected(null);
    setForm({ cliNome: "", cliEmail: "", cliTelefone: "" });
    setIsModalOpen(true);
  };

  const openEdit = (cliente: Cliente) => {
    setSelected(cliente);
    setForm({
      cliNome: cliente.cliNome,
      cliEmail: cliente.cliEmail ?? "",
      cliTelefone: cliente.cliTelefone ?? ""
    });
    setIsModalOpen(true);
  };

  const saveCliente = async (e: React.FormEvent) => {
    e.preventDefault();
    if (selected) {
      await api.put(`/clientes/${selected.cliId}`, form);
    } else {
      await api.post("/clientes", form);
    }
    setIsModalOpen(false);
    await loadClientes();
  };

  const confirmDelete = (cliente: Cliente) => {
    setSelected(cliente);
    setIsDeleteOpen(true);
  };

  const deleteCliente = async () => {
    if (selected) {
      await api.delete(`/clientes/${selected.cliId}`);
      setIsDeleteOpen(false);
      await loadClientes();
    }
  };

  return (
    <Layout>
      <div className="page-header">
        <h1>Clientes</h1>
        <div className="page-header-actions">
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
          <button type="button" onClick={openCreate}>
            Novo cliente
          </button>
        </div>
      </div>
      {loading ? (
        <Loader />
      ) : (
        <DataTable
          keyField="cliId"
          data={clientes}
          columns={[
            { key: "cliNome", header: "Nome" },
            { key: "cliEmail", header: "E-mail" },
            { key: "cliTelefone", header: "Telefone" },
            {
              key: "cliAtivo",
              header: "Status",
              render: (c) => (c.cliAtivo ? "Ativo" : "Inativo")
            },
            {
              key: "cliId",
              header: "Ações",
              render: (c) => (
                <div className="actions">
                  <button type="button" onClick={() => openEdit(c)}>
                    Editar
                  </button>
                  <button type="button" className="danger" onClick={() => confirmDelete(c)}>
                    Excluir
                  </button>
                </div>
              )
            }
          ]}
        />
      )}
      <div className="pagination">
        <span>
          Página {page} de {Math.max(1, Math.ceil(total / pageSize))}
        </span>
        <button type="button" disabled={page <= 1} onClick={() => setPage((p) => Math.max(1, p - 1))}>
          Anterior
        </button>
        <button
          type="button"
          disabled={page >= Math.ceil(total / pageSize)}
          onClick={() => setPage((p) => p + 1)}
        >
          Próxima
        </button>
      </div>

      <Modal isOpen={isModalOpen} title={selected ? "Editar cliente" : "Novo cliente"} onClose={() => setIsModalOpen(false)}>
        <form className="form-vertical" onSubmit={saveCliente}>
          <label>
            Nome
            <input
              type="text"
              value={form.cliNome}
              onChange={(e) => setForm((f) => ({ ...f, cliNome: e.target.value }))}
              required
            />
          </label>
          <label>
            E-mail
            <input
              type="email"
              value={form.cliEmail}
              onChange={(e) => setForm((f) => ({ ...f, cliEmail: e.target.value }))}
            />
          </label>
          <label>
            Telefone
            <input
              type="text"
              value={form.cliTelefone}
              onChange={(e) => setForm((f) => ({ ...f, cliTelefone: e.target.value }))}
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
        isOpen={isDeleteOpen}
        message={`Deseja realmente excluir o cliente "${selected?.cliNome}"?`}
        onCancel={() => setIsDeleteOpen(false)}
        onConfirm={deleteCliente}
      />
    </Layout>
  );
};

export default ClientesPage;

