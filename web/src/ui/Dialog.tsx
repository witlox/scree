import { Dialog as RadixDialog } from "radix-ui";
import type { ReactNode } from "react";

/** Accessible modal on Radix (focus trap, Esc, aria-modal/labelledby — the hard a11y
 *  parts), styled with our tokens. Controlled via `open`/`onOpenChange`. */
export function Dialog({
  open,
  onOpenChange,
  title,
  trigger,
  children,
}: {
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  title: string;
  trigger?: ReactNode;
  children?: ReactNode;
}) {
  return (
    <RadixDialog.Root open={open} onOpenChange={onOpenChange}>
      {trigger && <RadixDialog.Trigger asChild>{trigger}</RadixDialog.Trigger>}
      <RadixDialog.Portal>
        <RadixDialog.Overlay className="dialog__overlay" />
        <RadixDialog.Content className="dialog__content" aria-describedby={undefined}>
          <RadixDialog.Title className="dialog__title">{title}</RadixDialog.Title>
          {children}
        </RadixDialog.Content>
      </RadixDialog.Portal>
    </RadixDialog.Root>
  );
}
