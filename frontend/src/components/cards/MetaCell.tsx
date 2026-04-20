import { cn } from "@/lib/utils";
import type { ReactNode } from "react";

export function MetaCell({
  label,
  children,
  tone = "default",
  tnum = false,
}: {
  label: string;
  children: ReactNode;
  tone?: "default" | "danger" | "warn" | "ok" | "muted";
  tnum?: boolean;
}) {
  return (
    <div className="min-w-0">
      <div className="text-[10.5px] font-semibold uppercase tracking-[0.06em] text-[#94a3b8]">
        {label}
      </div>
      <div
        className={cn(
          "mt-0.5 flex items-center gap-1 truncate text-[13px] font-semibold",
          tone === "default" && "text-[#273951]",
          tone === "danger" && "text-[#ba1a1a]",
          tone === "warn" && "text-[#9b6829]",
          tone === "ok" && "text-[#108c3d]",
          tone === "muted" && "text-[#64748d]",
          tnum && "tnum",
        )}
      >
        {children}
      </div>
    </div>
  );
}
