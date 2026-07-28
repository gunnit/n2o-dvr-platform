import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

/**
 * The one way this app shows a form-level failure.
 *
 * `role="alert"` is the whole point: most screens used to render their error as
 * a bare `<p className="text-destructive">`, which is red to a sighted user and
 * silent to everyone else — the message was never announced. An assistive
 * technology only speaks a message that arrives in a live region, so the
 * container has to exist in the DOM before the text lands in it. Rendering
 * `null` until there is an error and then mounting the whole box is enough for
 * `alert` (it is an assertive live region and fires on insertion), which is why
 * this component owns the empty case instead of asking callers to guard.
 *
 * Markup follows /login, which had the only correct implementation.
 */
export function FormError({
  children,
  className,
}: {
  children?: ReactNode;
  className?: string;
}) {
  if (!children) return null;

  return (
    <div
      role="alert"
      className={cn(
        "flex items-start gap-2.5 rounded-md border border-[rgba(199,42,58,0.28)] bg-[rgba(199,42,58,0.05)] px-3.5 py-3",
        className
      )}
    >
      <span className="mt-px flex shrink-0 text-[#c72a3a]">
        <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden>
          <circle cx="7" cy="7" r="6" fill="none" stroke="currentColor" strokeWidth="1.4" />
          <path
            d="M7 6.4v3.4M7 4.1v.6"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.4"
            strokeLinecap="round"
          />
        </svg>
      </span>
      <p className="text-[13px] leading-[1.45] text-[#c72a3a]">{children}</p>
    </div>
  );
}

/**
 * Per-field validation message, sitting under its input.
 *
 * Deliberately not an alert box: six of these can be on screen at once and a
 * stack of bordered panels would bury the form. It carries an `id` instead, so
 * the input can point at it with `aria-describedby` — paired with
 * `aria-invalid`, that is what makes a screen reader read the reason when the
 * field takes focus. The id is required for exactly that reason.
 */
export function FieldError({
  id,
  children,
}: {
  id: string;
  children?: ReactNode;
}) {
  if (!children) return null;

  return (
    <p id={id} className="text-xs text-destructive">
      {children}
    </p>
  );
}
