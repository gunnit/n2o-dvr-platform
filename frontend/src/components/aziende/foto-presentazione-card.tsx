"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ImageIcon } from "lucide-react";
import { toast } from "sonner";

import {
  removeFotoPresentazione,
  uploadFotoPresentazione,
} from "@/components/aziende/foto-presentazione-actions";
import { Panel, PanelHeader } from "@/components/aziende/tabs/_shared";
import { Button } from "@/components/ui/button";
import { useApi } from "@/hooks/use-api";
import { usePermissions } from "@/hooks/use-permissions";
import { fetchImageBlobUrl } from "@/lib/api-client";
import { SURVEY_WRITE } from "@/lib/permissions";

/**
 * The company photo printed under "Presentazione dell'azienda" in the DVR.
 * Previewed through an authenticated fetch (an <img src> cannot carry the
 * bearer token). Upload and removal need the survey-write capability; the
 * preview does not.
 */
export function FotoPresentazioneCard({ aziendaId }: { aziendaId: string }) {
  const { can } = usePermissions();
  const { apiFetch } = useApi();
  const canWrite = can(SURVEY_WRITE);
  const path = `/api/v1/aziende/${aziendaId}/foto-presentazione`;

  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  // Bumped after an upload or removal to refetch the preview.
  const [version, setVersion] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    let cancelled = false;
    let created: string | null = null;
    setLoading(true);
    fetchImageBlobUrl(path)
      .catch(() => null)
      .then((url) => {
        if (cancelled) {
          if (url) URL.revokeObjectURL(url);
          return;
        }
        created = url;
        setPreviewUrl(url);
        setLoading(false);
      });
    return () => {
      cancelled = true;
      if (created) URL.revokeObjectURL(created);
    };
  }, [path, version]);

  const onFile = useCallback(
    async (file: File) => {
      setBusy(true);
      try {
        if (await uploadFotoPresentazione(apiFetch, path, file, toast)) {
          setVersion((v) => v + 1);
        }
      } finally {
        setBusy(false);
      }
    },
    [apiFetch, path],
  );

  const onRemove = useCallback(async () => {
    setBusy(true);
    try {
      if (await removeFotoPresentazione(apiFetch, path, toast)) {
        setVersion((v) => v + 1);
      }
    } finally {
      setBusy(false);
    }
  }, [apiFetch, path]);

  return (
    <Panel accent="sky">
      <PanelHeader
        icon={ImageIcon}
        title="Foto di presentazione"
        subtitle="Compare nel DVR sotto «Presentazione dell'azienda». JPG, PNG o HEIC fino a 10 MB."
        accent="sky"
      />
      <div className="space-y-4 p-6">
        {previewUrl ? (
          // eslint-disable-next-line @next/next/no-img-element -- authenticated blob URL, not optimisable
          <img
            src={previewUrl}
            alt="Foto di presentazione dell'azienda"
            className="max-h-64 w-full rounded-md border border-[#e5edf5] object-contain"
          />
        ) : (
          !loading && (
            <p className="text-[14px] text-[#64748d]">
              Nessuna foto caricata.
            </p>
          )
        )}
        {canWrite && (
          <div className="flex flex-wrap gap-2">
            <input
              ref={inputRef}
              type="file"
              accept="image/jpeg,image/png,image/heic,.jpg,.jpeg,.png,.heic"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0];
                e.target.value = "";
                if (file) void onFile(file);
              }}
            />
            <Button
              variant={previewUrl ? "outline" : "default"}
              disabled={busy}
              onClick={() => inputRef.current?.click()}
            >
              {previewUrl ? "Sostituisci" : "Carica foto"}
            </Button>
            {previewUrl && (
              <Button variant="destructive" disabled={busy} onClick={onRemove}>
                Rimuovi
              </Button>
            )}
          </div>
        )}
      </div>
    </Panel>
  );
}
