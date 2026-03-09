import React from "react";

export interface Column<T> {
  key: keyof T;
  header: string;
  render?: (row: T) => React.ReactNode;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  keyField: keyof T;
  emptyMessage?: string;
}

export function DataTable<T>({ columns, data, keyField, emptyMessage = "Nenhum registro encontrado." }: DataTableProps<T>) {
  if (data.length === 0) {
    return <div className="datatable-empty">{emptyMessage}</div>;
  }

  return (
    <table className="datatable">
      <thead>
        <tr>
          {columns.map((col) => (
            <th key={String(col.key)}>{col.header}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {data.map((row) => (
          <tr key={String(row[keyField])}>
            {columns.map((col) => (
              <td key={String(col.key)}>{col.render ? col.render(row) : (row[col.key] as React.ReactNode)}</td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

