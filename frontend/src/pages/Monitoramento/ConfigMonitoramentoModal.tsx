import React, { useEffect, useState } from "react";
import Modal from "../../components/Modal";
import { useAuth } from "../../contexts/AuthContext";
import { MonitorConfig, mensagemErroApi } from "../Campanhas/metaAdsTipos";

interface Etapa {
  etkId: number;
  etkNome: string;
  etkOrdem: number;
}

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onSaved: () => void;
}

const ALERTAS: [string, string][] = [
  ["cpl", "CPL fora do padrão"],
  ["gasto", "Gasto sem retorno"],
  ["frequencia", "Criativo saturando"],
  ["ctr", "Queda de CTR"],
  ["parado", "Anúncio parado"],
  ["semContato", "Lead sem contato"],
];

type CampoNumerico = Exclude<keyof MonitorConfig, "etapaMqlId" | "etapaOportunidadeId" | "alertas">;

const ConfigMonitoramentoModal: React.FC<Props> = ({ isOpen, onClose, onSaved }) => {
  const { api } = useAuth();
  const [config, setConfig] = useState<MonitorConfig | null>(null);
  const [etapas, setEtapas] = useState<Etapa[]>([]);
  const [carregando, setCarregando] = useState(false);
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen) return;
    let ativo = true;
    setCarregando(true);
    setErro(null);
    setConfig(null);
    Promise.all([
      api.get<MonitorConfig>("/meta-ads/monitoramento/config"),
      api.get<{ items: Etapa[] }>("/etapas-kanban", {
        params: { pipeline: "default", status: "ativos", page_size: 100 },
      }),
    ])
      .then(([c, e]) => {
        if (!ativo) return;
        setConfig(c.data);
        setEtapas([...(e.data.items ?? [])].sort((a, b) => a.etkOrdem - b.etkOrdem));
      })
      .catch((err) => {
        if (ativo) setErro(mensagemErroApi(err, "Não foi possível carregar a configuração."));
      })
      .finally(() => {
        if (ativo) setCarregando(false);
      });
    return () => {
      ativo = false;
    };
  }, [api, isOpen]);

  const salvar = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!config) return;
    setSalvando(true);
    setErro(null);
    try {
      await api.put("/meta-ads/monitoramento/config", config);
      onSaved();
      onClose();
    } catch (err: any) {
      setErro(mensagemErroApi(err, "Não foi possível salvar a configuração."));
    } finally {
      setSalvando(false);
    }
  };

  const seletorEtapa = (campo: "etapaMqlId" | "etapaOportunidadeId", rotulo: string) => (
    <label>
      {rotulo}
      <select
        value={config?.[campo] ?? ""}
        onChange={(e) =>
          setConfig((c) => (c ? { ...c, [campo]: e.target.value ? Number(e.target.value) : null } : c))
        }
        disabled={salvando}
      >
        <option value="">Não definida</option>
        {etapas.map((et) => (
          <option key={et.etkId} value={et.etkId}>
            {et.etkNome}
          </option>
        ))}
      </select>
    </label>
  );

  const campoNumero = (campo: CampoNumerico, rotulo: string, step = "1", dica?: string) => (
    <label>
      {rotulo}
      <input
        type="number"
        min="0"
        step={step}
        value={config ? String(config[campo]) : ""}
        onChange={(e) => setConfig((c) => (c ? { ...c, [campo]: e.target.value === "" ? 0 : Number(e.target.value) } : c))}
        disabled={salvando}
        required
      />
      {dica ? <span className="field-hint">{dica}</span> : null}
    </label>
  );

  return (
    <Modal isOpen={isOpen} title="Configurar monitoramento" onClose={() => !salvando && onClose()}>
      {erro ? (
        <div className="integracao-erro" role="alert">
          {erro}
        </div>
      ) : null}
      {carregando ? <p className="muted-text">Carregando…</p> : null}
      {config ? (
        <form onSubmit={(e) => void salvar(e)}>
          {seletorEtapa("etapaMqlId", "Etapa que conta como MQL")}
          {seletorEtapa("etapaOportunidadeId", "Etapa que conta como oportunidade")}
          {campoNumero("cplFator", "Fator do CPL (alerta acima de N× a média)", "0.1")}
          {campoNumero("gastoSemLead", "Gasto sem lead (R$)")}
          {campoNumero("frequenciaMax", "Frequência máxima", "0.1")}
          {campoNumero("quedaCtrPct", "Queda de CTR (%)")}
          {campoNumero("horasSemContato", "Horas sem contato")}
          {campoNumero("gastoMinRanking", "Gasto mínimo para entrar no ranking (R$)")}
          {campoNumero("horaResumo", "Hora do resumo diário (0–23)", "1", "Horário de Brasília, em dias úteis.")}
          <fieldset className="integracao-escopos">
            <legend>Alertas ativos</legend>
            {ALERTAS.map(([chave, rotulo]) => (
              <label key={chave} className="checkbox-inline">
                <input
                  type="checkbox"
                  checked={config.alertas[chave] ?? false}
                  onChange={(e) =>
                    setConfig((c) => (c ? { ...c, alertas: { ...c.alertas, [chave]: e.target.checked } } : c))
                  }
                  disabled={salvando}
                />
                {rotulo}
              </label>
            ))}
          </fieldset>
          <div className="modal-actions">
            <button type="button" onClick={onClose} disabled={salvando}>
              Cancelar
            </button>
            <button type="submit" className="primary" disabled={salvando}>
              {salvando ? "Salvando…" : "Salvar"}
            </button>
          </div>
        </form>
      ) : null}
    </Modal>
  );
};

export default ConfigMonitoramentoModal;
