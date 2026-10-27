import { Link } from "react-router-dom";
import { horas, inteiro, percentual, type MetaAdsCockpit } from "../metaAdsTipos";

export function SaudeOperacao({ cockpit }: { cockpit: MetaAdsCockpit }) {
  const o = cockpit.operacao;
  return (
    <section className="cockpit-cartoes" aria-label="Saúde da operação">
      <article className="cockpit-cartao">
        <span className="cockpit-cartao-rotulo">Rastreio dos leads</span>
        <strong className="cockpit-cartao-valor">{o.cobertura == null ? "—" : percentual(o.cobertura)}</strong>
        <span className="cockpit-cartao-explica">dos leads da Meta chegam com o anúncio identificado (meta: 90%)</span>
      </article>
      <article className="cockpit-cartao">
        <span className="cockpit-cartao-rotulo">Tempo até o 1º contato</span>
        <strong className="cockpit-cartao-valor">{o.horasPrimeiroContato == null ? "—" : `${horas(o.horasPrimeiroContato)} h`}</strong>
        <span className="cockpit-cartao-explica">da entrada do lead até o cartão sair de "Contatos"</span>
      </article>
      <article className="cockpit-cartao">
        <span className="cockpit-cartao-rotulo">Alertas abertos</span>
        <strong className="cockpit-cartao-valor">{inteiro(o.alertasAbertos)}</strong>
        <span className="cockpit-cartao-explica">CPL fora do padrão, saturação, lead sem contato…</span>
        <Link to="/monitoramento" className="cockpit-cartao-link">Ver alertas</Link>
      </article>
      <article className="cockpit-cartao">
        <span className="cockpit-cartao-rotulo">Origem a revisar</span>
        <strong className="cockpit-cartao-valor">{`${inteiro(o.origemRevisar)} ${o.origemRevisar === 1 ? "lead" : "leads"}`}</strong>
        <span className="cockpit-cartao-explica">marcados como "Anúncios" sem registro na Meta</span>
        <a href="#revisao-origem" className="cockpit-cartao-link">Ver a lista</a>
      </article>
    </section>
  );
}
