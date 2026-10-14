import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../../contexts/AuthContext";
import { MetaAdsResumo, moeda, multiplicador } from "../../pages/Campanhas/metaAdsTipos";

const MetaAdsResumoFaixa: React.FC<{ dataInicial: string | null; dataFinal: string | null }> = ({ dataInicial, dataFinal }) => {
  const { api } = useAuth();
  const [resumo, setResumo] = useState<MetaAdsResumo | null>(null);

  useEffect(() => {
    api
      .get<MetaAdsResumo>("/meta-ads/resumo", {
        params: { data_inicial: dataInicial || undefined, data_final: dataFinal || undefined },
      })
      .then((r) => setResumo(r.data))
      .catch(() => setResumo(null));
  }, [api, dataInicial, dataFinal]);

  if (!resumo?.temConta) return null;

  const cards: Array<[string, string]> = [
    ["Investimento Meta", moeda(resumo.investimento)],
    ["CPL", moeda(resumo.cpl)],
    ["CAC", moeda(resumo.cac)],
    ["Retorno", multiplicador(resumo.retorno)],
  ];
  return (
    <section className="dashboard-meta-ads">
      <div className="dashboard-meta-ads-header">
        <h2 className="section-title">Meta Ads</h2>
        <Link to="/campanhas">Ver campanhas</Link>
      </div>
      <div className="dashboard-cards-row">
        {cards.map(([rotulo, valor]) => (
          <div key={rotulo} className="dashboard-card">
            <strong className="dashboard-card-value">{valor}</strong>
            <span className="dashboard-card-label">{rotulo}</span>
          </div>
        ))}
      </div>
    </section>
  );
};

export default MetaAdsResumoFaixa;
