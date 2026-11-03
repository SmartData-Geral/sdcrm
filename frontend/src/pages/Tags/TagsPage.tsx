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
import TagBadge from "../../components/tags/TagBadge";
import { useAuth } from "../../contexts/AuthContext";

interface TagItem {
  tagId: number;
  tagNome: string;
  tagCor: string;
  tagAtivo: boolean;
}

interface ListResponse {
  items: TagItem[];
  total: number;
  page: number;
  page_size: number;
}

const CORES_SUGERIDAS = [
  "#2563eb",
  "#0891b2",
  "#059669",
  "#65a30d",
  "#ca8a04",
  "#ea580c",
  "#dc2626",
  "#db2777",
  "#7c3aed",
  "#475569",
];

const TagsPage: React.FC = () => {
  const { api } = useAuth();
  const [items, setItems] = useState<TagItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(10);
  const [total, setTotal] = useState(0);
  const [nomeFiltro, setNomeFiltro] = useState("");
  const [statusFiltro, setStatusFiltro] = useState<"todos" | "ativos" | "inativos">("ativos");
  const [selected, setSelected] = useState<TagItem | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isInativarOpen, setIsInativarOpen] = useState(false);
  const [form, setForm] = useState({ tagNome: "", tagCor: CORES_SUGERIDAS[0] });
  const [erro, setErro] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { page, page_size: pageSize, status: statusFiltro };
      if (nomeFiltro.trim()) params.nome = nomeFiltro.trim();
      const res = await api.get<ListResponse>("/tags", { params });
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
    setForm({ tagNome: "", tagCor: CORES_SUGERIDAS[0] });
    setErro(null);
    setIsModalOpen(true);
  };

  const openEdit = (row: TagItem) => {
    setSelected(row);
    setForm({ tagNome: row.tagNome, tagCor: row.tagCor });
    setErro(null);
    setIsModalOpen(true);
  };

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    setErro(null);
    try {
      if (selected) {
        await api.put(`/tags/${selected.tagId}`, form);
      } else {
        await api.post("/tags", form);
      }
    } catch (err) {
      const detail = (err as { response?: { data?: { detail?: unknown } } }).response?.data?.detail;
      setErro(typeof detail === "string" ? detail : "Não foi possível salvar a tag.");
      return;
    }
    setIsModalOpen(false);
    await load();
  };

  const confirmInativar = (row: TagItem) => {
    setSelected(row);
    setIsInativarOpen(true);
  };

  const inativar = async () => {
    if (selected) {
      await api.patch(`/tags/${selected.tagId}/inativar`);
      setIsInativarOpen(false);
      await load();
    }
  };

  const ativar = async (row: TagItem) => {
    await api.patch(`/tags/${row.tagId}/ativar`);
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
            keyField="tagId"
            data={items}
            columns={[
              {
                key: "tagNome",
                header: "Tag",
                render: (r) => <TagBadge nome={r.tagNome} cor={r.tagCor} />,
              },
              {
                key: "tagAtivo",
                header: "Status",
                render: (r) => (
                  <span className={`status-badge ${r.tagAtivo ? "status-badge--active" : "status-badge--inactive"}`}>
                    {r.tagAtivo ? "Ativo" : "Inativo"}
                  </span>
                ),
              },
              {
                key: "tagId",
                header: "Ações",
                render: (r) => (
                  <div className="actions">
                    <ActionIconButton icon="edit" label="Editar" onClick={() => openEdit(r)} />
                    {r.tagAtivo ? (
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
              value={form.tagNome}
              maxLength={60}
              onChange={(e) => setForm((f) => ({ ...f, tagNome: e.target.value }))}
              required
            />
          </label>
          <div className="tag-cor-field">
            <span>Cor</span>
            <div className="tag-cor-opcoes">
              {CORES_SUGERIDAS.map((cor) => (
                <button
                  key={cor}
                  type="button"
                  className={`tag-cor-opcao${form.tagCor.toLowerCase() === cor ? " is-active" : ""}`}
                  style={{ background: cor }}
                  aria-label={`Usar a cor ${cor}`}
                  aria-pressed={form.tagCor.toLowerCase() === cor}
                  onClick={() => setForm((f) => ({ ...f, tagCor: cor }))}
                />
              ))}
              <input
                type="color"
                aria-label="Escolher outra cor"
                title="Escolher outra cor"
                value={form.tagCor}
                onChange={(e) => setForm((f) => ({ ...f, tagCor: e.target.value }))}
              />
            </div>
          </div>
          <div className="tag-preview">
            <TagBadge nome={form.tagNome.trim() || "Prévia da tag"} cor={form.tagCor} />
          </div>
          {erro && <div className="error-text">{erro}</div>}
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
        message={`Inativar "${selected?.tagNome}"? Ela deixa de aparecer nos cards.`}
        onCancel={() => setIsInativarOpen(false)}
        onConfirm={inativar}
      />
    </Layout>
  );
};

export default TagsPage;
