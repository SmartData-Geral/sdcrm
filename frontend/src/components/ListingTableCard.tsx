import React from "react";

interface ListingTableCardProps {
  children: React.ReactNode;
  footer?: React.ReactNode;
}

const ListingTableCard: React.FC<ListingTableCardProps> = ({ children, footer }) => {
  return (
    <section className="listing-table-card">
      <div className="listing-table-content">{children}</div>
      {footer ? <div className="listing-table-footer">{footer}</div> : null}
    </section>
  );
};

export default ListingTableCard;
