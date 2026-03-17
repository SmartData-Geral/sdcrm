import React from "react";
import { getStaticBaseUrl } from "../../utils/api";

interface Props {
  token: string;
  /** Quando true, a URL usa ?preview=1 e o backend retorna HTML atual (último salvo) sem publicar */
  isPreview?: boolean;
}

const ProposalPublicPage: React.FC<Props> = ({ token, isPreview = false }) => {
  const base = `${getStaticBaseUrl()}/public/propostas/${token}`;
  const src = isPreview ? `${base}?preview=1` : base;
  return (
    <div className="proposal-public-wrapper">
      <iframe title="Página pública da proposta" src={src} className="proposal-public-iframe" />
    </div>
  );
};

export default ProposalPublicPage;

