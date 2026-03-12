import React from "react";

interface ListingToolbarProps {
  actions: React.ReactNode;
  filters: React.ReactNode;
  singleRow?: boolean;
}

const ListingToolbar: React.FC<ListingToolbarProps> = ({ actions, filters, singleRow = false }) => {
  return (
    <section className={`listing-toolbar${singleRow ? " listing-toolbar--single-row" : ""}`}>
      <div className="listing-toolbar-actions">{actions}</div>
      <div className="listing-toolbar-filters">{filters}</div>
    </section>
  );
};

export default ListingToolbar;
