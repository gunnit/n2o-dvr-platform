import type { Metadata } from "next";

// Metadata-only layout: the page itself is a client component and cannot
// export `metadata`. The root layout's title template turns this into
// "Dashboard | N2O DVR" (P3-6).
export const metadata: Metadata = {
  title: "Dashboard",
  description: "Panoramica dell'attività: aziende, sopralluoghi e documenti.",
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
