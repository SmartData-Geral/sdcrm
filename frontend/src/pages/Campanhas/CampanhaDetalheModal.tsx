import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import Loader from "../../components/Loader";
import Modal from "../../components/Modal";
import { useAuth } from "../../contexts/AuthContext";
import {
  MetaAdsCampanhaDetalhe,
  MetaAdsSerieDia,
  dataBR,
  moeda,
  multiplicador,
} from "./metaAdsTipos";

const GraficoDiario: React.FC<{ serie: MetaAdsSerieDia[] }> = ({ serie }) => {
  if (serie.length === 0) return <p className="muted-text">Sem movimento no período.</p>;
  const largura = 640;
  const altura = 180;
  const passo = largura / serie.length;
  const maxInv = Math.max(1, ...serie.map((d) => d.investimento));
  const maxLeads = Math.max(1, ...serie.map((d) => d.leadsCrm));
  const pontos = serie
    .map((d, i) => `${i * passo + passo / 2},${altura - (d.leadsCrm / maxLeads) * (altura - 10)}`)
    .join(" ");
  return (
    <div className="campanha-grafico">
      <svg viewBox={`0 0 ${largura} ${altura}`} role="img" aria-label="Investimento e leads por dia">
        {serie.map((d, i) => {
          const h = (d.investimento / maxInv) * (altura - 10);
          return (
            <rect key={d.data} x={i * passo + passo * 0.15} y={altura - h} width={passo * 0.7} height={h} className="campanha-grafico-barra">
              <title>{`${dataBR(d.data)}: ${moeda(d.investimento)} · ${d.leadsCrm} lead(s) no CRM · ${d.leadsMeta} no Meta`}</title>
            </rect>
          );
        })}
        <polyline points={pontos} className="campanha-grafico-linha" />
      </svg>
      <div className="campanha-grafico-legenda muted-text">
        <span className="campanha-legenda-barra" /> Investimento <span className="campanha-legenda-linha" /> Leads no CRM
      </div>
    </div>
  );
};

const CampanhaDetalheModal: React.FC<{
  mcgId: number | null;
  inicio: string;
  fim: string;
  onClose: () => void;
}> = ({ mcgId, inicio, fim, onClose }) => {
  const { api } = useAuth();
  const [dados, setDados] = useState<MetaAdsCampanhaDetalhe | null>(null);
  const [loading, setLoading] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    if (mcgId == null) return;
    setLoading(true);
    setDados(null);
    setErro(null);
    api
      .get<MetaAdsCampanhaDetalhe>(`/meta-ads/campanhas/${mcgId}`, { params: { data_inicial: inicio || undefined, data_final: fim || undefined } })
      .then((res) => setDados(res.data))
      .catch(() => setErro("Não foi possível carregar a campanha."))
      .finally(() => setLoading(false));
  }, [api, mcgId, inicio, fim]);

  const c = dados?.campanha;
  return (
    <Modal isOpen={mcgId != null} title={c?.nome ?? "Campanha"} onClose={onClose}>
      {erro ? (
        <div className="integracao-erro">{erro}</div>
      ) : loading || !dados || !c ? (
        <Loader />
      ) : (
        <div className="campanha-detalhe">
          <div className="campanha-detalhe-kpis">
            <span>Investimento <strong>{moeda(c.investimento)}</strong></span>
            <span>Leads CRM <strong>{c.leadsCrm}</strong></span>
            <span>CPL <strong>{moeda(c.cpl)}</strong></span>
            <span>Vendas <strong>{c.vendas}</strong></span>
            <span>CAC <strong>{moeda(c.cac)}</strong></span>
            <span>Retorno <strong>{multiplicador(c.retorno)}</strong></span>
          </div>
          <GraficoDiario serie={dados.serie} />
          <h3 className="detail-field-group-title">Leads da campanha</h3>
          {dados.leads.length === 0 ? (
            <p className="muted-text">Nenhum lead ligado a esta campanha no período.</p>
          ) : (
            <table className="datatable">
              <thead>
                <tr>
                  <th>Oportunidade</th>
                  <th>Contato</th>
                  <th>Recebida</th>
                  <th>Status</th>
                  <th>Valor fechado</th>
                </tr>
              </thead>
              <tbody>
                {dados.leads.map((l) => (
                  <tr key={l.opoId}>
                    <td>
                      <Link to={`/oportunidades/${l.opoId}`}>{l.opoTitulo}</Link>
                    </td>
                    <td>{l.opoNomeContato ?? "—"}</td>
                    <td>{dataBR(l.opoDataRecebimento)}</td>
                    <td>{l.opoStatusFechamento ?? "Em aberto"}</td>
                    <td>{l.opoValorFechado != null ? moeda(l.opoValorFechado) : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </Modal>
  );
};

export default CampanhaDetalheModal;
