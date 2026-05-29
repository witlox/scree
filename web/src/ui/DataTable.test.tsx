import type { ColumnDef } from "@tanstack/react-table";
import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { DataTable } from "./DataTable";

interface Row {
  name: string;
  n: number;
}
const columns: ColumnDef<Row>[] = [
  { accessorKey: "name", header: "Name" },
  { accessorKey: "n", header: "N" },
];
const data: Row[] = [
  { name: "beta", n: 2 },
  { name: "alpha", n: 1 },
];

afterEach(() => {
  document.body.innerHTML = "";
});

describe("DataTable", () => {
  it("renders rows in a real table with a caption", () => {
    render(<DataTable caption="Things" columns={columns} data={data} />);
    expect(screen.getByRole("table", { name: "Things" })).toBeInTheDocument();
    expect(screen.getAllByRole("row")).toHaveLength(3); // header + 2 data rows
  });

  it("sorts when a column header is activated (aria-sort reflects state)", () => {
    render(<DataTable caption="Things" columns={columns} data={data} />);
    const header = screen.getByRole("button", { name: /Name/ });
    fireEvent.click(header);
    const nameHeader = screen.getByRole("columnheader", { name: /Name/ });
    expect(nameHeader).toHaveAttribute("aria-sort", "ascending");
    // first data row is now "alpha" (ascending)
    const firstDataRow = screen.getAllByRole("row")[1];
    expect(firstDataRow).toHaveTextContent("alpha");
  });
});
