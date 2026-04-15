"use client";

import { SessionProvider } from "next-auth/react";
import { AIFilterProvider } from "@/components/ai/ai-filter-context";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <SessionProvider>
      <AIFilterProvider>{children}</AIFilterProvider>
    </SessionProvider>
  );
}
