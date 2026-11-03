import React from "react";

export interface TagResumo {
  tagId: number;
  tagNome: string;
  tagCor: string;
}

interface TagBadgeProps {
  nome: string;
  cor: string;
}

const TagBadge: React.FC<TagBadgeProps> = ({ nome, cor }) => (
  <span className="tag-badge" style={{ "--tag-cor": cor } as React.CSSProperties} title={nome}>
    {nome}
  </span>
);

export default TagBadge;
