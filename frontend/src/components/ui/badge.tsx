import { mergeProps } from "@base-ui/react/merge-props"
import { useRender } from "@base-ui/react/use-render"
import { cva, type VariantProps } from "class-variance-authority"

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
        destructive:
          "bg-[rgba(186,26,26,0.1)] text-destructive border-[rgba(186,26,26,0.3)] [a]:hover:bg-[rgba(186,26,26,0.15)]",
        outline:
          "border-[#e5edf5] bg-white text-[#273951] [a]:hover:bg-[#f6f9fc]",
        ghost:
          "text-[#64748d] hover:bg-[#f6f9fc] hover:text-[#273951]",
        link: "text-primary underline-offset-4 hover:underline",
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
