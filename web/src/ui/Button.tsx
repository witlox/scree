import type { ButtonHTMLAttributes } from "react";

type Variant = "primary" | "secondary" | "ghost";

/** Native button (keyboard/focus come free); variant is visual only. Defaults to
 *  type="button" so it never accidentally submits a form. */
export function Button({
  variant = "secondary",
  className,
  type = "button",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  const cls = ["btn", `btn--${variant}`, className].filter(Boolean).join(" ");
  return <button type={type} className={cls} {...props} />;
}
