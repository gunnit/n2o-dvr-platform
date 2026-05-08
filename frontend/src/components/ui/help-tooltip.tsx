"use client"

/**
 * Tiny inline help affordance — a muted "?" icon that shows a tooltip on hover
 * or focus. Built on Base UI (the project already standardises on it; no Radix
 * is installed). Use it next to form labels / table headers when a field's
 * meaning or scale isn't obvious from the label alone.
 */
import * as React from "react"
import { Tooltip as TooltipPrimitive } from "@base-ui/react/tooltip"
import { HelpCircle } from "lucide-react"

import { cn } from "@/lib/utils"

interface HelpTooltipProps {
  text: string
  /** Accessible label for the trigger. Defaults to "Aiuto". */
  ariaLabel?: string
  /** Where the popup appears relative to the trigger. */
  side?: "top" | "right" | "bottom" | "left"
  className?: string
}

export function HelpTooltip({
  text,
  ariaLabel = "Aiuto",
  side = "top",
  className,
}: HelpTooltipProps) {
  return (
    <TooltipPrimitive.Root>
      <TooltipPrimitive.Trigger
        delay={150}
        // Native title is a no-JS / screen-reader-friendly fallback.
        title={text}
        aria-label={ariaLabel}
        className={cn(
          "inline-flex items-center justify-center text-muted-foreground transition-colors hover:text-foreground focus-visible:text-foreground focus-visible:outline-none",
          className,
        )}
      >
        <HelpCircle className="h-3.5 w-3.5" aria-hidden="true" />
      </TooltipPrimitive.Trigger>
      <TooltipPrimitive.Portal>
        <TooltipPrimitive.Positioner side={side} sideOffset={6}>
          <TooltipPrimitive.Popup
            className={cn(
              "z-50 max-w-[280px] rounded-md border border-[#e5edf5] bg-popover px-3 py-2 text-xs leading-snug text-popover-foreground shadow-md outline-none",
              "transition-opacity duration-100 data-[starting-style]:opacity-0 data-[ending-style]:opacity-0",
            )}
          >
            {text}
          </TooltipPrimitive.Popup>
        </TooltipPrimitive.Positioner>
      </TooltipPrimitive.Portal>
    </TooltipPrimitive.Root>
  )
}
