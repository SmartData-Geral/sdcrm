import { useEffect, useRef, useState, type FormEvent } from "react";
import { useAuth } from "../../../contexts/AuthContext";
import {
  mensagemErroApi,
  type CockpitRecorte,
  type CockpitTroca,
  type MetaAdsCockpitResposta,
} from "../metaAdsTipos";

interface Props {
  recorte: CockpitRecorte;
  iaDisponivel: boolean;
  aviso: string | null;
}

const SUGESTOES = ["Qual criativo devo escalar?", "Por que o custo por lead mudou?", "Onde perco mais leads no funil?"];
const MAX_PERGUNTA = 500;
const MAX_TROCAS_HISTORICO = 6;

export function PergunteAnalista({ recorte, iaDisponivel, aviso }: Props) {
  const { api } = useAuth();
  const [texto, setTexto] = useState("");
  const [trocas, setTrocas] = useState<CockpitTroca[]>([]);
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [restantes, setRestantes] = useState<number | null>(null);
  const requisicao = useRef(0);

  // A conversa pertence ao recorte: muda o recorte, zera.
  useEffect(() => {
    requisicao.current += 1;
    setTrocas([]);
    setTexto("");
    setErro(null);
    setEnviando(false);
  }, [recorte.inicio, recorte.fim, recorte.macId, recorte.somenteAtivas]);

  const perguntar = (pergunta: string) => {
    const limpa = pergunta.trim();
    if (!limpa || enviando) return;
    const id = ++requisicao.current;
    const historico = trocas.slice(-MAX_TROCAS_HISTORICO).flatMap((t) => [
      { papel: "pergunta", texto: t.pergunta },
      { papel: "resposta", texto: t.resposta },
    ]);
    setEnviando(true);
    setErro(null);
    api
      .post<MetaAdsCockpitResposta>("/meta-ads/cockpit/perguntar", {
        dataInicial: recorte.inicio,
        dataFinal: recorte.fim,
        macId: recorte.macId ? Number(recorte.macId) : null,
        somenteAtivas: recorte.somenteAtivas,
        pergunta: limpa,
        historico,
      })
      .then((r) => {
        if (id !== requisicao.current) return;
        setTrocas((atual) => [...atual, { pergunta: limpa, resposta: r.data.resposta }]);
        setRestantes(r.data.restantesHoje);
        setTexto("");
      })
      .catch((e) => {
        if (id !== requisicao.current) return;
        setErro(
          e?.response?.status === 429
            ? "Limite de perguntas de hoje atingido."
            : mensagemErroApi(e, "Não foi possível obter a resposta do analista."),
        );
      })
      .finally(() => {
        if (id === requisicao.current) setEnviando(false);
      });
  };

  const enviar = (e: FormEvent) => {
    e.preventDefault();
    perguntar(texto);
  };

  return (
    <div className="cockpit-analista-chat">
      <h2 className="cockpit-analista-chat-titulo">Pergunte ao analista</h2>
      {!iaDisponivel ? (
        <p className="cockpit-analista-nota">{aviso ?? "A leitura por IA não está disponível no momento."}</p>
      ) : (
        <>
          <div className="cockpit-analista-sugestoes">
            {SUGESTOES.map((s) => (
              <button key={s} type="button" className="cockpit-analista-sugestao" disabled={enviando} onClick={() => perguntar(s)}>
                {s}
              </button>
            ))}
          </div>

          {trocas.length > 0 && (
            <ol className="cockpit-analista-conversa" aria-label="Conversa com o analista">
              {trocas.map((t, i) => (
                <li key={i}>
                  <p className="cockpit-analista-pergunta">
                    <span className="cockpit-analista-quem">Você</span> {t.pergunta}
                  </p>
                  <p className="cockpit-analista-resposta">
                    <span className="cockpit-analista-quem">Analista</span> {t.resposta}
                  </p>
                </li>
              ))}
            </ol>
          )}
          <div aria-live="polite">{enviando && <p className="cockpit-analista-nota">O analista está respondendo...</p>}</div>

          <form className="cockpit-analista-form" onSubmit={enviar}>
            <label htmlFor="cockpit-pergunta">Sua pergunta</label>
            <textarea
              id="cockpit-pergunta"
              rows={2}
              maxLength={MAX_PERGUNTA}
              value={texto}
              placeholder="Ex.: comparar setembro com outubro"
              onChange={(e) => setTexto(e.target.value)}
            />
            <div className="cockpit-analista-form-rodape">
              <span className="cockpit-analista-nota">
                {texto.length}/{MAX_PERGUNTA}
                {restantes != null && (
                  <>
                    {" "}
                    · Restam {restantes} {restantes === 1 ? "pergunta" : "perguntas"} hoje
                  </>
                )}
              </span>
              <button type="submit" className="cockpit-analista-botao" disabled={enviando || !texto.trim()}>
                Enviar
              </button>
            </div>
          </form>
          {erro && (
            <p className="cockpit-analista-erro" role="alert">
              {erro}
            </p>
          )}
        </>
      )}
    </div>
  );
}
