import type { ComponentType, ReactNode } from "react";

import { cn } from "@/lib/utils";

/**
 * The "there is nothing here yet" block.
 *
 * Lived in `components/aziende/tabs/_shared.tsx`, so only the azienda tabs
 * could reach it and every page-level screen rolled its own: /documents
 * centred a 40%-opacity icon over one grey line, /admin/feedback printed a bare
 * "Nessuna segnalazione." with no icon at all, and DUVRI wrote
 * `Clicca "Aggiungi appaltatore" per iniziare` — prose pointing at a button
 * instead of offering one.
 *
 * The shape is title / body / action, in that order, because the operator needs
 * to know *what* is missing before *why*, and wants the way out in the block
 * rather than described by it. `body` and `action` are both optional; a title
 * alone is a legitimate empty state.
 */
export function EmptyState({
  icon: Icon,
  title,
  body,
  action,
  className,
}: {
  icon?: ComponentType<{ className?: string; strokeWidth?: number }>;
  title: string;
  body?: ReactNode;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-3 px-6 py-14 text-center",
        className,
      )}
    >
      {Icon && (
        <span className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-[#f6f9fc]">
          <Icon className="h-5 w-5 text-[#64748d]" strokeWidth={1.5} />
        </span>
      )}
      <div className="space-y-1">
        <p className="text-[14px] font-medium text-[#273951]">{title}</p>
        {body && (
          <p className="mx-auto max-w-[420px] text-[13px] leading-[1.5] text-[#64748d]">
            {body}
          </p>
        )}
      </div>
      {action}
    </div>
  );
}

/**
 * `EmptyState` in its own card — the page-level form, where there is no
 * surrounding panel to sit inside.
 *
 * `dashed` marks the "your filter matched nothing" case as distinct from "there
 * is no data yet": a solid card is a permanent state of the record, a dashed
 * one is a consequence of what the operator just typed and disappears when they
 * clear it.
 */
export function EmptyStateCard({
  dashed = false,
  ...props
}: Parameters<typeof EmptyState>[0] & { dashed?: boolean }) {
  return (
    <div
      className={cn(
        "rounded-md border bg-white",
        dashed
          ? "border-dashed border-[#dbe4ee]"
          : "border-[#e5edf5] shadow-stripe-ambient",
      )}
    >
      <EmptyState {...props} />
    </div>
  );
}
