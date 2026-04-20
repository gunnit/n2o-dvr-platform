import { cn } from "@/lib/utils";
import type { ReactNode } from "react";

export function StatusBadge({
  className,
  children,
}: {
  className?: string;
  children: ReactNode;
}) {
  return (
    <span
      className={cn(
        "inline-flex flex-none items-center rounded-full px-2 py-[3px] text-[11px] font-semibold whitespace-nowrap",
        className,
      )}
    >
      {children}
    </span>
  );
}
