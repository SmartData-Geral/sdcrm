import React, { useEffect, useState } from "react";
import Layout from "../../components/Layout";

const DashboardPage: React.FC = () => {
  const [faviconPreview, setFaviconPreview] = useState<string | null>(null);

  useEffect(() => {
    return () => {
      if (faviconPreview) {
        URL.revokeObjectURL(faviconPreview);
      }
    };
  }, [faviconPreview]);

  const handleFaviconChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    if (faviconPreview) {
      URL.revokeObjectURL(faviconPreview);
    }
    setFaviconPreview(URL.createObjectURL(file));
  };

  return (
    <Layout>
      <section className="dashboard-grid">
        <article className="surface-card">
          <h2>Visao geral</h2>
          <p>Base inicial pronta para os novos projetos, com foco em navegacao lateral e componentes padronizados.</p>
        </article>

        <article className="surface-card">
          <h2>Branding do sistema</h2>
          <p>
            O favicon do sistema deve ficar em <code>frontend/public/assets/branding/favicon.svg</code> ou{" "}
            <code>favicon.ico</code>.
          </p>
          <label className="upload-field">
            Simular upload de favicon
            <input type="file" accept=".ico,.png,.svg,image/x-icon,image/png,image/svg+xml" onChange={handleFaviconChange} />
          </label>
          {faviconPreview && <img className="favicon-preview" src={faviconPreview} alt="Preview de favicon" />}
        </article>
      </section>
    </Layout>
  );
};

export default DashboardPage;

