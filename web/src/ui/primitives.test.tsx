import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { useState } from "react";
import { afterEach, describe, expect, it } from "vitest";

import { Button } from "./Button";
import { Dialog } from "./Dialog";
import { TextField } from "./TextField";

afterEach(() => {
  document.body.innerHTML = "";
});

describe("Button", () => {
  it("is a real button defaulting to type=button", () => {
    render(<Button>Save</Button>);
    expect(screen.getByRole("button", { name: "Save" })).toHaveAttribute("type", "button");
  });
});

describe("TextField", () => {
  it("associates the label and exposes the error accessibly", () => {
    render(<TextField label="Title" error="Required" defaultValue="" />);
    const input = screen.getByLabelText("Title");
    expect(input).toHaveAttribute("aria-invalid", "true");
    const error = screen.getByRole("alert");
    expect(input).toHaveAttribute("aria-describedby", error.id);
  });

  it("has no error wiring when valid", () => {
    render(<TextField label="Title" />);
    expect(screen.getByLabelText("Title")).not.toHaveAttribute("aria-invalid");
    expect(screen.queryByRole("alert")).toBeNull();
  });
});

describe("Dialog", () => {
  it("opens from its trigger as an accessible modal and closes on Escape", async () => {
    function Harness() {
      const [open, setOpen] = useState(false);
      return (
        <Dialog open={open} onOpenChange={setOpen} title="Confirm" trigger={<Button>Open</Button>}>
          <p>Body</p>
        </Dialog>
      );
    }
    render(<Harness />);
    fireEvent.click(screen.getByRole("button", { name: "Open" }));
    const dialog = await screen.findByRole("dialog");
    expect(dialog).toHaveAccessibleName("Confirm");
    fireEvent.keyDown(document, { key: "Escape" });
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  });
});
