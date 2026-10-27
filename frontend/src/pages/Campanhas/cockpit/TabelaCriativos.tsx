import { inteiro, moeda, percentual, rotuloStatusCampanha, type CockpitCriativo, type MetaAdsCockpit } from "../metaAdsTipos";

const COR_ETIQUETA: Record<CockpitCriativo["quadrante"], string> = {
  escalar: "#0f766e",
  otimizar_custo: "#1d4ed8",
  rever_publico: "#b45309",
  pausar: "#b91c1c",
  aguardar_dados: "#475569",
};

function porque(c: CockpitCriativo) {
  if (!c.amostraPequena || /amostra pequena/i.test(c.porque)) return c.porque;
  return `${c.porque} Amostra pequena: menos de 5 leads no CRM.`;
}

export function TabelaCriativos({ cockpit }: { cockpit: MetaAdsCockpit }) {
  const linhas = [...cockpit.criativos].sort((a, b) => b.investimento - a.investimento);
  return (
    <section className="cockpit-bloco" aria-labelledby="cockpit-tabela-titulo">
      <h2 id="cockpit-tabela-titulo">Criativos: o que fazer com cada um</h2>
      {linhas.length === 0 ? (
        <p className="cockpit-vazio">Nenhum anúncio com investimento no período.</p>
      ) : (
        <div className="campanhas-tabela-scroll">
          <table className="dashboard-ranking-table cockpit-tabela">
            <thead>
              <tr>
                <th>Criativo</th>
                <th>Campanha</th>
                <th>Status</th>
                <th>Investido</th>
                <th>Leads</th>
                <th>CPL</th>
                <th>MQLs</th>
                <th>Taxa de MQL</th>
                <th>Recomendação</th>
                <th>Por quê</th>
              </tr>
            </thead>
            <tbody>
              {linhas.map((c) => (
                <tr key={`${c.id ?? c.nome}-${c.mcgId ?? ""}`}>
                  <td className="cockpit-tabela-nome">{c.nome}</td>
                  <td>{c.campanha}</td>
                  <td>{rotuloStatusCampanha(c.status)}</td>
                  <td>{moeda(c.investimento)}</td>
                  <td>{inteiro(c.leadsMeta)}</td>
                  <td>{moeda(c.cpl)}</td>
                  <td>{inteiro(c.mqls)}</td>
                  <td>{percentual(c.taxaMql)}</td>
                  <td>
                    <span className="cockpit-etiqueta" style={{ background: COR_ETIQUETA[c.quadrante] }}>{c.recomendacao}</span>
                  </td>
                  <td className="cockpit-tabela-porque">{porque(c)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
