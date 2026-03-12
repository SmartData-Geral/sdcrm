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

interface UsuarioItem {
  usuId: number;
  usuNome: string;
  usuEmail: string;
  usuAdmin: boolean;
  usuAtivo: boolean;
  usuAvatarUrl: string | null;
}

interface ListResponse {
  items: UsuarioItem[];
  total: number;
  page: number;
  page_size: number;
}

const UsuariosPage: React.FC = () => {
  const { api } = useAuth();
  const [items, setItems] = useState<UsuarioItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(10);
  const [total, setTotal] = useState(0);
  const [nomeFiltro, setNomeFiltro] = useState("");
  const [statusFiltro, setStatusFiltro] = useState<"todos" | "ativos" | "inativos">("ativos");
  const [selected, setSelected] = useState<UsuarioItem | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isInativarOpen, setIsInativarOpen] = useState(false);
  const [form, setForm] = useState({ usuNome: "", usuEmail: "", usuSenha: "", usuAdmin: false, usuAvatarUrl: "" });

  const load = async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { page, page_size: pageSize, status: statusFiltro };
      if (nomeFiltro.trim()) params.nome = nomeFiltro.trim();
      const res = await api.get<ListResponse>("/usuarios", { params });
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
    setForm({ usuNome: "", usuEmail: "", usuSenha: "", usuAdmin: false, usuAvatarUrl: "" });
    setIsModalOpen(true);
  };

  const openEdit = (row: UsuarioItem) => {
    setSelected(row);
    setForm({
      usuNome: row.usuNome,
      usuEmail: row.usuEmail,
      usuSenha: "",
      usuAdmin: row.usuAdmin,
      usuAvatarUrl: row.usuAvatarUrl ?? "",
    });
    setIsModalOpen(true);
  };

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    if (selected) {
      const payload: { usuNome: string; usuEmail: string; usuAdmin: boolean; usuAvatarUrl?: string | null; usuSenha?: string } = {
        usuNome: form.usuNome,
        usuEmail: form.usuEmail,
        usuAdmin: form.usuAdmin,
        usuAvatarUrl: form.usuAvatarUrl.trim() || null,
      };
      if (form.usuSenha) payload.usuSenha = form.usuSenha;
      await api.put(`/usuarios/${selected.usuId}`, payload);
    } else {
      if (!form.usuSenha) return;
      await api.post("/usuarios", {
        usuNome: form.usuNome,
        usuEmail: form.usuEmail,
        usuSenha: form.usuSenha,
        usuAdmin: form.usuAdmin,
        usuAvatarUrl: form.usuAvatarUrl.trim() || null,
      });
    }
    setIsModalOpen(false);
    await load();
  };

  const confirmInativar = (row: UsuarioItem) => {
    setSelected(row);
    setIsInativarOpen(true);
  };

  const inativar = async () => {
    if (selected) {
      await api.patch(`/usuarios/${selected.usuId}/inativar`);
      setIsInativarOpen(false);
      await load();
    }
  };

  const ativar = async (row: UsuarioItem) => {
    await api.patch(`/usuarios/${row.usuId}/ativar`);
    await load();
  };

  return (
    <Layout>
      <ListingToolbar
        actions={
          <button type="button" className="btn-primary" onClick={openCreate}>
            Novo usuário
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
            keyField="usuId"
            data={items}
            columns={[
              { key: "usuNome", header: "Nome" },
              { key: "usuEmail", header: "E-mail" },
              {
                key: "usuAdmin",
                header: "Admin",
                render: (r) => (r.usuAdmin ? "Sim" : "Não"),
              },
              {
                key: "usuAtivo",
                header: "Status",
                render: (r) => (
                  <span className={`status-badge ${r.usuAtivo ? "status-badge--active" : "status-badge--inactive"}`}>
                    {r.usuAtivo ? "Ativo" : "Inativo"}
                  </span>
                ),
              },
              {
                key: "usuId",
                header: "Ações",
                render: (r) => (
                  <div className="actions">
                    <ActionIconButton icon="edit" label="Editar" onClick={() => openEdit(r)} />
                    {r.usuAtivo ? (
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
      <Modal isOpen={isModalOpen} title={selected ? "Editar usuário" : "Novo usuário"} onClose={() => setIsModalOpen(false)}>
        <form className="form-vertical" onSubmit={save}>
          <label>
            Nome
            <input
              type="text"
              value={form.usuNome}
              onChange={(e) => setForm((f) => ({ ...f, usuNome: e.target.value }))}
              required
            />
          </label>
          <label>
            E-mail
            <input
              type="email"
              value={form.usuEmail}
              onChange={(e) => setForm((f) => ({ ...f, usuEmail: e.target.value }))}
              required
              disabled={!!selected}
            />
          </label>
          <label>
            Senha {selected && "(deixe em branco para não alterar)"}
            <input
              type="password"
              value={form.usuSenha}
              onChange={(e) => setForm((f) => ({ ...f, usuSenha: e.target.value }))}
              required={!selected}
              minLength={6}
            />
          </label>
          <label>
            Avatar (URL)
            <input
              type="url"
              value={form.usuAvatarUrl}
              onChange={(e) => setForm((f) => ({ ...f, usuAvatarUrl: e.target.value }))}
              placeholder="https://..."
            />
          </label>
          <label className="checkbox-inline">
            <input
              type="checkbox"
              checked={form.usuAdmin}
              onChange={(e) => setForm((f) => ({ ...f, usuAdmin: e.target.checked }))}
            />
            Administrador
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
        message={`Inativar o usuário "${selected?.usuNome}"?`}
        onCancel={() => setIsInativarOpen(false)}
        onConfirm={inativar}
      />
    </Layout>
  );
};

export default UsuariosPage;
