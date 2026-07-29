import type { ReactNode } from "react";
import { AlertTriangle, CheckCircle2, Info, OctagonAlert } from "lucide-react";

import { TONE_SURFACE } from "@/lib/ui/tones";
import { cn } from "@/lib/utils";

/**
 * The one bordered "read this" box in the app.
 *
 * Before this existed, roughly twenty screens hand-rolled the same shape with
 * `border-amber-300 bg-amber-50 text-amber-900` — a fully saturated yellow slab
 * that out-shouts the content it annotates, breaks DESIGN.md §7 ("don't use
 * warm accent colors", "conservative rounding") and drifts a shade every time
 * someone copies it. `FormError` had already solved this correctly for the red
 * case: a 5%-alpha tint under a 28%-alpha hairline, 13px text, small icon. This
 * is that recipe generalised to four tones, and `FormError` remains its own
 * component only because it owns `role="alert"` semantics a generic box cannot
 * assume.
 *
 * The tone colours come from `lib/ui/tones` — the same vocabulary the badges
 * read, one tier softer. Warn is Stripe "lemon" (`--color-warning`), not
 * amber-500.
 */

export type CalloutTone = "info" | "warn" | "danger" | "success";

/** `warn` rather than `warning` is what the billing screens already say. */
const TONE_KEY = {
  info: "info",
  warn: "warning",
  danger: "danger",
  success: "success",
} as const;

const TONE_ICON: Record<CalloutTone, typeof Info> = {
  info: Info,
  warn: AlertTriangle,
  danger: OctagonAlert,
  success: CheckCircle2,
};

export function Callout({
  tone = "info",
  title,
  icon,
  action,
  dense = false,
  className,
  children,
  ...rest
}: {
  tone?: CalloutTone;
  /** Lead-in phrase. Rendered inline before the body so the box stays one strip. */
  title?: ReactNode;
  /** Overrides the tone's default glyph. Sized by the caller. */
  icon?: ReactNode;
  /** Buttons or links pinned to the trailing edge; wraps under on narrow widths. */
  action?: ReactNode;
  /** Tighter padding for boxes nested inside cards and table rows. */
  dense?: boolean;
  className?: string;
  children?: ReactNode;
} & Omit<React.HTMLAttributes<HTMLDivElement>, "title">) {
  const ToneIcon = TONE_ICON[tone];

  return (
    <div
      className={cn(
        // Type sizing lives on the root, not on the text node, so a caller in a
        // denser context can shrink it with `className="text-[11.5px]"` and let
        // tailwind-merge win the conflict.
        "flex items-start gap-2.5 rounded-md border text-[13px] leading-[1.45]",
        dense ? "px-3 py-2" : "px-3.5 py-3",
        TONE_SURFACE[TONE_KEY[tone]],
        className
      )}
      {...rest}
    >
      <span className="mt-px flex shrink-0" aria-hidden>
        {icon ?? <ToneIcon className="h-3.5 w-3.5" strokeWidth={1.9} />}
      </span>

      <div
        className={cn(
          "min-w-0 flex-1",
          // The action only earns its own row when it exists; otherwise the text
          // should be free to use the full width.
          action && "flex flex-wrap items-center justify-between gap-x-4 gap-y-2"
        )}
      >
        <div className={cn("min-w-0", action && "flex-1")}>
          {title ? <span className="font-semibold">{title}</span> : null}
          {title && children ? " " : null}
          {children}
        </div>
        {action ? <div className="flex shrink-0 items-center gap-2">{action}</div> : null}
      </div>
    </div>
  );
}
