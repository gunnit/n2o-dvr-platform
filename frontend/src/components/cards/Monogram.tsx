import { cn } from "@/lib/utils";
import type { ReactNode } from "react";

export type AccentKey =
  | "navy"
  | "sky"
  | "emerald"
  | "amber"
  | "violet"
  | "rose"
  | "slate";

const ACCENT_CLASS: Record<AccentKey, string> = {
  navy: "bg-[linear-gradient(135deg,#e6f0fb_0%,#c9dcf1_100%)] text-[#003d74] border-[rgba(0,61,116,0.18)]",
  sky: "bg-[linear-gradient(135deg,#eef4ff_0%,#dbe6fe_100%)] text-[#1b5594] border-[rgba(27,85,148,0.15)]",
  emerald:
    "bg-[linear-gradient(135deg,#ecfdf5_0%,#d1fae5_100%)] text-[#108c3d] border-[rgba(16,140,61,0.18)]",
  amber:
    "bg-[linear-gradient(135deg,#fffbeb_0%,#fef3c7_100%)] text-[#9b6829] border-[rgba(155,104,41,0.18)]",
  violet:
    "bg-[linear-gradient(135deg,#f5f0ff_0%,#e4d8ff_100%)] text-[#5b21b6] border-[rgba(91,33,182,0.18)]",
  rose: "bg-[linear-gradient(135deg,#fff1f2_0%,#fecaca_100%)] text-[#be185d] border-[rgba(190,24,93,0.18)]",
  slate:
    "bg-[linear-gradient(135deg,#f6f9fc_0%,#e5edf5_100%)] text-[#475569] border-[rgba(71,85,105,0.18)]",
};

const SIZE_CLASS = {
  sm: "h-9 w-9 rounded-[8px] text-[12px]",
  md: "h-[42px] w-[42px] rounded-[10px] text-[14px]",
  lg: "h-12 w-12 rounded-[10px] text-[16px]",
} as const;

export function Monogram({
  accent = "navy",
  size = "md",
  className,
  children,
}: {
  accent?: AccentKey;
  size?: keyof typeof SIZE_CLASS;
  className?: string;
  children: ReactNode;
}) {
  return (
    <div
      className={cn(
        "flex flex-none items-center justify-center border font-bold tracking-tight",
        "tnum",
        SIZE_CLASS[size],
        ACCENT_CLASS[accent],
        className,
      )}
    >
      {children}
    </div>
  );
}
