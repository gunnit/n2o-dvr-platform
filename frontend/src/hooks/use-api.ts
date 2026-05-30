"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { signOut } from "next-auth/react";
import { parseApiError } from "@/lib/api-errors";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function getToken(): Promise<string | null> {
  try {
    const res = await fetch("/api/auth/session");
    const session = await res.json();
    return session?.accessToken ?? null;
  } catch {
    return null;
  }
}

export function useApi() {
  const tokenRef = useRef<string | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    getToken().then((t) => {
      tokenRef.current = t;
      setIsAuthenticated(!!t);
    });
  }, []);

  const apiFetch = useCallback(
    async <T>(path: string, options: RequestInit = {}): Promise<T> => {
      // Always get fresh token at call time
      let token = tokenRef.current;
      if (!token) {
        token = await getToken();
        tokenRef.current = token;
      }

      const { headers, body, ...rest } = options;

      // Multipart uploads must let the browser set Content-Type with the
      // correct boundary. Forcing application/json (the JSON-RPC default
      // for this hook) breaks FormData parsing on the FastAPI side.
      const isFormData =
        typeof FormData !== "undefined" && body instanceof FormData;
      const baseHeaders: Record<string, string> = isFormData
        ? {}
        : { "Content-Type": "application/json" };

      const res = await fetch(`${API_URL}${path}`, {
        body,
        headers: {
          ...baseHeaders,
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
          ...(headers as Record<string, string>),
        },
        ...rest,
      });

      if (res.status === 401) {
        // Backend token expired or invalid — sign out of NextAuth and bounce to login
        await signOut({ redirectTo: "/login" });
        throw new Error("Sessione scaduta. Effettua nuovamente il login.");
      }

      if (!res.ok) {
        // Pydantic 422 returns a detail array, not a string — the old code
        // turned that into "[object Object]" for the user. `parseApiError`
        // produces a readable Italian message and attaches the per-field
        // breakdown on the thrown Error for inline display.
        const parsed = await parseApiError(res);
        const error = new Error(parsed.message) as Error & {
          parsed: typeof parsed;
        };
        error.parsed = parsed;
        throw error;
      }

      if (res.status === 204) return undefined as T;
      return res.json();
    },
    []
  );

  return { apiFetch, isAuthenticated };
}
