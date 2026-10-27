import { ROTULO_ETAPA, inteiro, moeda, type CockpitEtapa, type CockpitEtapaChave, type MetaAdsCockpit } from "../metaAdsTipos";

const LARGURA = [100, 82, 64, 58, 34, 24, 14];
const COR = ["#1e3a8a", "#1e40af", "#1d4ed8", "#2563eb", "#c2410c", "#6d28d9", "#475569"];

const pct = (v: number) => `${v.toLocaleString("pt-BR", { maximumFractionDigits: 2 })}%`;

const TEXTO_TAXA: Record<CockpitEtapaChave, (v: string) => string> = {
  impressoes: () => "impressões",
  cliques: (v) => `${v} de quem viu`,
  leads: (v) => `${v} dos cliques`,
  crm: (v) => `${v} dos leads`,
  mql: (v) => `${v} dos leads do CRM`,
  oportunidade: (v) => `${v} dos MQLs`,
  contrato: (v) => `${v} das oportunidades`,
};

const TEXTO_CUSTO: Record<CockpitEtapaChave, (v: string) => string> = {
  impressoes: (v) => `${v} a cada mil`,
  cliques: (v) => `${v} por clique`,
  leads: (v) => `${v} por lead`,
  crm: (v) => `${v} por lead no CRM`,
  mql: (v) => `${v} por MQL`,
  oportunidade: (v) => `${v} por oportunidade`,
  contrato: (v) => `${v} por contrato`,
};

function textoTaxa(e: CockpitEtapa) {
  if (e.chave === "impressoes") return TEXTO_TAXA.impressoes("");
  return e.taxa == null ? "—" : TEXTO_TAXA[e.chave](pct(e.taxa));
}

export function FunilCockpit({ cockpit }: { cockpit: MetaAdsCockpit }) {
  const resumo = cockpit.funil.map((e) => `${ROTULO_ETAPA[e.chave]}: ${inteiro(e.quantidade)}`).join("; ");
  return (
    <section className="cockpit-bloco" aria-labelledby="cockpit-funil-titulo">
      <div className="cockpit-bloco-cabeca">
        <h2 id="cockpit-funil-titulo">Do anúncio ao contrato</h2>
        <span>Cada degrau mostra quantos passaram e quanto custou chegar até ali.</span>
      </div>
      <div className="cockpit-funil" role="img" aria-label={`Funil do anúncio ao contrato. ${resumo}.`}>
        {cockpit.funil.map((e, i) => (
          <div key={e.chave} className={`cockpit-funil-linha${e.gargalo ? " cockpit-funil-linha--gargalo" : ""}`}>
            <div className="cockpit-funil-etapa">{ROTULO_ETAPA[e.chave]}</div>
            <div className="cockpit-funil-trilho">
              <div className="cockpit-funil-barra" style={{ width: `${LARGURA[i] ?? 14}%`, background: COR[i] ?? COR[6] }}>
                {inteiro(e.quantidade)}
              </div>
            </div>
            <div className="cockpit-funil-taxa">
              {textoTaxa(e)}
              {e.gargalo ? <span className="cockpit-funil-selo">Maior perda</span> : null}
              {e.taxa != null && e.taxa > 100 ? (
                <small className="cockpit-funil-dica">contagem por evento no período: inclui leads que entraram antes</small>
              ) : null}
            </div>
            <div className="cockpit-funil-custo">{e.custo == null ? "—" : TEXTO_CUSTO[e.chave](moeda(e.custo))}</div>
          </div>
        ))}
      </div>
      {cockpit.fraseGargalo ? (
        <div className="cockpit-gargalo">
          <strong>Maior perda:</strong> {cockpit.fraseGargalo}
        </div>
      ) : null}
    </section>
  );
}
