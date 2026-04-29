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

  const imprimirContrato = () => {
    if (!previewHtml) {
      alert("Gere o preview HTML antes de imprimir.");
      return;
    }
    const autoPrintScript = `
<script>
window.addEventListener("load", function () {
  try { window.focus(); } catch (e) {}
  try { window.print(); } catch (e) {}
});
</script>
`;
    const htmlForPrint = previewHtml.includes("</body>")
      ? previewHtml.replace("</body>", `${autoPrintScript}</body>`)
      : `${previewHtml}${autoPrintScript}`;

    const blob = new Blob([htmlForPrint], { type: "text/html;charset=utf-8" });
    const blobUrl = URL.createObjectURL(blob);
    const printWin = window.open(blobUrl, "_blank");
    if (!printWin) {
      URL.revokeObjectURL(blobUrl);
      alert("Não foi possível abrir a janela de impressão. Verifique se o pop-up foi bloqueado.");
      return;
    }
    // Libera o blob depois de algum tempo para não vazar memória.
    window.setTimeout(() => URL.revokeObjectURL(blobUrl), 60_000);
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
          <button type="button" className="btn-primary" onClick={imprimirContrato} disabled={!previewHtml}>
            Imprimir contrato
          </button>
        </div>
        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          <input type="text" readOnly value={publicUrl ?? ""} placeholder="Link público..." />
          <button type="button" className="btn-primary" onClick={() => void copiarLink()} disabled={!publicUrl}>
            Copiar link
          </button>
        </div>
      </div>

      {loadingHtml && <Loader />}

      {previewHtml ? (
        <div style={{ marginTop: 14 }}>
          <h3 className="section-title" style={{ marginTop: 0 }}>
            Preview HTML
          </h3>
          <iframe title="Preview do Contrato" style={{ width: "100%", height: 620, border: "1px solid #e5e7eb", borderRadius: 12 }} srcDoc={previewHtml} />
        </div>
      ) : null}

    </div>
  );
};

export default ContratoPreviewPanel;

