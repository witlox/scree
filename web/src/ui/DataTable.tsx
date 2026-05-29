import {
  type ColumnDef,
  type SortingState,
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
} from "@tanstack/react-table";
import { useState } from "react";

/** Accessible, sortable table on TanStack Table (ADR-0011). Headless engine, our
 *  markup/tokens: real <table> with <caption>, scope="col", aria-sort, and a button
 *  to toggle sort (keyboard-operable). */
export function DataTable<T>({
  columns,
  data,
  caption,
}: {
  columns: ColumnDef<T>[];
  data: T[];
  caption: string;
}) {
  const [sorting, setSorting] = useState<SortingState>([]);
  const table = useReactTable({
    data,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  return (
    <table className="data-table">
      <caption className="sr-only">{caption}</caption>
      <thead>
        {table.getHeaderGroups().map((hg) => (
          <tr key={hg.id}>
            {hg.headers.map((h) => {
              const sorted = h.column.getIsSorted();
              const ariaSort = sorted === "asc" ? "ascending" : sorted === "desc" ? "descending" : "none";
              return (
                <th key={h.id} scope="col" aria-sort={ariaSort}>
                  {h.column.getCanSort() ? (
                    <button type="button" className="data-table__sort" onClick={h.column.getToggleSortingHandler()}>
                      {flexRender(h.column.columnDef.header, h.getContext())}
                      <span aria-hidden="true">{sorted === "asc" ? " ▲" : sorted === "desc" ? " ▼" : ""}</span>
                    </button>
                  ) : (
                    flexRender(h.column.columnDef.header, h.getContext())
                  )}
                </th>
              );
            })}
          </tr>
        ))}
      </thead>
      <tbody>
        {table.getRowModel().rows.map((row) => (
          <tr key={row.id}>
            {row.getVisibleCells().map((cell) => (
              <td key={cell.id}>{flexRender(cell.column.columnDef.cell, cell.getContext())}</td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
