import assert from "node:assert/strict";
import test from "node:test";

import {
  incendioAreaFromServer,
  incendioAreaNameIsReadOnly,
  incendioAreaToRequest,
  incendioSaveAllowed,
} from "../src/components/assessments/incendio/incendio-roundtrip.ts";

const persistedArea = {
  ambiente_id: "9ec4578c-ad37-46b9-84cd-268cabcc8b3f",
  nome_area: "Magazzino vernici",
  inf: 3,
  si: 2,
  pi: 2,
  note: "Porta REI da verificare",
  misure_prevenzione: "Controllo estintori\nAggiornare segnaletica",
  estintori_presenti: 4,
  idranti_presenti: 1,
  uscite_emergenza: 2,
};

test("fire assessment hydration preserves every editable persisted field", () => {
  assert.deepEqual(incendioAreaFromServer(persistedArea), {
    ambiente_id: "9ec4578c-ad37-46b9-84cd-268cabcc8b3f",
    nome: "Magazzino vernici",
    inf: 3,
    si: 2,
    pi: 2,
    note: "Porta REI da verificare",
    misure_prevenzione: "Controllo estintori\nAggiornare segnaletica",
    estintori_presenti: 4,
    idranti_presenti: 1,
    uscite_emergenza: 2,
  });
});

test("fire assessment save payload preserves every backend-supported field", () => {
  const formArea = incendioAreaFromServer(persistedArea);

  assert.deepEqual(incendioAreaToRequest(formArea), persistedArea);
});

test("nullable persisted text remains unconfigured and saves as null", () => {
  const emptyArea = incendioAreaFromServer({
    ...persistedArea,
    ambiente_id: null,
    nome_area: null,
    note: null,
    misure_prevenzione: null,
    estintori_presenti: 0,
    idranti_presenti: 0,
    uscite_emergenza: 0,
  });

  assert.equal(emptyArea.nome, "");
  assert.equal(emptyArea.note, "");
  assert.equal(emptyArea.misure_prevenzione, null);
  assert.deepEqual(incendioAreaToRequest(emptyArea), {
    ambiente_id: null,
    nome_area: null,
    inf: 3,
    si: 2,
    pi: 2,
    note: null,
    misure_prevenzione: null,
    estintori_presenti: 0,
    idranti_presenti: 0,
    uscite_emergenza: 0,
  });
});

test("linked rows display the canonical Ambiente name", () => {
  const linked = incendioAreaFromServer(
    { ...persistedArea, nome_area: null },
    "Magazzino vernici canonico",
  );

  assert.equal(linked.nome, "Magazzino vernici canonico");
  assert.equal(
    incendioAreaNameIsReadOnly(linked.ambiente_id, [persistedArea.ambiente_id]),
    true,
  );
  assert.equal(incendioAreaNameIsReadOnly(linked.ambiente_id, []), false);
});

test("an explicit empty recommendation selection survives save and reload", () => {
  const explicitNone = incendioAreaFromServer({
    ...persistedArea,
    misure_prevenzione: "",
  });

  assert.equal(explicitNone.misure_prevenzione, "");
  assert.equal(incendioAreaToRequest(explicitNone).misure_prevenzione, "");
});

test("fire assessment save is blocked whenever the full form is invalid", () => {
  assert.equal(
    incendioSaveAllowed({ allScoresComplete: true, formIsValid: false }),
    false,
  );
  assert.equal(
    incendioSaveAllowed({ allScoresComplete: true, formIsValid: true }),
    true,
  );
});
