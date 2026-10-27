import { moeda, percentual, type CockpitCriativo, type CockpitMetas, type CockpitQuadrante, type MetaAdsCockpit } from "../metaAdsTipos";

const W = 640;
const H = 360;
const FAIXA = 100; // largura da faixa "sem lead" à direita
const X_MIN = 40;
const X_MAX = W - FAIXA - 30;

export const COR_QUADRANTE: Record<CockpitQuadrante, string> = {
  escalar: "#0f766e",
  otimizar_custo: "#1d4ed8",
  rever_publico: "#b45309",
  pausar: "#b91c1c",
  aguardar_dados: "#64748b",
};

const nomeCurto = (nome: string) => (nome.length > 20 ? `${nome.slice(0, 19)}…` : nome);

interface Bolha {
  c: CockpitCriativo;
  x: number;
  y: number;
  d: number;
}

const diametro = (investimento: number) => Math.round(14 + Math.sqrt(Math.max(investimento, 0)) / 1.6);

function dica(c: CockpitCriativo) {
  const partes = [
    c.nome,
    `Investido ${moeda(c.investimento)}`,
    `CPL ${moeda(c.cpl)}`,
    `Taxa de MQL ${percentual(c.taxaMql)}`,
    c.recomendacao,
  ];
  if (c.amostraPequena) partes.push("amostra pequena: menos de 5 leads no CRM");
  return partes.join(" · ");
}

function posicionar(cockpit: MetaAdsCockpit, metas: CockpitMetas) {
  const comPonto = cockpit.criativos.filter(
    (c) => c.quadrante !== "aguardar_dados" && c.cpl != null && c.taxaMql != null,
  );
  const semLead = cockpit.criativos.filter((c) => c.quadrante === "pausar" && c.motivo === "sem_lead");

  const maxX = Math.max(metas.cpl * 2, ...comPonto.map((c) => c.cpl as number)) || 1;
  const maxY = Math.min(100, Math.max(metas.taxaMql * 2, ...comPonto.map((c) => c.taxaMql as number))) || 1;
  const px = (cpl: number) => X_MIN + (Math.min(cpl, maxX) / maxX) * (X_MAX - X_MIN);
  const py = (t: number) => H - 30 - (Math.min(t, maxY) / maxY) * (H - 70);

  // Os maiores primeiro; cada colisão com um já colocado empurra 8px para baixo.
  const bolhas: Bolha[] = [];
  [...comPonto]
    .sort((a, b) => b.investimento - a.investimento)
    .forEach((c) => {
      const d = diametro(c.investimento);
      const x = px(c.cpl as number);
      const y0 = py(c.taxaMql as number);
      const colisoes = bolhas.filter(
        (o) => Math.abs(o.x - x) < (o.d + d) / 2 && Math.abs(o.y - y0) < (o.d + d) / 2,
      ).length;
      bolhas.push({ c, x, y: Math.min(y0 + colisoes * 8, H - 8), d });
    });

  const faixa: Bolha[] = [...semLead]
    .sort((a, b) => b.investimento - a.investimento)
    .map((c, i) => ({ c, x: W - FAIXA / 2, y: 60 + i * 34, d: diametro(c.investimento) }));

  return { bolhas, faixa, linhaX: px(metas.cpl), linhaY: py(metas.taxaMql) };
}

function BolhaItem({ b }: { b: Bolha }) {
  const cor = COR_QUADRANTE[b.c.quadrante];
  const rotulo = `${dica(b.c)}`;
  return (
    <>
      <div
        tabIndex={0}
        role="img"
        aria-label={rotulo}
        title={rotulo}
        className={`cockpit-bolha${b.c.amostraPequena ? " cockpit-bolha--amostra" : ""}`}
        style={{ left: b.x, top: b.y, width: b.d, height: b.d, marginLeft: -b.d / 2, marginTop: -b.d / 2, background: cor, borderColor: cor }}
      />
      <span className="cockpit-bolha-rotulo" style={{ left: b.x + b.d / 2 + 4, top: b.y - 8 }}>
        {nomeCurto(b.c.nome)}
      </span>
    </>
  );
}

