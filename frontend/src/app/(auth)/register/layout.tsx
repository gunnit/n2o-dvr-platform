import type { Metadata } from "next";

// Metadata-only layout: the page itself is a client component and cannot
// export `metadata`. The root layout's title template turns this into
// "Crea account | N2O DVR" (P3-6).
export const metadata: Metadata = {
  title: "Crea account",
  description: "Attiva un piano N2O DVR.",
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
