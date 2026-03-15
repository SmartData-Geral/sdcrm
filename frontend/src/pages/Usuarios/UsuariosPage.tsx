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
import UserAvatar from "../../components/UserAvatar";
import { useAuth } from "../../contexts/AuthContext";
import { getAvatarSrc } from "../../utils/api";

interface UsuarioItem {
  usuId: number;
  usuNome: string;
  usuEmail: string;
  usuAdmin: boolean;
  usuAtivo: boolean;
  usuAvatarUrl: string | null;
   empresas?: string[] | null;
}

interface UsuarioForm {
  usuNome: string;
  usuEmail: string;
  usuSenha: string;
  usuPerfil: "ADMIN" | "USER";
  usuAvatarUrl: string;
  empresasIds: number[];
}

interface ListResponse {
  items: UsuarioItem[];
  total: number;
  page: number;
  page_size: number;
}

interface EmpresaItem {
  empId: number;
  empNome: string;
}

interface EmpresaListResponse {
  items: EmpresaItem[];
}

const UsuariosPage: React.FC = () => {
  const { api, companyId } = useAuth();
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
  const [empresas, setEmpresas] = useState<EmpresaItem[]>([]);
  const [form, setForm] = useState<UsuarioForm>({
    usuNome: "",
    usuEmail: "",
    usuSenha: "",
    usuPerfil: "USER",
    usuAvatarUrl: "",
    empresasIds: [],
  });
  const [avatarUploading, setAvatarUploading] = useState(false);

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

  useEffect(() => {
    const loadEmpresas = async () => {
      const res = await api.get<EmpresaListResponse>("/empresas", {
        params: { gestao: 1, status: "ativos", page: 1, page_size: 100 },
      });
      setEmpresas(res.data.items);
    };
    void loadEmpresas();
  }, [api]);

  const openCreate = () => {
    setSelected(null);
    setForm({
      usuNome: "",
      usuEmail: "",
      usuSenha: "",
      usuPerfil: "USER",
      usuAvatarUrl: "",
      empresasIds: [],
    });
    setIsModalOpen(true);
  };

  const openEdit = (row: UsuarioItem) => {
    setSelected(row);
    setForm({
      usuNome: row.usuNome,
      usuEmail: row.usuEmail,
      usuSenha: "",
      usuPerfil: row.usuAdmin ? "ADMIN" : "USER",
      usuAvatarUrl: row.usuAvatarUrl ?? "",
      empresasIds: [],
    });
    setIsModalOpen(true);
  };

  const handleAvatarFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const ext = file.name.toLowerCase().slice(file.name.lastIndexOf("."));
    if (![".png", ".jpg", ".jpeg"].includes(ext)) {
      return;
    }
    setAvatarUploading(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await api.post<{ avatarUrl: string }>("/usuarios/avatar/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setForm((f) => ({ ...f, usuAvatarUrl: res.data.avatarUrl }));
    } finally {
      setAvatarUploading(false);
      e.target.value = "";
    }
  };

  const removeAvatar = () => {
    setForm((f) => ({ ...f, usuAvatarUrl: "" }));
  };

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    if (selected) {
      const payload: {
        usuNome: string;
        usuEmail: string;
        usuAdmin: boolean;
        usuPerfil: "ADMIN" | "USER";
        usuAvatarUrl?: string | null;
        usuSenha?: string;
        empresasIds?: number[];
      } = {
        usuNome: form.usuNome,
        usuEmail: form.usuEmail,
        usuAdmin: form.usuPerfil === "ADMIN",
        usuPerfil: form.usuPerfil,
        usuAvatarUrl: form.usuAvatarUrl.trim() || null,
      };
      if (form.usuSenha) payload.usuSenha = form.usuSenha;
      if (form.usuPerfil === "USER") {
        payload.empresasIds = form.empresasIds;
      }
      await api.put(`/usuarios/${selected.usuId}`, payload);
    } else {
      if (!form.usuSenha) return;
      await api.post("/usuarios", {
        usuNome: form.usuNome,
        usuEmail: form.usuEmail,
        usuSenha: form.usuSenha,
        usuAdmin: form.usuPerfil === "ADMIN",
        usuPerfil: form.usuPerfil,
        usuAvatarUrl: form.usuAvatarUrl.trim() || null,
        empresasIds:
          form.usuPerfil === "USER"
            ? form.empresasIds
            : companyId
            ? [companyId]
            : [],
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
                key: "empresas",
                header: "Empresas",
                render: (r) =>
                  r.usuAdmin ? "Todas" : (r.empresas && r.empresas.length > 0 ? r.empresas.join(", ") : "-"),
              },
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
            Perfil *
            <select
              value={form.usuPerfil}
              onChange={(e) =>
                setForm((f) => ({
                  ...f,
                  usuPerfil: e.target.value as UsuarioForm["usuPerfil"],
                }))
              }
            >
              <option value="ADMIN">ADMIN</option>
              <option value="USER">USER</option>
            </select>
          </label>
          {form.usuPerfil === "USER" && (
            <div>
              <p>Empresas *</p>
              <div className="empresa-checkbox-grid">
                {empresas.map((emp) => (
                  <label key={emp.empId} className="checkbox-inline">
                    <input
                      type="checkbox"
                      checked={form.empresasIds.includes(emp.empId)}
                      onChange={(e) =>
                        setForm((f) => ({
                          ...f,
                          empresasIds: e.target.checked
                            ? [...f.empresasIds, emp.empId]
                            : f.empresasIds.filter((id) => id !== emp.empId),
                        }))
                      }
                    />
                    {emp.empNome}
                  </label>
                ))}
              </div>
            </div>
          )}
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
            Avatar
            <div className="avatar-upload-area">
              {form.usuAvatarUrl ? (
                <div className="avatar-preview-wrap">
                  <img
                    src={getAvatarSrc(form.usuAvatarUrl) || ""}
                    alt="Avatar"
                    className="avatar-preview-img"
                  />
                  {!avatarUploading && (
                    <button type="button" className="btn-link btn-link-danger" onClick={removeAvatar}>
                      Remover
                    </button>
                  )}
                </div>
              ) : (
                <UserAvatar name={form.usuNome || "?"} avatarUrl={null} size="md" />
              )}
              <input
                type="file"
                accept=".png,.jpg,.jpeg,image/png,image/jpeg"
                onChange={handleAvatarFileChange}
                disabled={avatarUploading}
              />
              {avatarUploading && <span className="avatar-upload-status">Enviando...</span>}
              <span className="field-hint">PNG ou JPG</span>
            </div>
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
