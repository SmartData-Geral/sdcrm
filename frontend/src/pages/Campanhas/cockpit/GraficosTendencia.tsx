import { inteiro, moeda, type CockpitPonto, type MetaAdsCockpit } from "../metaAdsTipos";

const L = 540;
const A = 230;
const X0 = 56;
const X1 = 524;
const BASE = 190;
const TOPO = 34;

const moedaCurta = (v: number) => `R$ ${v.toLocaleString("pt-BR", { maximumFractionDigits: 0 })}`;

/** Mostra no máximo ~8 rótulos no eixo, para não sobrepor. */
const passoRotulo = (n: number) => Math.max(1, Math.ceil(n / 8));

function Eixo({ maximo, formato }: { maximo: number; formato: (v: number) => string }) {
  return (
    <>
      <line x1={X0} y1={BASE} x2={X1} y2={BASE} stroke="#cbd5e1" />
      <line x1={X0} y1={TOPO} x2={X1} y2={TOPO} stroke="#e2e8f0" strokeDasharray="3 3" />
      <text x={X0 - 6} y={TOPO + 4} textAnchor="end" fontSize="11" fill="#475569">{formato(maximo)}</text>
      <text x={X0 - 6} y={BASE + 4} textAnchor="end" fontSize="11" fill="#475569">0</text>
    </>
  );
}

function Rotulos({ pontos, slot }: { pontos: CockpitPonto[]; slot: number }) {
  const passo = passoRotulo(pontos.length);
  return (
    <>
      {pontos.map((p, i) =>
        i % passo === 0 ? (
          <text key={p.inicio} x={X0 + slot * i + slot / 2} y={BASE + 18} textAnchor="middle" fontSize="11" fill="#334155">
            {p.rotulo}
          </text>
        ) : null,
      )}
    </>
  );
}

function GraficoInvestimento({ serie }: { serie: CockpitPonto[] }) {
  const n = serie.length;
  const slot = (X1 - X0) / n;
  const larg = Math.min(70, slot * 0.6);
  const maxInv = Math.max(...serie.map((p) => p.investimento), 0) || 1;
  const maxCpl = Math.max(...serie.map((p) => p.cpl ?? 0), 0) || 1;
  const yInv = (v: number) => BASE - (v / maxInv) * (BASE - TOPO);
  const yCpl = (v: number) => BASE - (v / maxCpl) * (BASE - TOPO);
  const cx = (i: number) => X0 + slot * i + slot / 2;

  // A linha do CPL quebra onde não há CPL (sem lead no intervalo).
  const trechos: string[][] = [];
  let atual: string[] = [];
  serie.forEach((p, i) => {
    if (p.cpl == null) {
      if (atual.length) trechos.push(atual);
      atual = [];
    } else {
      atual.push(`${cx(i)},${yCpl(p.cpl)}`);
    }
  });
  if (atual.length) trechos.push(atual);

  const resumo = serie
    .map((p) => `${p.rotulo}: investimento ${moeda(p.investimento)}, CPL ${moeda(p.cpl)}`)
    .join("; ");

  return (
    <svg viewBox={`0 0 ${L} ${A}`} role="img" aria-label={`Investimento e custo por lead por intervalo. ${resumo}.`} className="cockpit-grafico">
      <Eixo maximo={maxInv} formato={moedaCurta} />
      {serie.map((p, i) => (
        <rect
          key={p.inicio}
          tabIndex={0}
          x={cx(i) - larg / 2}
          y={yInv(p.investimento)}
          width={larg}
          height={BASE - yInv(p.investimento)}
          rx={4}
          fill="#93c5fd"
          className="cockpit-grafico-foco"
        >
          <title>{`${p.rotulo}: investimento ${moeda(p.investimento)}`}</title>
        </rect>
      ))}
      {trechos.map((t, i) => (
        <polyline key={i} points={t.join(" ")} fill="none" stroke="#c2410c" strokeWidth={3} />
      ))}
      {serie.map((p, i) =>
        p.cpl == null ? null : (
          <circle key={p.inicio} tabIndex={0} cx={cx(i)} cy={yCpl(p.cpl)} r={5} fill="#c2410c" className="cockpit-grafico-foco">
            <title>{`${p.rotulo}: CPL ${moeda(p.cpl)}`}</title>
          </circle>
        ),
      )}
      {n <= 8
        ? serie.map((p, i) =>
            p.cpl == null ? null : (
              <text key={p.inicio} x={cx(i)} y={yCpl(p.cpl) - 10} textAnchor="middle" fontSize="11" fontWeight="600" fill="#9a3412">
                {moeda(p.cpl)}
              </text>
            ),
          )
        : null}
      <Rotulos pontos={serie} slot={slot} />
    </svg>
  );
}