export function MatrizCriativos({ cockpit, metas }: { cockpit: MetaAdsCockpit; metas: CockpitMetas }) {
  const { bolhas, faixa, linhaX, linhaY } = posicionar(cockpit, metas);
  const escalar = cockpit.criativos.filter((c) => c.quadrante === "escalar");
  const aguardando = cockpit.criativos.filter((c) => c.quadrante === "aguardar_dados").length;
  const resumo = [...bolhas, ...faixa].map((b) => dica(b.c)).join("; ");

  return (
    <section className="cockpit-bloco" aria-labelledby="cockpit-matriz-titulo">
      <div className="cockpit-bloco-cabeca">
        <h2 id="cockpit-matriz-titulo">Matriz de decisão dos criativos</h2>
        <span>Para a direita: lead mais caro. Para cima: mais leads viram MQL. Tamanho: quanto já foi investido.</span>
      </div>
      <div className="cockpit-matriz-layout">
        <div className="cockpit-matriz-scroll">
          <div
            className="cockpit-matriz"
            role="group"
            aria-label={bolhas.length + faixa.length ? `Matriz de criativos. ${resumo}.` : "Matriz de criativos sem anúncios para posicionar."}
            style={{ width: W, height: H }}
          >
            <div className="cockpit-matriz-meta cockpit-matriz-meta--v" style={{ left: linhaX }} />
            <div className="cockpit-matriz-meta cockpit-matriz-meta--h" style={{ top: linhaY, right: FAIXA }} />
            <div className="cockpit-matriz-faixa" style={{ width: FAIXA }}>
              <span>sem lead</span>
            </div>
            <span className="cockpit-matriz-q" style={{ left: 12, top: 10, color: COR_QUADRANTE.escalar }}>ESCALAR · barato e qualificado</span>
            <span className="cockpit-matriz-q" style={{ right: FAIXA + 12, top: 10, color: COR_QUADRANTE.otimizar_custo }}>OTIMIZAR CUSTO · caro, mas qualifica</span>
            <span className="cockpit-matriz-q" style={{ left: 12, bottom: 10, color: COR_QUADRANTE.rever_publico }}>REVER PÚBLICO · barato, pouco qualificado</span>
            <span className="cockpit-matriz-q" style={{ right: FAIXA + 12, bottom: 10, color: COR_QUADRANTE.pausar }}>PAUSAR · caro e sem qualificação</span>
            {bolhas.map((b) => <BolhaItem key={`${b.c.id ?? b.c.nome}-${b.c.mcgId ?? ""}`} b={b} />)}
            {faixa.map((b) => (
              <div key={`f-${b.c.id ?? b.c.nome}-${b.c.mcgId ?? ""}`}>
                <div
                  tabIndex={0}
                  role="img"
                  aria-label={dica(b.c)}
                  title={dica(b.c)}
                  className={`cockpit-bolha${b.c.amostraPequena ? " cockpit-bolha--amostra" : ""}`}
                  style={{ left: W - FAIXA + 22, top: b.y, width: 14, height: 14, marginLeft: 0, marginTop: -7, background: COR_QUADRANTE.pausar, borderColor: COR_QUADRANTE.pausar }}
                />
                <span className="cockpit-bolha-rotulo cockpit-bolha-rotulo--faixa" style={{ left: W - FAIXA + 36, top: b.y - 8 }}>
                  {b.c.nome}
                </span>
              </div>
            ))}
          </div>
        </div>
        <div className="cockpit-como-ler">
          <strong>Como ler</strong>
          <span>
            As linhas tracejadas são as metas: <strong>CPL de {moeda(metas.cpl)}</strong> e{" "}
            <strong>{metas.taxaMql.toLocaleString("pt-BR")}% dos leads virando MQL</strong>. Elas ficam na configuração do monitoramento.
          </span>
          <span>
            {escalar.length
              ? `${escalar.length} criativo(s) no quadrante Escalar: ${escalar.map((c) => c.nome).join(", ")}.`
              : "Hoje nenhum criativo está no quadrante Escalar."}
          </span>
          <span>A faixa à direita reúne anúncios que gastaram sem gerar nenhum lead (sem CPL para posicionar).</span>
          {aguardando ? <span>{aguardando} anúncio(s) aguardam dados e aparecem só na tabela.</span> : null}
          <span className="cockpit-como-ler-nota">
            Borda tracejada: amostra pequena (menos de 5 leads no CRM). Um único MQL muda a posição do criativo.
          </span>
        </div>
      </div>
    </section>
  );
}
