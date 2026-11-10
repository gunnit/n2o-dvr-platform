"use client";

import { useEffect, useState, type RefObject } from "react";

import { fetchImageBlobUrl } from "@/lib/api-client";

export interface DocumentImage {
  /** Object URL of the picture once fetched; null while loading or failed. */
  src: string | null;
  failed: boolean;
}

/**
 * A picture of the document, from GET /documenti/{id}/preview/images/{id}
 * (main-part "rIdN" or part-scoped "ftr:footerN.xml:rIdM"). The endpoint
 * needs the session's bearer token, so the picture is fetched into an
 * object URL, which is revoked when the component unmounts or the id
 * changes. Nothing is fetched until `enabled`.
 */
export function useDocumentImage(
  documentId: string,
  imageId: string | null | undefined,
  enabled = true,
): DocumentImage {
  const key = imageId ? `${documentId}/${imageId}` : null;
  const [loaded, setLoaded] = useState<{ key: string; src: string | null } | null>(
    null,
  );

  useEffect(() => {
    if (!enabled || !imageId || key === null) return;
    let objectUrl: string | null = null;
    let cancelled = false;
    fetchImageBlobUrl(
      `/api/v1/documenti/${documentId}/preview/images/${encodeURIComponent(imageId)}`,
    )
      .then((url) => {
        if (cancelled) {
          if (url) URL.revokeObjectURL(url);
          return;
        }
        objectUrl = url;
        setLoaded({ key, src: url });
      })
      .catch(() => {
        // Network/auth failure: settle into the failed state instead of
        // loading forever (and leaking an unhandled promise rejection).
        if (!cancelled) setLoaded({ key, src: null });
      });
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [documentId, imageId, enabled, key]);

  // A result for another id (the id just changed) is stale: its URL is
  // already revoked.
  const current = loaded !== null && loaded.key === key ? loaded : null;
  return { src: current?.src ?? null, failed: current !== null && current.src === null };
}

/**
 * True once the element has come within `rootMargin` of the viewport, and
 * from then on: lets a sheet fetch its full-page art just before it is
 * scrolled to, instead of every divider of a DVR at once.
 */
export function useNearViewport(
  ref: RefObject<Element | null>,
  rootMargin = "1500px 0px",
): boolean {
  const [near, setNear] = useState(false);
  const supported = typeof IntersectionObserver !== "undefined";

  useEffect(() => {
    if (near || !supported) return;
    const element = ref.current;
    if (!element) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          setNear(true);
          observer.disconnect();
        }
      },
      { rootMargin },
    );
    observer.observe(element);
    return () => observer.disconnect();
  }, [near, supported, ref, rootMargin]);

  return near || !supported;
}
