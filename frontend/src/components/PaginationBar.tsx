import React, { useMemo } from "react";

interface PaginationBarProps {
  page: number;
  pageSize: number;
  total: number;
  onPageChange: (next: number) => void;
}

function buildPages(current: number, totalPages: number): number[] {
  if (totalPages <= 5) {
    return Array.from({ length: totalPages }, (_, i) => i + 1);
  }
  if (current <= 3) {
    return [1, 2, 3, 4, totalPages];
  }
  if (current >= totalPages - 2) {
    return [1, totalPages - 3, totalPages - 2, totalPages - 1, totalPages];
  }
  return [1, current - 1, current, current + 1, totalPages];
}

const PaginationBar: React.FC<PaginationBarProps> = ({ page, pageSize, total, onPageChange }) => {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const pages = useMemo(() => buildPages(page, totalPages), [page, totalPages]);

  return (
    <div className="pagination pagination--listing">
      <button type="button" disabled={page <= 1} onClick={() => onPageChange(page - 1)}>
        Previous
      </button>
      {pages.map((p, idx) => {
        const prev = pages[idx - 1];
        const showGap = prev != null && p - prev > 1;
        return (
          <React.Fragment key={p}>
            {showGap ? <span className="pagination-gap">...</span> : null}
            <button
              type="button"
              className={`pagination-page${p === page ? " is-active" : ""}`}
              onClick={() => onPageChange(p)}
              aria-current={p === page ? "page" : undefined}
            >
              {p}
            </button>
          </React.Fragment>
        );
      })}
      <button type="button" disabled={page >= totalPages} onClick={() => onPageChange(page + 1)}>
        Next
      </button>
    </div>
  );
};

export default PaginationBar;
