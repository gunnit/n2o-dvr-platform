import assert from "node:assert/strict";
import test from "node:test";

import {
  loadRiskMasterEquipment,
} from "../src/app/(dashboard)/assessments/duvri/[aziendaId]/risk-master-equipment.ts";

test("Risk Master equipment loader joins, normalizes, and orders the company inventory", async () => {
  const paths = [];

  const rows = await loadRiskMasterEquipment("company-42", async (path) => {
    paths.push(path);
    if (path === "/api/v1/aziende/company-42/attrezzature") {
      return [
        {
          id: "equipment-4",
          azienda_id: "company-42",
          ambiente_id: "unknown-environment",
          descrizione: "  Generatore  ",
          marcatura_ce: true,
          verifiche_periodiche: false,
        },
        {
          id: "equipment-3",
          azienda_id: "company-42",
          ambiente_id: "warehouse",
          descrizione: "Trapano",
          marcatura_ce: true,
          verifiche_periodiche: true,
        },
        {
          id: "equipment-2",
          azienda_id: "company-42",
          ambiente_id: "office",
          descrizione: "  Avvitatore  ",
          marcatura_ce: false,
          verifiche_periodiche: false,
        },
        {
          id: "equipment-1",
          azienda_id: "company-42",
          ambiente_id: "office",
          descrizione: "Trapano",
          marcatura_ce: true,
          verifiche_periodiche: false,
        },
        {
          id: "equipment-0",
          azienda_id: "company-42",
          ambiente_id: "office",
          descrizione: "Trapano",
          marcatura_ce: true,
          verifiche_periodiche: false,
        },
        {
          id: "equipment-ignored",
          azienda_id: "company-42",
          ambiente_id: "office",
          descrizione: "   ",
          marcatura_ce: false,
          verifiche_periodiche: false,
        },
      ];
    }
    if (path === "/api/v1/aziende/company-42/ambienti") {
      return [
        {
          id: "office",
          azienda_id: "company-42",
          nome: "Ufficio",
          tipo: "Ufficio",
          superficie_mq: 32,
          preposto_id: null,
          descrizione_attivita: null,
          ordine: 0,
        },
        {
          id: "warehouse",
          azienda_id: "company-42",
          nome: "Magazzino",
          tipo: "Magazzino",
          superficie_mq: 80,
          preposto_id: null,
          descrizione_attivita: null,
          ordine: 1,
        },
      ];
    }
    throw new Error(`Unexpected endpoint: ${path}`);
  });

  assert.deepEqual(paths, [
    "/api/v1/aziende/company-42/attrezzature",
    "/api/v1/aziende/company-42/ambienti",
  ]);
  assert.deepEqual(rows, [
    {
      id: "equipment-4",
      description: "Generatore",
      environment: "Ambiente non disponibile",
    },
    {
      id: "equipment-3",
      description: "Trapano",
      environment: "Magazzino",
    },
    {
      id: "equipment-2",
      description: "Avvitatore",
      environment: "Ufficio",
    },
    {
      id: "equipment-0",
      description: "Trapano",
      environment: "Ufficio",
    },
    {
      id: "equipment-1",
      description: "Trapano",
      environment: "Ufficio",
    },
  ]);
});

test("Risk Master equipment loader rejects endpoint failures to its caller", async () => {
  await assert.rejects(
    loadRiskMasterEquipment("company-42", async () => {
      throw new Error("Servizio non raggiungibile");
    }),
    /Servizio non raggiungibile/,
  );
});
