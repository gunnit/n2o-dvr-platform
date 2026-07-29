import * as React from "react";

import { cn } from "@/lib/utils";

/**
 * The project's `<select>`, styled to match `<Input>`.
 *
 * Before this component the app spelled a dropdown eight different ways —
 * `border-input bg-transparent`, `border bg-background`, `rounded-xl
 * border-none bg-surface-low`, three different heights and two different focus
 * rings — so the azienda picker on /documents looked nothing like the one on
 * /assessments. The box now has one definition.
 *
 * It renders a bare `<select>` rather than wrapping one, so it is a drop-in
 * swap at call sites where the element is a flex child or sized by its parent.
 * That rules out an element-based chevron, hence the inline SVG background:
 * `appearance-none` hides the OS arrow, which otherwise varies per platform and
 * ignores our palette. `pr-9` keeps long option labels clear of it.
 */

const CHEVRON =
  "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%2364748d' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='m6 9 6 6 6-6'/%3E%3C/svg%3E\")";

function Select({
  className,
  size = "default",
  style,
  ...props
}: Omit<React.ComponentProps<"select">, "size"> & {
  /**
   * Control height. Shadows the native `size` attribute (rows visible in a
   * multi-select), which this app never uses and which would otherwise
   * intersect to `never`.
   */
  size?: "sm" | "default";
}) {
  return (
    <select
      data-slot="select"
      className={cn(
        "w-full min-w-0 appearance-none rounded-md border border-[#e5edf5] bg-white bg-no-repeat pr-9 text-sm text-[#061b31] transition-colors outline-none",
        "focus-visible:border-primary focus-visible:ring-2 focus-visible:ring-primary/20",
        "disabled:pointer-events-none disabled:cursor-not-allowed disabled:bg-[#f6f9fc] disabled:opacity-60",
        "aria-invalid:border-destructive aria-invalid:ring-2 aria-invalid:ring-destructive/20",
        size === "sm" ? "h-9 pl-2.5" : "h-10 pl-3",
        className,
      )}
      style={{
        backgroundImage: CHEVRON,
        backgroundPosition: "right 0.625rem center",
        backgroundSize: "1rem 1rem",
        ...style,
      }}
      {...props}
    />
  );
}

export { Select };
