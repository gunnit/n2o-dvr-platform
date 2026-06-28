const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function getToken(): Promise<string | undefined> {
  const res = await fetch("/api/auth/session");
  const session = await res.json();
  return session?.accessToken as string | undefined;
}

/**
 * Fetch an authenticated image endpoint and return an object URL for an
 * <img src>. Returns null when the endpoint 404s (e.g. no custom logo set),
 * so callers can fall back to a bundled default mark. The caller owns the
 * returned URL and should URL.revokeObjectURL() it on cleanup.
 */
export async function fetchImageBlobUrl(path: string): Promise<string | null> {
  const token = await getToken();
  const res = await fetch(`${API_URL}${path}`, {
    headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
  });
  if (!res.ok) return null;
  const blob = await res.blob();
  return URL.createObjectURL(blob);
}

export async function apiCall<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const token = await getToken();
  const { headers: callerHeaders, ...rest } = options ?? {};
  const res = await fetch(`${API_URL}${path}`, {
    ...rest,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(callerHeaders as Record<string, string> | undefined),
    },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `API error: ${res.status}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

/**
 * Download a file from an authenticated endpoint.
 *
 * `window.open()` / `<a href>` cannot attach the Bearer token that lives in
 * the NextAuth session, so protected downloads must go through fetch. We pull
 * the response as a blob, synthesize a temporary anchor, and click it to
 * trigger the browser's download UI.
 */
export async function downloadFile(
  path: string,
  fallbackFilename?: string
): Promise<void> {
  const token = await getToken();
  const res = await fetch(`${API_URL}${path}`, {
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });
  if (!res.ok) {
    let detail: string | undefined;
    try {
      const body = await res.json();
      detail = body?.detail;
    } catch {
      /* non-JSON error body */
    }
    throw new Error(detail || `Download failed: ${res.status}`);
  }

  // Try to honor the server-provided filename
  const disposition = res.headers.get("content-disposition") || "";
  const match = disposition.match(/filename\*?=(?:UTF-8'')?"?([^";]+)"?/i);
  const filename = match ? decodeURIComponent(match[1]) : fallbackFilename || "download";

  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  // Release memory on the next tick so the browser has a chance to start the download.
  setTimeout(() => URL.revokeObjectURL(url), 0);
}
