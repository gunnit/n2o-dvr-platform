import type { ReactNode } from "react";
import { LoginBackdrop } from "@/components/auth/login-backdrop";

/**
 * The split screen both /login and /register sit in: the workshop panel on the
 * left, a white form column on the right.
 *
 * Below 900px the two stack — backdrop first, form under it — rather than
 * collapsing the photo away, so the promise still frames the form on a phone.
 * `min-h-svh` not `min-h-screen`: on mobile browsers with a retracting toolbar
 * `100vh` is taller than the visible viewport, which pushed the submit button
 * under the chrome on first paint.
 */
export function AuthSplit({
  children,
  /** Form column measure. Register runs wider — it has a two-up field row. */
  panelWidth = "392px",
  backdrop,
}: {
  children: ReactNode;
  panelWidth?: string;
  backdrop?: { eyebrow: string; title: ReactNode; body: string };
}) {
  return (
    <div className="grid min-h-svh grid-cols-[minmax(0,1.12fr)_minmax(0,0.88fr)] bg-[#061b31] max-[900px]:min-h-0 max-[900px]:grid-cols-[minmax(0,1fr)] max-[900px]:grid-rows-[auto_auto]">
      <LoginBackdrop {...backdrop} />

      <div className="relative flex flex-col items-center justify-center bg-white px-13 py-14 shadow-[-30px_0_70px_-40px_rgba(6,27,49,0.55)] max-[1080px]:px-[34px] max-[1080px]:py-12 max-[900px]:border-t max-[900px]:border-[rgba(6,27,49,0.1)] max-[900px]:px-[26px] max-[900px]:pt-13 max-[900px]:pb-11 max-[900px]:shadow-none">
        <div className="w-full" style={{ maxWidth: panelWidth }}>
          {children}
        </div>
      </div>
    </div>
  );
}
