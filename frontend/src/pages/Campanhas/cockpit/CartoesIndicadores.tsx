import { SeloSaude } from "./SeloSaude";
import { inteiro, moeda, multiplicador, percentual, type CockpitSelo, type MetaAdsCockpit } from "../metaAdsTipos";

interface Cartao {
  chave: string;
  rotulo: string;
  valor: string;
  selo: CockpitSelo | null;
  atual: number | null;
  anterior: number | null;
  tendencia: string;
  explica: string;
}

/** Texto da variação. Para custos, cair é bom; o texto diz só "caiu"/"subiu", sem depender de seta ou cor. */
function variacao(atual: number | null, anterior: number | null): string | null {
  if (atual == null || anterior == null) return null;
  if (anterior === 0) return atual === 0 ? "igual ao período anterior" : "subiu em relação a um período anterior zerado";
  const pct = ((atual - anterior) / Math.abs(anterior)) * 100;
  if (Math.abs(pct) < 0.05) return "igual ao período anterior";
  const txt = `${Math.abs(pct).toLocaleString("pt-BR", { maximumFractionDigits: 0 })}%`;
  return pct < 0 ? `caiu ${txt} vs. período anterior` : `subiu ${txt} vs. período anterior`;
}

function tendenciaInvestimento(cockpit: MetaAdsCockpit): string {
  const pontos = cockpit.serie.slice(-4);
  if (!pontos.length) return "Sem investimento no período";
  return pontos.map((p) => `${p.rotulo} ${moeda(p.investimento)}`).join(" · ");
}

function tendenciaCpl(cockpit: MetaAdsCockpit): string {
  const comGasto = cockpit.serie.filter((p) => p.investimento > 0 && p.cpl != null);
  if (comGasto.length < 2) return `Meta: ${moeda(cockpit.metas.cpl)}`;
  const primeiro = comGasto[0];
  const ultimo = comGasto[comGasto.length - 1];
  const verbo = (ultimo.cpl as number) < (primeiro.cpl as number) ? "caiu" : "subiu";
  return `${verbo} de ${moeda(primeiro.cpl)} (${primeiro.rotulo}) para ${moeda(ultimo.cpl)} (${ultimo.rotulo})`;
}

function montarCartoes(c: MetaAdsCockpit): Cartao[] {
  const t = c.total;
  const a = c.anterior;
  return [
    {
      chave: "investimento", rotulo: "Investimento", valor: moeda(t.investimento), selo: null,
      atual: t.investimento, anterior: a.investimento, tendencia: tendenciaInvestimento(c),
      explica: "Quanto foi pago à Meta no período.",
    },
    {
      chave: "leads", rotulo: "Leads", valor: inteiro(t.leadsMeta), selo: null,
      atual: t.leadsMeta, anterior: a.leadsMeta, tendencia: `${inteiro(t.leadsCrm)} chegaram ao CRM com o anúncio`,
      explica: "Pessoas que preencheram o formulário.",
    },
    {
      chave: "cpl", rotulo: "Custo por lead (CPL)", valor: moeda(t.cpl), selo: c.selos.cpl,
      atual: t.cpl, anterior: a.cpl, tendencia: tendenciaCpl(c),
      explica: `Quanto custou, em média, cada contato. Meta: ${moeda(c.metas.cpl)}.`,
    },
    {
      chave: "mqls", rotulo: "MQLs", valor: inteiro(t.mqls), selo: c.selos.taxaMql,
      atual: t.mqls, anterior: a.mqls,
      tendencia: c.taxaMql == null ? "Sem lead no CRM para calcular a taxa" : `${percentual(c.taxaMql)} dos leads do CRM`,
      explica: "Leads que chegaram à reunião de levantamento.",
    },
    {
      chave: "custoMql", rotulo: "Custo por MQL", valor: moeda(t.custoMql), selo: c.selos.custoMql,
      atual: t.custoMql, anterior: a.custoMql, tendencia: `Meta implícita: ${moeda(c.metas.custoMqlImplicito)}`,
      explica: "Quanto custa cada lead que vira reunião.",
    },
    {
      chave: "oportunidades", rotulo: "Oportunidades", valor: inteiro(t.oportunidades), selo: null,
      atual: t.oportunidades, anterior: a.oportunidades,
      tendencia: `${inteiro(t.oportunidades)} de ${inteiro(t.mqls)} MQLs avançou`,
      explica: "Chegaram à reunião de vendas ou além.",
    },
    {
      chave: "contratos", rotulo: "Contratos", valor: inteiro(t.vendas), selo: null,
      atual: t.vendas, anterior: a.vendas,
      tendencia: t.vendas === 0 ? "Nenhum ganho atribuído à Meta" : "Ganhos atribuídos à Meta",
      explica: "Leads da Meta marcados como ganhos.",
    },
    {
      chave: "retorno", rotulo: "Retorno", valor: multiplicador(t.retorno), selo: null,
      atual: t.retorno, anterior: a.retorno,
      tendencia: t.retorno == null ? "Aparece com o 1º contrato" : "Receita do 1º ano por real investido",
      explica: "Receita do 1º ano (MRR × 12 + projeto) por real investido.",
    },
  ];
}

export function CartoesIndicadores({ cockpit, comparar }: { cockpit: MetaAdsCockpit; comparar: boolean }) {
  return (
    <section className="cockpit-cartoes" aria-label="Indicadores do período">
      {montarCartoes(cockpit).map((k) => {
        let linha = k.tendencia;
        if (comparar) {
          if (cockpit.anteriorTemDados) {
            const v = variacao(k.atual, k.anterior);
            if (v) linha = v;
          } else {
            linha = `Sem dados no período anterior · ${k.tendencia}`;
          }
        }
        return (
          <article key={k.chave} className="cockpit-cartao">
            <div className="cockpit-cartao-topo">
              <span className="cockpit-cartao-rotulo">{k.rotulo}</span>
              {k.selo ? <SeloSaude selo={k.selo} /> : null}
            </div>
            <strong className="cockpit-cartao-valor">{k.valor}</strong>
            <span className="cockpit-cartao-linha">{linha}</span>
            <span className="cockpit-cartao-explica">{k.explica}</span>
          </article>
        );
      })}
    </section>
  );
}
