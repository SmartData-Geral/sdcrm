import React, { useState } from "react";
import { useAuth } from "../../contexts/AuthContext";
import { getPublicContractUrl } from "../../utils/api";

import Loader from "../Loader";

type Props = {
  contratoId: number;
  tokenPublico: string | null | undefined;
};

const ContratoPreviewPanel: React.FC<Props> = ({ contratoId, tokenPublico }) => {
  const { api } = useAuth();

  const [previewHtml, setPreviewHtml] = useState<string | null>(null);
  const [loadingHtml, setLoadingHtml] = useState(false);
  const [loadingPdf, setLoadingPdf] = useState(false);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);

  const publicUrl = tokenPublico ? getPublicContractUrl(tokenPublico) : null;

  const gerarHtml = async () => {
    setLoadingHtml(true);
    try {
      const res = await api.post<string>(`/contratos/${contratoId}/gerar-html`, undefined);
      setPreviewHtml(res.data);
    } finally {
      setLoadingHtml(false);
    }
  };

  const gerarPdf = async () => {
    setLoadingPdf(true);
    try {
      const res = await api.post<{ pdfUrl: string }>(`/contratos/${contratoId}/gerar-pdf`);
      setPdfUrl(res.data.pdfUrl);
    } finally {
      setLoadingPdf(false);
    }
  };

  const copiarLink = async () => {
    if (!publicUrl) return;
    await navigator.clipboard.writeText(publicUrl);
    alert("Link público copiado para a área de transferência.");
  };

  return (
    <div style={{ marginTop: "1rem" }}>
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          <button type="button" className="btn-primary" onClick={() => void gerarHtml()} disabled={loadingHtml}>
            {loadingHtml ? "Gerando HTML..." : "Gerar preview HTML"}
          </button>
          <button type="button" className="btn-primary" onClick={() => void gerarPdf()} disabled={loadingPdf}>
            {loadingPdf ? "Gerando PDF..." : "Gerar PDF"}
          </button>
        </div>
        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          <input type="text" readOnly value={publicUrl ?? ""} placeholder="Link público..." />
          <button type="button" className="btn-primary" onClick={() => void copiarLink()} disabled={!publicUrl}>
            Copiar link
          </button>
        </div>
      </div>

      {(loadingHtml || loadingPdf) && <Loader />}

      {previewHtml ? (
        <div style={{ marginTop: 14 }}>
          <h3 className="section-title" style={{ marginTop: 0 }}>
            Preview HTML
          </h3>
          <iframe title="Preview do Contrato" style={{ width: "100%", height: 620, border: "1px solid #e5e7eb", borderRadius: 12 }} srcDoc={previewHtml} />
        </div>
      ) : null}

      {pdfUrl ? (
        <div style={{ marginTop: 14 }}>
          <h3 className="section-title" style={{ marginTop: 0 }}>
            PDF
          </h3>
          <a href={pdfUrl} target="_blank" rel="noopener" className="btn-primary">
            Abrir PDF
          </a>
        </div>
      ) : null}
    </div>
  );
};

export default ContratoPreviewPanel;

