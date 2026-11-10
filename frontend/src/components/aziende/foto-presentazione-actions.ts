/**
 * Upload and removal of the azienda's "foto di presentazione", each
 * confirmed or reported with a toast. Kept apart from the card so the flow
 * can be tested without a browser (tests/foto-presentazione-actions.test.mjs).
 */

type ApiFetch = (path: string, init: RequestInit) => Promise<unknown>;

/** The two toasts the card shows: sonner's `toast` fits. */
export type Notify = {
  success: (message: string) => unknown;
  error: (message: string) => unknown;
};

function failureMessage(err: unknown, fallback: string): string {
  return err instanceof Error && err.message ? err.message : fallback;
}

/** PUT the file as multipart; true when the photo was saved. */
export async function uploadFotoPresentazione(
  apiFetch: ApiFetch,
  path: string,
  file: File,
  notify: Notify,
): Promise<boolean> {
  try {
    const body = new FormData();
    body.append("file", file);
    await apiFetch(path, { method: "PUT", body });
    notify.success("Foto di presentazione salvata");
    return true;
  } catch (err) {
    notify.error(failureMessage(err, "Caricamento della foto non riuscito"));
    return false;
  }
}

/** DELETE the photo; true when it was removed. */
export async function removeFotoPresentazione(
  apiFetch: ApiFetch,
  path: string,
  notify: Notify,
): Promise<boolean> {
  try {
    await apiFetch(path, { method: "DELETE" });
    notify.success("Foto rimossa");
    return true;
  } catch (err) {
    notify.error(failureMessage(err, "Rimozione della foto non riuscita"));
    return false;
  }
}
