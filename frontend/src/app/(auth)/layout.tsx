import type { ReactNode } from "react";

/**
 * Pass-through. This layout used to own a shell of its own — a background
 * photograph with its own header and footer, under which /register floated as
 * a centred card. That made the signup half of the funnel look like a
 * different product from the sign-in half two clicks later, so the page now
 * renders the shared `AuthSplit` instead and there is nothing left to wrap.
 *
 * Kept rather than deleted because the route group's `register/layout.tsx`
 * sibling carries metadata, and a segment here keeps that nesting explicit.
 */
export default function AuthLayout({ children }: { children: ReactNode }) {
  return children;
}
