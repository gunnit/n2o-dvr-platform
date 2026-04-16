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
    <header className="sticky top-0 z-40 flex h-16 items-center justify-between bg-white/80 px-8 font-heading text-sm tracking-tight shadow-sm backdrop-blur-xl">
      <nav className="flex min-w-0 items-center gap-2 text-on-surface-variant" aria-label="Breadcrumb">
        {breadcrumbs.length === 0 ? (
          <span className="font-bold text-primary-container">Dashboard</span>
        ) : (
          breadcrumbs.map((crumb, i) => {
            const isLast = i === breadcrumbs.length - 1;
            return (
              <span key={`${crumb.label}-${i}`} className="flex items-center gap-2">
                {i > 0 && <ChevronRight className="h-4 w-4 shrink-0 text-on-surface-variant/50" strokeWidth={2} />}
                {isLast ? (
                  <span className="truncate font-bold text-primary-container">{crumb.label}</span>
                ) : crumb.href ? (
                  <Link
                    href={crumb.href}
                    className="truncate transition-colors hover:text-primary-container"
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
