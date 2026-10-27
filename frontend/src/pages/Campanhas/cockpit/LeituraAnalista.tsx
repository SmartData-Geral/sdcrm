import { useEffect, useRef, useState } from "react";
import { useAuth } from "../../../contexts/AuthContext";
import {
  mensagemErroApi,
  type CockpitRecorte,
  type CockpitSelo,
  type MetaAdsCockpitLeitura,
} from "../metaAdsTipos";
import { SeloSaude } from "./SeloSaude";

interface Props {
  recorte: CockpitRecorte;
  selo: CockpitSelo;
  fraseGargalo: string | null;
  onDisponibilidade?: (iaDisponivel: boolean, aviso: string | null) => void;
}

const ROTA = "/meta-ads/cockpit/leitura";

function geradoEmBR(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const dois = (n: number) => String(n).padStart(2, "0");
  return `${dois(d.getDate())}/${dois(d.getMonth() + 1)} ${dois(d.getHours())}:${dois(d.getMinutes())}`;
}

export function LeituraAnalista({ recorte, selo, fraseGargalo, onDisponibilidade }: Props) {
  const { api } = useAuth();
  const [dados, setDados] = useState<MetaAdsCockpitLeitura | null>(null);
  const [gerando, setGerando] = useState(false);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const requisicao = useRef(0);

  const params = {
    data_inicial: recorte.inicio || undefined,
    data_final: recorte.fim || undefined,
    macId: recorte.macId || undefined,
    somente_ativas: recorte.somenteAtivas,
  };

  useEffect(() => {
    const id = ++requisicao.current;
    setCarregando(true);
    setGerando(false);
    setErro(null);
    api
      .get<MetaAdsCockpitLeitura>(ROTA, { params })
      .then((r) => {
        if (id === requisicao.current) setDados(r.data);
      })
      .catch((e) => {
        if (id !== requisicao.current) return;
        setDados(null);
        setErro(mensagemErroApi(e, "Não foi possível carregar a leitura do analista."));
      })
      .finally(() => {
        if (id === requisicao.current) setCarregando(false);
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [api, recorte.inicio, recorte.fim, recorte.macId, recorte.somenteAtivas]);

  const gerar = () => {
    const id = ++requisicao.current;
    setGerando(true);
    setErro(null);
    api
      .post<MetaAdsCockpitLeitura>(ROTA, null, { params })
      .then((r) => {
        if (id === requisicao.current) setDados(r.data);
      })
      .catch((e) => {
        if (id === requisicao.current) setErro(mensagemErroApi(e, "Não foi possível gerar a leitura."));
      })
      .finally(() => {
        if (id === requisicao.current) setGerando(false);
      });
  };

  useEffect(() => {
    if (dados) onDisponibilidade?.(dados.iaDisponivel, dados.aviso);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dados]);

  const temLeitura = !!dados && (dados.leitura != null || !!dados.texto);
  const iaIndisponivel = dados != null && !dados.iaDisponivel;
  const gerado = geradoEmBR(dados?.geradoEm ?? null);

  return (
    <div className="cockpit-analista-leitura" aria-busy={gerando || carregando}>
      <div className="cockpit-analista-cabeca">
        <h2 className="cockpit-analista-titulo">Leitura do analista (IA)</h2>
        <SeloSaude selo={selo} />
      </div>
      {fraseGargalo && <p className="cockpit-analista-gargalo">{fraseGargalo}</p>}

      {dados?.leitura && (
        <>
          <p className="cockpit-analista-manchete">{dados.leitura.manchete}</p>
          <div className="cockpit-analista-blocos">
            <div className="cockpit-analista-bloco">
              <strong className="cockpit-analista-bloco--bom">O que funciona</strong>
              <span>{dados.leitura.funciona}</span>
            </div>
            <div className="cockpit-analista-bloco">
              <strong className="cockpit-analista-bloco--atencao">Onde está o problema</strong>
              <span>{dados.leitura.problema}</span>
            </div>
            <div className="cockpit-analista-bloco">
              <strong className="cockpit-analista-bloco--olhar">O que olhar agora</strong>
              <span>{dados.leitura.olharAgora}</span>
            </div>
          </div>
        </>
      )}
      {!dados?.leitura && dados?.texto && <p className="cockpit-analista-texto">{dados.texto}</p>}
      {dados && !temLeitura && !iaIndisponivel && (
        <p className="cockpit-analista-nota">Ainda não há leitura gerada para este recorte.</p>
      )}

      {temLeitura && (
        <p className="cockpit-analista-nota">
          {gerado && <>Gerada em {gerado}. </>}
          {dados?.desatualizada && <>Atenção: gerada com números anteriores. </>}
          A leitura usa só números agregados e não executa nada na conta.
        </p>
      )}
      {dados?.aviso && (
        <p className="cockpit-analista-nota" role="status">
          {dados.aviso}
        </p>
      )}
      {erro && (
        <p className="cockpit-analista-erro" role="alert">
          {erro}
        </p>
      )}

      <div>
        <button
          type="button"
          className="cockpit-analista-botao"
          onClick={gerar}
          disabled={gerando || carregando || !dados || !dados.iaDisponivel}
        >
          {gerando ? "Gerando..." : temLeitura ? "Gerar de novo" : "Gerar leitura"}
        </button>
      </div>
    </div>
  );
}
