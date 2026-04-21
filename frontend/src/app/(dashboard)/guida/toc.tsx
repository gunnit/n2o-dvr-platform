"use client";

import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";

export type TocItem = {
  id: string;
  text: string;
  level: 2 | 3 | 4;
};

const LEVEL_INDENT: Record<TocItem["level"], string> = {
  2: "pl-3",
  3: "pl-6",
  4: "pl-9",
};

export function Toc({ items }: { items: TocItem[] }) {
  const [activeId, setActiveId] = useState<string | null>(
    items[0]?.id ?? null
  );

  useEffect(() => {
    if (items.length === 0) return;
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
        if (visible[0]) setActiveId(visible[0].target.id);
      },
      {
        rootMargin: "-80px 0px -70% 0px",
        threshold: 0,
      }
    );
    items.forEach((item) => {
      const el = document.getElementById(item.id);
      if (el) observer.observe(el);
    });
    return () => observer.disconnect();
  }, [items]);

  return (
    <nav aria-label="Indice della guida" className="space-y-1">
      <p className="type-eyebrow mb-3">In questa pagina</p>
      <ul className="space-y-1 border-l border-[#e5edf5]">
        {items.map((item) => (
          <li key={item.id}>
            <a
              href={`#${item.id}`}
              className={cn(
                "block border-l-2 py-1 text-[13px] leading-snug transition-colors",
                LEVEL_INDENT[item.level],
                activeId === item.id
                  ? "-ml-px border-primary font-medium text-primary"
                  : "-ml-px border-transparent text-[#64748d] hover:text-[#061b31]"
              )}
            >
              {item.text}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}
