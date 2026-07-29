import { mergeProps } from "@base-ui/react/merge-props"
import { useRender } from "@base-ui/react/use-render"
import { cva, type VariantProps } from "class-variance-authority"

import { TONE_CHIP } from "@/lib/ui/tones"
import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "group/badge inline-flex h-[22px] w-fit shrink-0 items-center justify-center gap-1 overflow-hidden rounded-sm border border-transparent px-2 py-0.5 text-[11px] font-medium whitespace-nowrap transition-all focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary has-data-[icon=inline-end]:pr-1.5 has-data-[icon=inline-start]:pl-1.5 aria-invalid:border-destructive aria-invalid:ring-destructive/20 [&>svg]:pointer-events-none [&>svg]:size-3!",
  {
    variants: {
      variant: {
        default:
          "bg-[rgba(0,61,116,0.08)] text-primary border-[rgba(0,61,116,0.2)] [a]:hover:bg-[rgba(0,61,116,0.12)]",
        secondary:
          "bg-[#f6f9fc] text-[#273951] border-[#e5edf5] [a]:hover:bg-[#eef2f7]",
        // `destructive` is the shadcn name and `danger` the one the tone
        // vocabulary uses; they render identically so a call site can say
        // either without the two drifting apart.
        destructive: TONE_CHIP.danger,
        danger: TONE_CHIP.danger,
        outline:
          "border-[#e5edf5] bg-white text-[#273951] [a]:hover:bg-[#f6f9fc]",
        ghost:
          "text-[#64748d] hover:bg-[#f6f9fc] hover:text-[#273951]",
        link: "text-primary underline-offset-4 hover:underline",
        // Semantic tones from `lib/ui/tones`. Without these, ~40 call sites
        // reached past the component for a raw amber-100/amber-800 pair
        // and every one of them picked a slightly different yellow.
        success: TONE_CHIP.success,
        warning: TONE_CHIP.warning,
        info: TONE_CHIP.info,
        neutral: TONE_CHIP.neutral,
        /** Provenance marker for anything a model wrote. */
        ai: TONE_CHIP.ai,
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

function Badge({
  className,
  variant = "default",
  render,
  ...props
}: useRender.ComponentProps<"span"> & VariantProps<typeof badgeVariants>) {
  return useRender({
    defaultTagName: "span",
    props: mergeProps<"span">(
      {
        className: cn(badgeVariants({ variant }), className),
      },
      props
    ),
    render,
    state: {
      slot: "badge",
      variant,
    },
  })
}

export { Badge, badgeVariants }
