"use client";

import { Sparkles } from "lucide-react";
import { createContext, useCallback, useContext, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

/**
 * Global "Mostra solo contenuto AI" filter (US-5.3 AC3).
 *
 * Pages wrap their content in <AIFilterProvider>. Any <AIContent> descendant
 * declares its provenance; when the filter is ON, non-AI blocks are dimmed
 * and made non-interactive while AI blocks stay crisp.
 *
 * The toggle lives in <AIFilterToggle>, which can be dropped into a header
 * or toolbar. State is page-local (not persisted) — resets on navigation,
 * which matches operator expectation that review is a focused mode.
 */

interface AIFilterState {
  active: boolean;
  toggle: () => void;
  setActive: (v: boolean) => void;
}

const AIFilterContext = createContext<AIFilterState | null>(null);

export function AIFilterProvider({ children }: { children: React.ReactNode }) {
  const [active, setActive] = useState(false);
  const value = useMemo<AIFilterState>(
    () => ({ active, setActive, toggle: () => setActive((a) => !a) }),
    [active]
  );
  return <AIFilterContext.Provider value={value}>{children}</AIFilterContext.Provider>;
}

export function useAIFilter(): AIFilterState {
  const ctx = useContext(AIFilterContext);
  // Fall back to an inert context when there's no provider — lets <AIContent>
  // be used on pages that haven't opted into the filter without throwing.
  return ctx ?? { active: false, toggle: () => {}, setActive: () => {} };
}

interface AIContentProps {
  /** Whether this block is AI-originated. Edited or manual → non-AI for the filter's purposes. */
  isAI: boolean;
  className?: string;
  children: React.ReactNode;
}

/**
 * Wrap any section of content that has provenance so the page-level filter
 * can dim / highlight it. Non-AI blocks fade to 40% opacity and ignore
 * pointer events when the filter is active.
 */
export function AIContent({ isAI, className, children }: AIContentProps) {
  const { active } = useAIFilter();
  const dimmed = active && !isAI;
  const highlighted = active && isAI;

  return (
    <div
      data-ai-block={isAI ? "ai" : "non-ai"}
      className={cn(
        "transition-opacity",
        dimmed && "pointer-events-none select-none opacity-40",
        highlighted && "ring-1 ring-violet-200 rounded-md",
        className
      )}
    >
      {children}
    </div>
  );
}

export function AIFilterToggle({ className }: { className?: string }) {
  const { active, toggle } = useAIFilter();
  return (
    <Button
      type="button"
      variant={active ? "default" : "outline"}
      size="sm"
      onClick={toggle}
      className={cn(className)}
      aria-pressed={active}
      title="Metti in evidenza solo il contenuto generato dall'AI."
    >
      <Sparkles className="mr-1.5 h-3.5 w-3.5" />
      {active ? "Mostrando solo AI" : "Mostra solo contenuto AI"}
    </Button>
  );
}
