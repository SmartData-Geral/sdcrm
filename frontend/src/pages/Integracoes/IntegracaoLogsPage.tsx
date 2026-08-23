import React, { useEffect, useState } from "react";
import Layout from "../../components/Layout";
import ListingTableCard from "../../components/ListingTableCard";
import Loader from "../../components/Loader";
import { useAuth } from "../../contexts/AuthContext";

interface LogItem {
  irlId: number;
  irlDataCriacao: string;
  irlRota: string;
  irlMetodo: string;
  irlStatusHttp: number;
  irlResultado: string;
  irlOrigemSistema: string | null;
  irlExternalId: string | null;
  irlOpoId: number | null;
  irlPrefixoInformado: string | null;
  irlPayloadJson: unknown;
  irlErroJson: unknown;
  irlIp: string | null;
  irlDuracaoMs: number | null;
}

const RESULTADOS = [
  { valor: "", rotulo: "Todos" },
  { valor: "created", rotulo: "Criado" },
  { valor: "updated", rotulo: "Atualizado" },
  { valor: "novo_ciclo", rotulo: "Novo ciclo" },
  { valor: "invalid", rotulo: "Inválido (422)" },
  { valor: "unauthorized", rotulo: "Não autorizado (401)" },
  { valor: "conflict", rotulo: "Conflito (409)" },
  { valor: "error", rotulo: "Erro (500)" },
];

const classeStatus = (status: number) => {
  if (status < 300) return "integracao-badge integracao-badge--ok";
  if (status < 500) return "integracao-badge integracao-badge--warn";
  return "integracao-badge integracao-badge--danger";
};

const IntegracaoLogsPage: React.FC = () => {
  const { api } = useAuth();
  const [items, setItems] = useState<LogItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [resultado, setResultado] = useState("");
  const [origem, setOrigem] = useState("");
  const [expandido, setExpandido] = useState<number | null>(null);

  const carregar = async () => {
    setLoading(true);
    try {
      const res = await api.get<{ items: LogItem[]; total: number }>("/integracao-logs", {
        params: {
          resultado: resultado || undefined,
          origem: origem || undefined,
          page_size: 100,
        },
      });
      setItems(res.data.items ?? []);
      setTotal(res.data.total ?? 0);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void carregar();
  }, [resultado]);

  return (
    <Layout>
      <section className="surface-card details-card">
        <h2 className="section-title">Log de integração</h2>
        <p className="muted-text">
          Toda chamada à API externa fica registrada aqui, inclusive as recusadas por chave inválida (401) e
          as com payload inválido (422). E-mail e telefone aparecem mascarados, e a chave nunca é gravada —
          apenas o prefixo público.
        </p>
        <div className="integracao-filtros">
          <label>
            Resultado
            <select value={resultado} onChange={(e) => setResultado(e.target.value)}>
              {RESULTADOS.map((opcao) => (
                <option key={opcao.valor} value={opcao.valor}>
                  {opcao.rotulo}
                </option>
              ))}
            </select>
          </label>
          <label>
            Origem
            <input
              value={origem}
              onChange={(e) => setOrigem(e.target.value)}
              placeholder="Ex.: planilha_leads"
              onKeyDown={(e) => e.key === "Enter" && void carregar()}
            />
          </label>
          <button type="button" onClick={() => void carregar()}>
            Filtrar
          </button>
        </div>
      </section>

      <ListingTableCard footer={<span className="muted-text">{total} requisição(ões)</span>}>
        {loading ? (
          <Loader />
        ) : items.length === 0 ? (
          <div className="datatable-empty">Nenhuma requisição registrada.</div>
        ) : (
          <table className="datatable">
            <thead>
              <tr>
                <th>Quando</th>
                <th>Rota</th>
                <th>Status</th>
                <th>Resultado</th>
                <th>Origem</th>
                <th>Oportunidade</th>
                <th>Duração</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {items.map((row) => (
                <React.Fragment key={row.irlId}>
                  <tr>
                    <td>{new Date(row.irlDataCriacao).toLocaleString("pt-BR")}</td>
                    <td>
                      <code>
                        {row.irlMetodo} {row.irlRota}
                      </code>
                    </td>
                    <td>
                      <span className={classeStatus(row.irlStatusHttp)}>{row.irlStatusHttp}</span>
                    </td>
                    <td>{row.irlResultado}</td>
                    <td>{row.irlOrigemSistema || "—"}</td>
                    <td>
                      {row.irlOpoId ? (
                        <a href={`/crm/oportunidades/${row.irlOpoId}`}>#{row.irlOpoId}</a>
                      ) : (
                        "—"
                      )}
                    </td>
                    <td>{row.irlDuracaoMs != null ? `${row.irlDuracaoMs} ms` : "—"}</td>
                    <td>
                      <button
                        type="button"
                        onClick={() => setExpandido(expandido === row.irlId ? null : row.irlId)}
                      >
                        {expandido === row.irlId ? "Ocultar" : "Detalhes"}
                      </button>
                    </td>
                  </tr>
                  {expandido === row.irlId ? (
                    <tr>
                      <td colSpan={8}>
                        <div className="integracao-detalhe">
                          <div>
                            <strong>Chave apresentada:</strong>{" "}
                            <code>{row.irlPrefixoInformado || "—"}</code>
                            {row.irlIp ? (
                              <>
                                {" · "}
                                <strong>IP:</strong> <code>{row.irlIp}</code>
                              </>
                            ) : null}
                            {row.irlExternalId ? (
                              <>
                                {" · "}
                                <strong>external_id:</strong> <code>{row.irlExternalId}</code>
                              </>
                            ) : null}
                          </div>
                          <div>
                            <strong>Payload recebido (redigido)</strong>
                            <pre className="integracao-json">
                              {JSON.stringify(row.irlPayloadJson ?? null, null, 2)}
                            </pre>
                          </div>
                          {row.irlErroJson ? (
                            <div>
                              <strong>Erro de validação</strong>
                              <pre className="integracao-json">
                                {JSON.stringify(row.irlErroJson, null, 2)}
                              </pre>
                            </div>
                          ) : null}
                        </div>
                      </td>
                    </tr>
                  ) : null}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        )}
      </ListingTableCard>
    </Layout>
  );
};

export default IntegracaoLogsPage;
