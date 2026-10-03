"use client";

import { useCallback, useEffect, useState, type ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import { Info } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

/**
 * Where an acknowledgment is remembered:
 * - "local": once per browser, until site data is cleared (onboarding hints);
 * - "session": once per browser tab session, so it comes back the next time
 *   the operator works on the page (notices N2O wants seen at each start).
 */
export type NoticeScope = "local" | "session";

function readFlag(scope: NoticeScope, key: string): boolean {
  try {
    const store = scope === "local" ? window.localStorage : window.sessionStorage;
    return store.getItem(key) === "1";
  } catch {
    // Private mode or blocked storage: show the notice, never crash.
    return false;
  }
}

function writeFlag(scope: NoticeScope, key: string): void {
  try {
    const store = scope === "local" ? window.localStorage : window.sessionStorage;
    store.setItem(key, "1");
  } catch {
    /* storage unavailable — the notice simply shows again next time */
  }
}

/**
 * Open a notice the first time `key` is seen in `scope`. `key` may change
 * (one notice per ambiente, say): the hook re-checks for each new key.
 * Passing `null` keeps the notice closed. `show()` reopens it on demand.
 */
export function useOnceNotice(key: string | null, scope: NoticeScope = "local") {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!key) return;
    // Deferred: reading storage is browser-only and must not set state
    // synchronously inside the effect body.
    const t = setTimeout(() => setOpen(!readFlag(scope, key)), 0);
    return () => clearTimeout(t);
  }, [key, scope]);

  const acknowledge = useCallback(() => {
    if (key) writeFlag(scope, key);
    setOpen(false);
  }, [key, scope]);

  const show = useCallback(() => setOpen(true), []);

  return { open, acknowledge, show };
}

interface NoticeDialogProps {
  open: boolean;
  /** Called by the confirm button and by closing the dialog. */
  onAcknowledge: () => void;
  title: string;
  children: ReactNode;
  confirmLabel?: string;
  icon?: LucideIcon;
}

/** Informational popup with one confirm button. Pair with `useOnceNotice`. */
export function NoticeDialog({
  open,
  onAcknowledge,
  title,
  children,
  confirmLabel = "Ho capito",
  icon: Icon = Info,
}: NoticeDialogProps) {
  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next) onAcknowledge();
      }}
    >
      <DialogContent>
        <DialogHeader>
          <div className="flex items-start gap-3">
            <span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-[rgba(27,85,148,0.1)] text-[#1b5594]">
              <Icon className="size-4" aria-hidden />
            </span>
            <div className="space-y-2">
              <DialogTitle>{title}</DialogTitle>
              <DialogDescription render={<div />}>{children}</DialogDescription>
            </div>
          </div>
        </DialogHeader>
        <DialogFooter>
          <Button type="button" onClick={onAcknowledge}>
            {confirmLabel}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
