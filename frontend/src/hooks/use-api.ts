"use client";

import { useCallback, useEffect, useRef, useState } from "react";

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

      const { headers, ...rest } = options;

      const res = await fetch(`${API_URL}${path}`, {
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
          ...(headers as Record<string, string>),
        },
        ...rest,
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `API error: ${res.status}`);
      }

      if (res.status === 204) return undefined as T;
      return res.json();
    },
    []
  );

  return { apiFetch, isAuthenticated };
}
