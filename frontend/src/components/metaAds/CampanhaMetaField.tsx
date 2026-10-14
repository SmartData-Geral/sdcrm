import React, { useEffect, useState } from "react";
import { useAuth } from "../../contexts/AuthContext";

interface Opcao {
  mcgId: number;
  nome: string;
  conta: string;
  status: string | null;
}

const CampanhaMetaField: React.FC<{
  opoId: number;
  opoMcgId: number | null;
  opoMcgManual: boolean;
  onSalvo: () => void;
}> = ({ opoId, opoMcgId, opoMcgManual, onSalvo }) => {
  const { api } = useAuth();
  const [opcoes, setOpcoes] = useState<Opcao[] | null>(null);
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState(false);

  useEffect(() => {
    api
      .get<{ items: Opcao[] }>("/meta-ads/campanhas-opcoes")
      .then((r) => setOpcoes(r.data.items ?? []))
      .catch(() => setOpcoes([]));
  }, [api]);

  if (opcoes === null || (opcoes.length === 0 && opoMcgId == null)) return null;

  const salvar = async (valor: string) => {
    setErro(false);
    setSalvando(true);
    try {
      await api.patch(`/meta-ads/oportunidades/${opoId}/campanha`, { opoMcgId: valor ? Number(valor) : null });
      onSalvo();
    } catch {
      setErro(true);
    } finally {
      setSalvando(false);
    }
  };

  return (
    <div className="info-item">
      <span className="info-label">Campanha Meta</span>
      <select
        className="detail-inline-input"
        value={opoMcgId ?? ""}
        disabled={salvando}
        onChange={(e) => void salvar(e.target.value)}
      >
        <option value="">Nenhuma</option>
        {opcoes.map((o) => (
          <option key={o.mcgId} value={o.mcgId}>
            {o.nome}
            {o.status && o.status !== "ACTIVE" ? " (inativa)" : ""}
          </option>
        ))}
      </select>
      {opoMcgId != null && !opoMcgManual ? <span className="field-hint">Vinculada automaticamente</span> : null}
      {erro ? (
        <span className="field-hint" role="alert">
          Não foi possível salvar a campanha.
        </span>
      ) : null}
    </div>
  );
};

export default CampanhaMetaField;