function GraficoLeads({ serie }: { serie: CockpitPonto[] }) {
  const n = serie.length;
  const slot = (X1 - X0) / n;
  const larg = Math.min(30, slot * 0.34);
  const maximo = Math.max(...serie.flatMap((p) => [p.leadsMeta, p.leadsCrm]), 0) || 1;
  const y = (v: number) => BASE - (v / maximo) * (BASE - TOPO);
  const c = (i: number) => X0 + slot * i + slot / 2;
  const resumo = serie.map((p) => `${p.rotulo}: Meta ${inteiro(p.leadsMeta)}, CRM ${inteiro(p.leadsCrm)}`).join("; ");

  return (
    <svg viewBox={`0 0 ${L} ${A}`} role="img" aria-label={`Leads da Meta e leads no CRM por intervalo. ${resumo}.`} className="cockpit-grafico">
      <Eixo maximo={maximo} formato={(v) => inteiro(Math.round(v))} />
      {serie.map((p, i) => (
        <g key={p.inicio}>
          <rect tabIndex={0} x={c(i) - larg - 1} y={y(p.leadsMeta)} width={larg} height={BASE - y(p.leadsMeta)} rx={3} fill="#1d4ed8" className="cockpit-grafico-foco">
            <title>{`${p.rotulo}: ${inteiro(p.leadsMeta)} leads na Meta`}</title>
          </rect>
          <rect tabIndex={0} x={c(i) + 1} y={y(p.leadsCrm)} width={larg} height={BASE - y(p.leadsCrm)} rx={3} fill="#93c5fd" className="cockpit-grafico-foco">
            <title>{`${p.rotulo}: ${inteiro(p.leadsCrm)} leads no CRM`}</title>
          </rect>
          {n <= 8 ? (
            <>
              <text x={c(i) - larg / 2 - 1} y={y(p.leadsMeta) - 5} textAnchor="middle" fontSize="11" fill="#0f172a">{inteiro(p.leadsMeta)}</text>
              <text x={c(i) + larg / 2 + 1} y={y(p.leadsCrm) - 5} textAnchor="middle" fontSize="11" fill="#0f172a">{inteiro(p.leadsCrm)}</text>
            </>
          ) : null}
        </g>
      ))}
      <Rotulos pontos={serie} slot={slot} />
    </svg>
  );
}

export function GraficosTendencia({ cockpit }: { cockpit: MetaAdsCockpit }) {
  const porSemana = cockpit.intervalo === "semana";
  const unidade = porSemana ? "semana" : "mês";
  const vazio = cockpit.serie.length === 0;
  return (
    <section className="cockpit-graficos">
      <div className="cockpit-bloco">
        <h2>{`Investimento e custo por lead, por ${unidade}`}</h2>
        <span className="cockpit-bloco-sub">Barras: quanto foi investido. Linha: quanto custou cada lead.</span>
        {vazio ? <p className="cockpit-vazio">Sem investimento nem leads no período.</p> : <GraficoInvestimento serie={cockpit.serie} />}
        <div className="cockpit-legenda">
          <span><i className="cockpit-legenda-cor" style={{ background: "#93c5fd" }} /> Investimento</span>
          <span><i className="cockpit-legenda-cor" style={{ background: "#c2410c" }} /> Custo por lead</span>
        </div>
      </div>
      <div className="cockpit-bloco">
        <h2>{`Leads por ${unidade}: Meta x CRM`}</h2>
        <span className="cockpit-bloco-sub">Azul-escuro: leads que a Meta contou. Claro: os que chegaram ao CRM.</span>
        {vazio ? <p className="cockpit-vazio">Sem investimento nem leads no período.</p> : <GraficoLeads serie={cockpit.serie} />}
        <div className="cockpit-legenda">
          <span><i className="cockpit-legenda-cor" style={{ background: "#1d4ed8" }} /> Leads na Meta</span>
          <span><i className="cockpit-legenda-cor" style={{ background: "#93c5fd" }} /> Leads no CRM</span>
        </div>
      </div>
    </section>
  );
}
