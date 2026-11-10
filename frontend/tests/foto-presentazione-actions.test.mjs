import assert from "node:assert/strict";
import test from "node:test";

import {
  removeFotoPresentazione,
  uploadFotoPresentazione,
} from "../src/components/aziende/foto-presentazione-actions.ts";

const PATH = "/api/v1/aziende/company-42/foto-presentazione";

function toasts() {
  const shown = { success: [], error: [] };
  return {
    shown,
    notify: {
      success: (message) => shown.success.push(message),
      error: (message) => shown.error.push(message),
    },
  };
}

test("removing the photo is confirmed by a success toast", async () => {
  const requests = [];
  const { shown, notify } = toasts();

  const removed = await removeFotoPresentazione(
    async (path, init) => {
      requests.push([path, init.method]);
    },
    PATH,
    notify,
  );

  assert.equal(removed, true);
  assert.deepEqual(requests, [[PATH, "DELETE"]]);
  assert.deepEqual(shown, { success: ["Foto rimossa"], error: [] });
});

test("a failed removal shows the server's message, else a fallback", async () => {
  const { shown, notify } = toasts();

  assert.equal(
    await removeFotoPresentazione(
      async () => {
        throw new Error("Azienda not found");
      },
      PATH,
      notify,
    ),
    false,
  );
  assert.equal(
    await removeFotoPresentazione(
      async () => {
        throw new Error("");
      },
      PATH,
      notify,
    ),
    false,
  );

  assert.deepEqual(shown, {
    success: [],
    error: ["Azienda not found", "Rimozione della foto non riuscita"],
  });
});

test("uploading sends the file as multipart and confirms it", async () => {
  const requests = [];
  const { shown, notify } = toasts();
  const file = new File(["jpeg"], "sede.jpg", { type: "image/jpeg" });

  const saved = await uploadFotoPresentazione(
    async (path, init) => {
      requests.push([path, init.method, init.body.get("file").name]);
    },
    PATH,
    file,
    notify,
  );

  assert.equal(saved, true);
  assert.deepEqual(requests, [[PATH, "PUT", "sede.jpg"]]);
  assert.deepEqual(shown, { success: ["Foto di presentazione salvata"], error: [] });
});

test("a failed upload shows the server's message, else a fallback", async () => {
  const { shown, notify } = toasts();
  const file = new File(["gif"], "logo.gif", { type: "image/gif" });

  for (const message of ["Formato non supportato o file troppo grande (max 10 MB)", ""]) {
    const saved = await uploadFotoPresentazione(
      async () => {
        throw new Error(message);
      },
      PATH,
      file,
      notify,
    );
    assert.equal(saved, false);
  }

  assert.deepEqual(shown, {
    success: [],
    error: [
      "Formato non supportato o file troppo grande (max 10 MB)",
      "Caricamento della foto non riuscito",
    ],
  });
});
