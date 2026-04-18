"use client";

import Link from "next/link";
import { ChevronRight } from "lucide-react";
import { AIFilterToggle } from "@/components/ai/ai-filter-context";

export type Breadcrumb = {
  label: string;
  href?: string;
};

export function Header({
  breadcrumbs = [],
  actions,
}: {
  breadcrumbs?: Breadcrumb[];
  actions?: React.ReactNode;
}) {
  return (
    <header className="sticky top-0 z-40 flex h-14 items-center justify-between border-b border-[#e5edf5] bg-white/90 px-8 text-[13px] backdrop-blur-xl">
      <nav className="flex min-w-0 items-center gap-2 text-[#64748d]" aria-label="Breadcrumb">
        {breadcrumbs.length === 0 ? (
          <span className="font-medium text-[#061b31]">Dashboard</span>
        ) : (
          breadcrumbs.map((crumb, i) => {
            const isLast = i === breadcrumbs.length - 1;
            return (
              <span key={`${crumb.label}-${i}`} className="flex items-center gap-2">
                {i > 0 && <ChevronRight className="h-3.5 w-3.5 shrink-0 text-[#c2c6d2]" strokeWidth={2} />}
                {isLast ? (
                  <span className="truncate font-medium text-[#061b31]">{crumb.label}</span>
                ) : crumb.href ? (
                  <Link
                    href={crumb.href}
                    className="truncate transition-colors hover:text-primary"
                  >
                    {crumb.label}
                  </Link>
                ) : (
                  <span className="truncate">{crumb.label}</span>
                )}
              </span>
            );
          })
        )}
      </nav>

      <div className="flex items-center gap-3">
        <AIFilterToggle />
        {actions}
      </div>
    </header>
  );
}
