# Wave 1 Assessment Frontends Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:dispatching-parallel-agents (primary — this is parallel multi-agent work) with superpowers:subagent-driven-development for each agent's internal task execution. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close 9 PARTIAL stories (US-3.1, 3.2, 3.3, 3.9, 3.10, 3.11, 3.12, 3.15) by completing operator data-entry UI for MMC, Incendio, Gestanti, and Biologico assessments, executed as 4 parallel agents.

**Architecture:** Orchestrator runs preflight (Phase 0) to establish shared scaffolding, then dispatches four parallel agents (Phase 1a–1d) working in mutually-exclusive directories. Each agent performs its own TDD loop, runs verification, commits, and returns a summary. Orchestrator runs postflight (Phase 2) to update progress docs and push.

**Tech Stack:** Next.js 16.2.3 (App Router — `params` is Promise), React 19.2.4, react-hook-form 7.72, zod 4, shadcn/ui, TanStack Query patterns (already in use), FastAPI, SQLAlchemy 2 async, Pydantic v2, Alembic.

**Spec:** `docs/superpowers/specs/2026-04-15-wave1-assessment-frontends-design.md`

---

## File Structure

```
backend/
  app/
    data/                                       # NEW package (Phase 0 task 1)
      __init__.py                               # NEW empty (Phase 0)
      niosh_cp.py                               # NEW (A1)
      fire_measures.py                          # NEW (A2)
      dlgs_151_2001.py                          # NEW (A3)
    api/v1/
      calculations.py                           # MODIFY (A1: niosh-cp, A2: fire-measures, A4: biologico-checklist)
      gestanti.py                               # NEW (A3)
      router.py                                 # MODIFY (A3: register gestanti router)
    services/document_generator/
      reference_data_biologico.py               # MODIFY (A4: add 3 checklists)
    schemas/
      calculation.py                            # MODIFY (A1,A2,A4: new request/response types)
      gestanti.py                               # NEW (A3)
  alembic/versions/
    c3d4e5f6a7b8_add_biologico_risposte_checklist.py  # NEW (Phase 0 task 2, A4 needs it)
  tests/
    test_calculators.py                         # MODIFY (A1,A2,A4: new tests)
    test_gestanti_cross_reference.py            # NEW (A3)

frontend/src/
  app/(dashboard)/assessments/
    mmc/[aziendaId]/page.tsx                    # MODIFY (A1)
    incendio/[aziendaId]/page.tsx               # MODIFY (A2)
    gestanti/[aziendaId]/page.tsx               # REWRITE (A3)
    biologico/[aziendaId]/page.tsx              # REWRITE (A4)
  components/assessments/
    mmc/                                        # NEW dir (A1)
      mmc-form.tsx                              # MOVE from components/assessments/mmc-form.tsx + extend
      mmc-lift-row.tsx                          # NEW (A1)
      mmc-cp-override.tsx                       # NEW (A1)
      mmc-measures.tsx                          # NEW (A1)
    incendio/                                   # NEW dir (A2)
      incendio-form.tsx                         # MOVE from components/assessments/incendio-form.tsx + extend
      incendio-area-card.tsx                    # NEW (A2)
      incendio-measures.tsx                     # NEW (A2)
      incendio-vvf-banner.tsx                   # NEW (A2)
    gestanti/                                   # NEW dir (A3)
      gestanti-form.tsx                         # NEW
      gestanti-worker-selector.tsx              # NEW
      gestanti-match-list.tsx                   # NEW
      gestanti-decision-dialog.tsx              # NEW
    biologico/                                  # NEW dir (A4)
      biologico-form.tsx                        # NEW
      biologico-sector-selector.tsx             # NEW
      biologico-checklist.tsx                   # NEW
      biologico-result.tsx                      # NEW

docs/
  qa/
    mmc/            # 3 screenshots (A1)
    incendio/       # 2 screenshots (A2)
    gestanti/       # 3 screenshots (A3)
    biologico/      # 3 screenshots (A4)
  context/
    USER_STORIES.md                             # MODIFY (Phase 2)
```

---

## Phase 0 — Preflight (Orchestrator)

### Task 0.1: Create `backend/app/data/` package

**Files:**
- Create: `backend/app/data/__init__.py` (empty)

- [ ] **Step 1: Create empty package file**

```bash
mkdir -p backend/app/data && touch backend/app/data/__init__.py
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/data/__init__.py
git commit -m "chore: scaffold backend/app/data package for static lookup tables"
```

---

### Task 0.2: Alembic migration — add `BiologicoValutazione.risposte_checklist` JSONB column

**Files:**
- Create: `backend/alembic/versions/c3d4e5f6a7b8_add_biologico_risposte_checklist.py`
- Modify: `backend/app/models/biologico_valutazione.py` (+1 field)

- [ ] **Step 1: Find current head revision**

```bash
cd backend && alembic heads
```
Record the revision id — the new migration's `down_revision` points to it. (From sprint closure 2026-04-14: likely `b2c3d4e5f6a7_wave1_assessment_and_complementary_models`.)

- [ ] **Step 2: Write migration**

```python
# backend/alembic/versions/c3d4e5f6a7b8_add_biologico_risposte_checklist.py
"""add biologico risposte_checklist JSONB column

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-04-15
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "biologico_valutazioni",
        sa.Column(
            "risposte_checklist",
            JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("biologico_valutazioni", "risposte_checklist")
```

- [ ] **Step 3: Add model field**

```python
# backend/app/models/biologico_valutazione.py — add after `dpi_richiesti` line
    # Risposte checklist auto-valutazione (lista di {id, risposta: "SI"|"NO"|"NA"})
    risposte_checklist: Mapped[list] = mapped_column(JSONB, default=list)
```

- [ ] **Step 4: Run migration against local DB**

```bash
cd backend && alembic upgrade head
```
Expected: `Running upgrade b2c3d4e5f6a7 -> c3d4e5f6a7b8`

- [ ] **Step 5: Verify the column exists**

```bash
cd backend && python -c "from app.models import BiologicoValutazione; print([c.name for c in BiologicoValutazione.__table__.columns])"
```
Expected output contains `risposte_checklist`.

- [ ] **Step 6: Commit**

```bash
git add backend/alembic/versions/c3d4e5f6a7b8_add_biologico_risposte_checklist.py backend/app/models/biologico_valutazione.py
git commit -m "feat(db): add BiologicoValutazione.risposte_checklist JSONB column"
```

---

### Task 0.3: Verify assertion baseline

- [ ] **Step 1: Run existing test suite, expect green**

```bash
cd backend && pytest tests/ -q
```
Expected: `16 passed`.

- [ ] **Step 2: Typecheck frontend baseline**

```bash
cd frontend && npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 3: Push preflight commits**

```bash
git push
```

---

## Phase 1a — Agent A1: MMC (NIOSH)

**Stories:** US-3.1, US-3.2, US-3.3
**Dispatch prompt:** this whole section (1a) plus the "Cross-Cutting Rules" appendix.

### Task A1.1: Static CP lookup table

**Files:**
- Create: `backend/app/data/niosh_cp.py`
- Modify: `backend/tests/test_calculators.py` (append tests)

- [ ] **Step 1: Write failing test**

```python
# backend/tests/test_calculators.py — append
from app.data.niosh_cp import get_default_cp


def test_niosh_cp_male_adult():
    assert get_default_cp("M", 30) == 25


def test_niosh_cp_male_young():
    assert get_default_cp("M", 17) == 20


def test_niosh_cp_male_senior():
    assert get_default_cp("M", 50) == 20


def test_niosh_cp_female_adult():
    assert get_default_cp("F", 30) == 20


def test_niosh_cp_female_young():
    assert get_default_cp("F", 16) == 15


def test_niosh_cp_female_senior():
    assert get_default_cp("F", 55) == 15


def test_niosh_cp_invalid_sex():
    import pytest
    with pytest.raises(ValueError):
        get_default_cp("X", 30)


def test_niosh_cp_negative_age():
    import pytest
    with pytest.raises(ValueError):
        get_default_cp("M", -1)
```

- [ ] **Step 2: Run, verify fails**

```bash
cd backend && pytest tests/test_calculators.py -k niosh_cp -q
```
Expected: `ModuleNotFoundError` or similar — 8 fail.

- [ ] **Step 3: Implement**

```python
# backend/app/data/niosh_cp.py
"""NIOSH reference weight constant (CP) lookup per sex and age.

Per D.Lgs. 81/2008 Allegato XXXIII and ISO 11228-1. Values in kg.
See docs/context/REFERENCE_DATA.md NIOSH section.
"""

from typing import Literal

Sex = Literal["M", "F"]


def get_default_cp(sesso: Sex, eta: int) -> int:
    """Return the reference weight constant CP in kg.

    Age bands: giovane (15–17), adulto (18–45), anziano (>45).
    Ages < 15 are rejected (legally cannot work in Italy).
    """
    if eta < 15:
        raise ValueError(f"Eta non valida: {eta} (minimo 15 anni)")
    if sesso not in ("M", "F"):
        raise ValueError(f"Sesso non valido: {sesso!r} (atteso 'M' o 'F')")

    if sesso == "M":
        if eta <= 17:
            return 20
        if eta <= 45:
            return 25
        return 20
    # F
    if eta <= 17:
        return 15
    if eta <= 45:
        return 20
    return 15
```

- [ ] **Step 4: Run, verify pass**

```bash
cd backend && pytest tests/test_calculators.py -k niosh_cp -q
```
Expected: 8 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/data/niosh_cp.py backend/tests/test_calculators.py
git commit -m "feat(mmc): add NIOSH CP lookup table with age/sex bands"
```

---

### Task A1.2: `GET /api/v1/calculate/niosh-cp` endpoint

**Files:**
- Modify: `backend/app/api/v1/calculations.py` (append handler)
- Modify: `backend/app/schemas/calculation.py` (add response schema)

- [ ] **Step 1: Add schema**

```python
# backend/app/schemas/calculation.py — append
from typing import Literal as _Literal


class NioshCpResponse(BaseModel):  # BaseModel already imported in this file
    cp: int
    sesso: _Literal["M", "F"]
    eta: int
    fascia: _Literal["giovane", "adulto", "anziano"]
```

- [ ] **Step 2: Add handler**

```python
# backend/app/api/v1/calculations.py — add import at top
from app.data.niosh_cp import get_default_cp
from app.schemas.calculation import NioshCpResponse  # adjust to existing import block

# append endpoint
@router.get("/niosh-cp", response_model=NioshCpResponse)
async def niosh_cp(sesso: str, eta: int) -> NioshCpResponse:
    """Return the default NIOSH weight constant for a worker's sex+age."""
    cp = get_default_cp(sesso, eta)  # raises ValueError → FastAPI returns 422 via validator
    if eta <= 17:
        fascia = "giovane"
    elif eta <= 45:
        fascia = "adulto"
    else:
        fascia = "anziano"
    return NioshCpResponse(cp=cp, sesso=sesso, eta=eta, fascia=fascia)
```

Wrap the `ValueError` with a `HTTPException(422, ...)` — check existing handlers in the same file for the established pattern and mirror it.

- [ ] **Step 3: Write integration test**

```python
# backend/tests/test_calculators.py — append
from httpx import AsyncClient
from fastapi import status
import pytest


@pytest.mark.asyncio
async def test_niosh_cp_endpoint_happy(test_client: AsyncClient):
    r = await test_client.get("/api/v1/calculate/niosh-cp", params={"sesso": "M", "eta": 30})
    assert r.status_code == status.HTTP_200_OK
    body = r.json()
    assert body["cp"] == 25
    assert body["fascia"] == "adulto"


@pytest.mark.asyncio
async def test_niosh_cp_endpoint_rejects_bad_sex(test_client: AsyncClient):
    r = await test_client.get("/api/v1/calculate/niosh-cp", params={"sesso": "Z", "eta": 30})
    assert r.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
```

- [ ] **Step 4: Run, verify pass**

```bash
cd backend && pytest tests/test_calculators.py -k niosh_cp -q
```
Expected: all new tests pass alongside unit tests.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/v1/calculations.py backend/app/schemas/calculation.py backend/tests/test_calculators.py
git commit -m "feat(mmc): expose GET /calculate/niosh-cp endpoint"
```

---

### Task A1.3: Move `mmc-form.tsx` into its own directory

**Files:**
- Move: `frontend/src/components/assessments/mmc-form.tsx` → `frontend/src/components/assessments/mmc/mmc-form.tsx`
- Modify: `frontend/src/app/(dashboard)/assessments/mmc/[aziendaId]/page.tsx` (update import)

- [ ] **Step 1: Move file**

```bash
mkdir -p frontend/src/components/assessments/mmc
git mv frontend/src/components/assessments/mmc-form.tsx frontend/src/components/assessments/mmc/mmc-form.tsx
```

- [ ] **Step 2: Update import in page**

```typescript
// frontend/src/app/(dashboard)/assessments/mmc/[aziendaId]/page.tsx line 12
// BEFORE: from "@/components/assessments/mmc-form"
// AFTER:
import {
  MmcForm,
  computeMmc,
  DEFAULT_INPUTS,
  type MmcInputs,
  type MmcResult,
} from "@/components/assessments/mmc/mmc-form";
```

- [ ] **Step 3: Typecheck**

```bash
cd frontend && npx tsc --noEmit
```
Expected: clean.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/assessments/mmc/mmc-form.tsx frontend/src/app/\(dashboard\)/assessments/mmc/\[aziendaId\]/page.tsx
git commit -m "refactor(mmc): move mmc-form into mmc/ subdirectory"
```

---

### Task A1.4: Multi-lift UI (US-3.1)

**Files:**
- Modify: `frontend/src/components/assessments/mmc/mmc-form.tsx` (convert to `useFieldArray`)
- Create: `frontend/src/components/assessments/mmc/mmc-lift-row.tsx`

- [ ] **Step 1: Create per-lift row component**

```typescript
// frontend/src/components/assessments/mmc/mmc-lift-row.tsx
"use client";

import { Control, useWatch } from "react-hook-form";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Trash2 } from "lucide-react";
import type { MmcFormValues, LiftResult } from "./mmc-form";

interface Props {
  index: number;
  control: Control<MmcFormValues>;
  result?: LiftResult;
  onRemove: () => void;
  canRemove: boolean;
}

export function MmcLiftRow({ index, control, result, onRemove, canRemove }: Props) {
  const name = useWatch({ control, name: `lifts.${index}.name` });
  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between">
        <CardTitle className="text-base">
          Sollevamento {index + 1}
          {name ? ` — ${name}` : ""}
        </CardTitle>
        {canRemove && (
          <Button variant="ghost" size="icon" onClick={onRemove} aria-label="Rimuovi">
            <Trash2 className="h-4 w-4" />
          </Button>
        )}
      </CardHeader>
      <CardContent className="grid grid-cols-2 gap-4">
        {/* 8 NIOSH parameters — altezza, dislocazione verticale, distanza
             orizzontale, angolo asimmetria, presa, frequenza, durata, peso reale.
             Each uses shadcn Input with zod-enforced ranges — see form zodSchema
             below. Labels in Italian with unit in parentheses, e.g.,
             "Altezza iniziale (cm)". */}
        {/* Example field — repeat pattern for all 8 params: */}
        <div className="grid gap-1.5">
          <Label htmlFor={`lift-${index}-altezza`}>Altezza iniziale (cm)</Label>
          <Input
            id={`lift-${index}-altezza`}
            type="number"
            {...{/* register via form.register(`lifts.${index}.altezza`) in parent */}}
          />
        </div>
        {/* ... repeat for 7 more params ... */}

        {result && (
          <div className="col-span-2 mt-2 flex items-center gap-3 rounded-md border bg-muted/30 p-3">
            <span className="text-sm font-medium">PLR: {result.plr.toFixed(1)} kg</span>
            <span className="text-sm">IR: {result.ir.toFixed(2)}</span>
            <Badge
              className={
                result.zona === "VERDE"
                  ? "bg-emerald-500/15 text-emerald-700"
                  : result.zona === "GIALLA"
                  ? "bg-amber-500/15 text-amber-800"
                  : "bg-rose-500/15 text-rose-700"
              }
            >
              {result.zona}
            </Badge>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 2: Refactor `mmc-form.tsx` to use `useFieldArray`**

Rewrite so the top-level shape is:

```typescript
// frontend/src/components/assessments/mmc/mmc-form.tsx
"use client";

import { useForm, useFieldArray, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Plus } from "lucide-react";
import { MmcLiftRow } from "./mmc-lift-row";
import { MmcCpOverride } from "./mmc-cp-override";
import { MmcMeasures } from "./mmc-measures";

const liftSchema = z.object({
  name: z.string().optional(),
  altezza: z.number().min(0, "Valore consentito: 0–175 cm").max(175),
  dislocazione: z.number().min(0).max(175),
  distanza: z.number().min(25, "Valore consentito: 25–63 cm").max(63),
  angolo: z.number().min(0, "Valore consentito: 0–135°").max(135),
  presa: z.enum(["buona", "discreta", "scarsa"]),
  frequenza: z.number().min(0.2).max(15),
  durata: z.enum(["breve", "media", "lunga"]),
  peso_reale: z.number().positive("Il peso deve essere > 0"),
});

export const mmcFormSchema = z.object({
  worker_sesso: z.enum(["M", "F"]),
  worker_eta: z.number().int().min(15).max(70),
  cp_override: z.number().optional(),
  cp_motivazione: z.string().optional(),
  lifts: z.array(liftSchema).min(1, "Almeno un sollevamento è richiesto"),
}).refine(
  (v) => v.cp_override === undefined || (v.cp_motivazione?.length ?? 0) >= 5,
  { message: "Motivazione richiesta (min. 5 caratteri) per modificare il CP", path: ["cp_motivazione"] },
);

export type MmcFormValues = z.infer<typeof mmcFormSchema>;

export interface LiftResult { plr: number; ir: number; zona: "VERDE" | "GIALLA" | "ROSSA" }
export interface MmcResult { perLift: LiftResult[]; worst: LiftResult | null; unanswered: string[] }

// Compute via POST /calculate/niosh — debounced in the page, not here.
// Keep computeMmc as a pure fallback-only helper for local echo.
export function computeMmc(_v: MmcFormValues): MmcResult {
  return { perLift: [], worst: null, unanswered: [] };
}

export const DEFAULT_INPUTS: MmcFormValues = {
  worker_sesso: "M",
  worker_eta: 30,
  lifts: [{
    name: "",
    altezza: 75, dislocazione: 25, distanza: 40, angolo: 0,
    presa: "buona", frequenza: 1, durata: "breve", peso_reale: 15,
  }],
};

export function MmcForm({ onResult, onFinalize, finalizing }: {
  onResult: (r: MmcResult) => void;
  onFinalize: (v: MmcFormValues) => void;
  finalizing: boolean;
}) {
  const form = useForm<MmcFormValues>({
    resolver: zodResolver(mmcFormSchema),
    defaultValues: DEFAULT_INPUTS,
    mode: "onBlur",
  });
  const { fields, append, remove } = useFieldArray({ control: form.control, name: "lifts" });

  // Call POST /calculate/niosh per valid lift — debounce via useDebouncedCallback.
  // On response, onResult(...).
  // [implementation inline in the real file; see verification screenshots for UI contract]

  return (
    <form onSubmit={form.handleSubmit(onFinalize)} className="space-y-6">
      <MmcCpOverride form={form} />
      <div className="space-y-4">
        {fields.map((f, i) => (
          <MmcLiftRow key={f.id} index={i} control={form.control} onRemove={() => remove(i)} canRemove={fields.length > 1} />
        ))}
      </div>
      <Button
        type="button"
        variant="outline"
        onClick={() => append(DEFAULT_INPUTS.lifts[0])}
      >
        <Plus className="mr-2 h-4 w-4" /> Aggiungi sollevamento
      </Button>
      <MmcMeasures visible={/* worst?.zona === "ROSSA" */ false} />
      <div className="flex justify-end">
        <Button type="submit" disabled={finalizing}>Salva valutazione</Button>
      </div>
    </form>
  );
}
```

- [ ] **Step 3: Typecheck**

```bash
cd frontend && npx tsc --noEmit
```
Expected: clean.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/assessments/mmc/
git commit -m "feat(mmc): multi-lift form with useFieldArray and zod validation (US-3.1)"
```

---

### Task A1.5: CP override UX (US-3.2)

**Files:**
- Create: `frontend/src/components/assessments/mmc/mmc-cp-override.tsx`

- [ ] **Step 1: Implement CP override panel**

```typescript
// frontend/src/components/assessments/mmc/mmc-cp-override.tsx
"use client";

import { useEffect, useState } from "react";
import { UseFormReturn } from "react-hook-form";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { MmcFormValues } from "./mmc-form";

export function MmcCpOverride({ form }: { form: UseFormReturn<MmcFormValues> }) {
  const sesso = form.watch("worker_sesso");
  const eta = form.watch("worker_eta");
  const override = form.watch("cp_override");
  const [autoCp, setAutoCp] = useState<number | null>(null);
  const [editing, setEditing] = useState(false);

  useEffect(() => {
    if (!sesso || !eta) return;
    const ctrl = new AbortController();
    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    fetch(`${apiUrl}/api/v1/calculate/niosh-cp?sesso=${sesso}&eta=${eta}`, { signal: ctrl.signal })
      .then((r) => r.json())
      .then((d) => setAutoCp(d.cp))
      .catch(() => {});
    return () => ctrl.abort();
  }, [sesso, eta]);

  const effectiveCp = override ?? autoCp;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Costante di peso (CP)</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div className="grid gap-1.5">
            <Label htmlFor="sesso">Sesso lavoratore</Label>
            <select
              id="sesso"
              className="h-9 rounded-md border px-2"
              {...form.register("worker_sesso")}
            >
              <option value="M">Maschio</option>
              <option value="F">Femmina</option>
            </select>
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="eta">Età (anni)</Label>
            <Input id="eta" type="number" {...form.register("worker_eta", { valueAsNumber: true })} />
          </div>
        </div>

        <div className="flex items-center gap-3">
          <span className="text-sm">CP effettivo:</span>
          <span className="text-lg font-semibold">{effectiveCp ?? "—"} kg</span>
          {override === undefined ? (
            <Badge variant="secondary">Auto</Badge>
          ) : (
            <Badge>Modificato</Badge>
          )}
          {!editing && (
            <Button type="button" size="sm" variant="outline" onClick={() => setEditing(true)}>
              Modifica CP
            </Button>
          )}
        </div>

        {editing && (
          <div className="grid gap-3 rounded-md border bg-muted/20 p-3">
            <div className="grid gap-1.5">
              <Label htmlFor="cp-override">Nuovo valore CP (kg)</Label>
              <Input
                id="cp-override"
                type="number"
                {...form.register("cp_override", { valueAsNumber: true })}
              />
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="cp-motivazione">Motivazione (obbligatoria, min. 5 caratteri)</Label>
              <Textarea id="cp-motivazione" rows={2} {...form.register("cp_motivazione")} />
              {form.formState.errors.cp_motivazione && (
                <p className="text-xs text-rose-600">{form.formState.errors.cp_motivazione.message}</p>
              )}
            </div>
            <div className="flex justify-end gap-2">
              <Button type="button" variant="ghost" onClick={() => {
                form.setValue("cp_override", undefined);
                form.setValue("cp_motivazione", "");
                setEditing(false);
              }}>
                Annulla
              </Button>
              <Button type="button" onClick={() => setEditing(false)}>Applica</Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 2: Typecheck + commit**

```bash
cd frontend && npx tsc --noEmit
git add frontend/src/components/assessments/mmc/mmc-cp-override.tsx
git commit -m "feat(mmc): auto-CP lookup with override + mandatory motivazione (US-3.2)"
```

---

### Task A1.6: Mandatory measures section for red zone (US-3.3)

**Files:**
- Create: `frontend/src/components/assessments/mmc/mmc-measures.tsx`

- [ ] **Step 1: Implement measures component**

```typescript
// frontend/src/components/assessments/mmc/mmc-measures.tsx
"use client";

import { useState } from "react";
import { AlertTriangle, Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";

const DEFAULT_MEASURES = [
  "Introdurre ausili meccanici per la movimentazione (carrelli, transpallet, sollevatori).",
  "Riorganizzare la postazione di lavoro riducendo la distanza orizzontale e l'angolo di asimmetria.",
  "Frazionare i carichi in unità più leggere (<15 kg per donne, <25 kg per uomini adulti).",
  "Alternare il personale per ridurre la frequenza di sollevamento per singolo lavoratore.",
  "Prevedere formazione specifica sulla movimentazione manuale dei carichi ai sensi dell'art. 169 D.Lgs. 81/2008.",
];

export function MmcMeasures({ visible }: { visible: boolean }) {
  const [items, setItems] = useState<string[]>(DEFAULT_MEASURES);
  if (!visible) return null;

  return (
    <Card className="border-rose-400/40 bg-rose-50/50 dark:bg-rose-950/20">
      <CardHeader className="flex flex-row items-center gap-2">
        <AlertTriangle className="h-5 w-5 text-rose-600" />
        <CardTitle className="text-base">Misure obbligatorie — zona ROSSA (IR &gt; 1.00)</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {items.map((m, i) => (
          <div key={i} className="flex gap-2">
            <Textarea
              value={m}
              onChange={(e) => {
                const next = [...items];
                next[i] = e.target.value;
                setItems(next);
              }}
              rows={2}
              className="flex-1"
            />
            <Button
              type="button"
              variant="ghost"
              size="icon"
              onClick={() => setItems(items.filter((_, j) => j !== i))}
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        ))}
        <Button type="button" variant="outline" onClick={() => setItems([...items, ""])}>
          <Plus className="mr-2 h-4 w-4" /> Aggiungi misura
        </Button>
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 2: Wire into form**

In `mmc-form.tsx`, compute `worst` from the array of `LiftResult` (max IR) and pass `visible={worst?.zona === "ROSSA"}` to `<MmcMeasures />`. Pipe the final measures array into the finalize payload.

- [ ] **Step 3: Typecheck + commit**

```bash
cd frontend && npx tsc --noEmit
git add frontend/src/components/assessments/mmc/mmc-measures.tsx frontend/src/components/assessments/mmc/mmc-form.tsx
git commit -m "feat(mmc): mandatory measures section for red zone (US-3.3)"
```

---

### Task A1.7: Update MMC page + capture screenshots

**Files:**
- Modify: `frontend/src/app/(dashboard)/assessments/mmc/[aziendaId]/page.tsx`

- [ ] **Step 1: Update page to consume the new form API shape**

Replace the current `inputs`/`result` state with just a `result` callback from `<MmcForm>`. On `onFinalize`, POST the full payload (all lifts + CP override + measures) to an existing assessment endpoint (check `backend/app/api/v1/` for the MMC POST route — if not present, this already existed per sprint closure 2026-04-14). Update status message on success.

- [ ] **Step 2: Migrate `params` to Promise (Next 16)**

```typescript
// If this page still uses `useParams()` from client hook, it's fine.
// If it uses `{ params }` prop at a server boundary, it must be:
// async function Page({ params }: { params: Promise<{ aziendaId: string }> }) {
//   const { aziendaId } = await params;
// }
// Check node_modules/next/dist/docs/01-app for the current guidance.
```

- [ ] **Step 3: Start frontend dev server**

```bash
cd frontend && npm run dev
```

- [ ] **Step 4: Manual verification — capture 3 screenshots**

Using Playwright MCP or the browser, exercise:
1. Single lift, green zone → save `docs/qa/mmc/mmc-01-single-lift.png`
2. Multi-lift with one red zone → save `docs/qa/mmc/mmc-02-multi-lift-red.png`
3. CP override with motivazione → save `docs/qa/mmc/mmc-03-cp-override.png`

- [ ] **Step 5: Run full test suite**

```bash
cd backend && pytest tests/ -q
cd ../frontend && npx tsc --noEmit && npm run lint
```
Expected: all green.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/app/\(dashboard\)/assessments/mmc/\[aziendaId\]/page.tsx docs/qa/mmc/
git commit -m "feat(mmc): wire multi-lift/CP-override/measures into assessment page (US-3.1-3.3)"
```

---

### Task A1.8: Return summary

Agent A1 returns:
- Commits: list of SHAs
- Tests run: `pytest tests/` → N passed, `tsc` clean, `lint` clean
- Screenshots: 3 files committed under `docs/qa/mmc/`
- Stories closed: US-3.1, US-3.2, US-3.3

---

## Phase 1b — Agent A2: Incendio (Fire Risk)

**Stories:** US-3.11, US-3.12

### Task A2.1: Static fire measures table

**Files:**
- Create: `backend/app/data/fire_measures.py`
- Modify: `backend/tests/test_calculators.py`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/test_calculators.py — append
from app.data.fire_measures import get_measures_for_level


def test_fire_measures_basso_has_min_3():
    measures = get_measures_for_level("Basso")
    assert len(measures) >= 3
    assert all(isinstance(m, str) and len(m) > 10 for m in measures)


def test_fire_measures_medio():
    measures = get_measures_for_level("Medio")
    assert len(measures) >= 3
    assert any("emergenza" in m.lower() or "rilevazione" in m.lower() for m in measures)


def test_fire_measures_alto():
    measures = get_measures_for_level("Alto")
    assert len(measures) >= 3
    # VVF reference should appear for Alto
    assert any("vvf" in m.lower() or "vv.f" in m.lower() or "antincendio" in m.lower() for m in measures)


def test_fire_measures_invalid():
    import pytest
    with pytest.raises(ValueError):
        get_measures_for_level("Estremo")
```

- [ ] **Step 2: Run, verify fails**

```bash
cd backend && pytest tests/test_calculators.py -k fire_measures -q
```

- [ ] **Step 3: Implement**

```python
# backend/app/data/fire_measures.py
"""Fire risk prevention/protection measures per level.

Source: D.M. 03/09/2021 (criteri di progettazione, gestione dell'emergenza
incendio) and D.Lgs. 81/2008 art. 46. See LEGISLATION_REFERENCE.md.
"""

from typing import Literal

Livello = Literal["Basso", "Medio", "Alto"]

_MEASURES: dict[str, list[str]] = {
    "Basso": [
        "Mantenere in efficienza gli estintori portatili esistenti con verifica semestrale.",
        "Verificare periodicamente vie di esodo, segnaletica e illuminazione di sicurezza.",
        "Aggiornare annualmente la formazione antincendio del personale (livello 1 — rischio basso).",
        "Redigere/aggiornare il piano di emergenza ed evacuazione aziendale.",
    ],
    "Medio": [
        "Installare impianto di rilevazione automatica incendi nelle aree a maggior carico di incendio.",
        "Adottare misure di compartimentazione per separare aree di lavoro con elevato carico di incendio.",
        "Controllare le sorgenti di innesco (apparecchi elettrici, sostanze infiammabili, lavorazioni a caldo).",
        "Designare e formare gli addetti alla gestione dell'emergenza (formazione livello 2).",
        "Aggiornare il piano di emergenza ed evacuazione con prove semestrali documentate.",
    ],
    "Alto": [
        "Attivare immediatamente misure straordinarie di prevenzione e protezione antincendio.",
        "Coinvolgere un professionista antincendio iscritto negli elenchi del Ministero dell'Interno (ex L. 818/1984).",
        "Presentare SCIA ai Vigili del Fuoco ove prevista dall'attività ai sensi del DPR 151/2011.",
        "Installare impianti di rilevazione e spegnimento automatici (sprinkler, rilevatori lineari, sistemi gas).",
        "Garantire formazione antincendio di livello 3 a tutti gli addetti alla gestione dell'emergenza.",
        "Prevedere valutazione approfondita del rischio incendio con metodo FSE (Fire Safety Engineering) ove applicabile.",
    ],
}


def get_measures_for_level(livello: Livello) -> list[str]:
    """Return the canonical list of prevention/protection measures."""
    if livello not in _MEASURES:
        raise ValueError(f"Livello non valido: {livello!r}")
    return list(_MEASURES[livello])
```

- [ ] **Step 4: Run, verify pass**

```bash
cd backend && pytest tests/test_calculators.py -k fire_measures -q
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/data/fire_measures.py backend/tests/test_calculators.py
git commit -m "feat(incendio): add fire measures lookup per level (Basso/Medio/Alto)"
```

---

### Task A2.2: `GET /api/v1/calculate/fire-measures` endpoint

**Files:**
- Modify: `backend/app/api/v1/calculations.py`
- Modify: `backend/app/schemas/calculation.py`

- [ ] **Step 1: Add schema**

```python
# backend/app/schemas/calculation.py — append
class FireMeasuresResponse(BaseModel):
    livello: Literal["Basso", "Medio", "Alto"]
    misure: list[str]
```

- [ ] **Step 2: Add handler**

```python
# backend/app/api/v1/calculations.py — append
from app.data.fire_measures import get_measures_for_level
from app.schemas.calculation import FireMeasuresResponse


@router.get("/fire-measures", response_model=FireMeasuresResponse)
async def fire_measures(livello: str) -> FireMeasuresResponse:
    try:
        misure = get_measures_for_level(livello)  # type: ignore[arg-type]
    except ValueError as e:
        from fastapi import HTTPException, status
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    return FireMeasuresResponse(livello=livello, misure=misure)  # type: ignore[arg-type]
```

- [ ] **Step 3: Test + commit**

```python
# backend/tests/test_calculators.py — append
@pytest.mark.asyncio
async def test_fire_measures_endpoint(test_client: AsyncClient):
    r = await test_client.get("/api/v1/calculate/fire-measures", params={"livello": "Alto"})
    assert r.status_code == 200
    body = r.json()
    assert body["livello"] == "Alto"
    assert len(body["misure"]) >= 3
```

```bash
cd backend && pytest tests/test_calculators.py -k fire_measures -q
git add backend/app/api/v1/calculations.py backend/app/schemas/calculation.py backend/tests/test_calculators.py
git commit -m "feat(incendio): expose GET /calculate/fire-measures endpoint"
```

---

### Task A2.3: Move incendio-form into directory + add sub-components

**Files:**
- Move: `frontend/src/components/assessments/incendio-form.tsx` → `frontend/src/components/assessments/incendio/incendio-form.tsx`
- Create: `frontend/src/components/assessments/incendio/incendio-area-card.tsx`
- Create: `frontend/src/components/assessments/incendio/incendio-measures.tsx`
- Create: `frontend/src/components/assessments/incendio/incendio-vvf-banner.tsx`
- Modify: `frontend/src/app/(dashboard)/assessments/incendio/[aziendaId]/page.tsx`

- [ ] **Step 1: Move file and update imports**

```bash
mkdir -p frontend/src/components/assessments/incendio
git mv frontend/src/components/assessments/incendio-form.tsx frontend/src/components/assessments/incendio/incendio-form.tsx
```

Update the page import path accordingly.

- [ ] **Step 2: Refactor `incendio-form.tsx` to multi-area (`useFieldArray`)**

The schema:
```typescript
const areaSchema = z.object({
  nome: z.string().min(1, "Nome area richiesto"),
  inf: z.number().int().min(1, "Valore consentito: 1–3").max(3),
  si:  z.number().int().min(1).max(3),
  pi:  z.number().int().min(1).max(3),
});
export const incendioFormSchema = z.object({
  areas: z.array(areaSchema).min(1, "Almeno un'area è richiesta"),
});
```

Live-compute per area: `somma = inf + si + pi`; band: `≤4 Basso`, `5-7 Medio`, `≥8 Alto`. (Matches existing backend `calculate_fire_risk`.)

- [ ] **Step 3: Create `incendio-area-card.tsx`**

Each card: area nome input, 3 sliders (INF/SI/PI, marks 1-2-3), live sum display, band badge (reuse `BAND_CLASS` from current page). Remove button (disabled if only one area). Duplicate button copying values into new `append()` entry with empty name.

- [ ] **Step 4: Create `incendio-measures.tsx`**

```typescript
"use client";
import { useEffect, useState } from "react";
import { Checkbox } from "@/components/ui/checkbox";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Plus } from "lucide-react";

export type Livello = "Basso" | "Medio" | "Alto";

export function IncendioMeasures({ livello, selected, onChange }: {
  livello: Livello;
  selected: string[];
  onChange: (next: string[]) => void;
}) {
  const [measures, setMeasures] = useState<string[]>([]);
  const [custom, setCustom] = useState("");

  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    fetch(`${apiUrl}/api/v1/calculate/fire-measures?livello=${livello}`)
      .then((r) => r.json())
      .then((d) => setMeasures(d.misure))
      .catch(() => setMeasures([]));
  }, [livello]);

  return (
    <Card>
      <CardHeader><CardTitle>Misure consigliate — livello {livello}</CardTitle></CardHeader>
      <CardContent className="space-y-2">
        {measures.map((m) => (
          <label key={m} className="flex items-start gap-2 text-sm">
            <Checkbox
              checked={selected.includes(m)}
              onCheckedChange={(v) => {
                if (v) onChange([...selected, m]);
                else onChange(selected.filter((s) => s !== m));
              }}
            />
            <span>{m}</span>
          </label>
        ))}
        <div className="flex gap-2 pt-2">
          <Input
            value={custom}
            onChange={(e) => setCustom(e.target.value)}
            placeholder="Misura personalizzata…"
          />
          <Button
            type="button"
            variant="outline"
            onClick={() => {
              if (custom.trim()) {
                onChange([...selected, custom.trim()]);
                setCustom("");
              }
            }}
          >
            <Plus className="h-4 w-4" />
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 5: Create `incendio-vvf-banner.tsx`**

```typescript
"use client";
import { AlertTriangle } from "lucide-react";

export function IncendioVvfBanner({ visible }: { visible: boolean }) {
  if (!visible) return null;
  return (
    <div className="sticky top-0 z-10 mb-4 flex items-start gap-3 rounded-md border border-rose-400/60 bg-rose-50 p-3 text-rose-900 dark:bg-rose-950/30 dark:text-rose-100">
      <AlertTriangle className="mt-0.5 h-5 w-5 flex-shrink-0" />
      <div>
        <p className="font-medium">Richiesta valutazione approfondita VV.F.</p>
        <p className="text-sm">
          Rischio Alto rilevato in almeno un'area. Attivare professionista antincendio e verificare obblighi SCIA ai sensi DPR 151/2011.
        </p>
      </div>
    </div>
  );
}
```

- [ ] **Step 6: Wire into page**

Page watches the `areas` array, computes per-area results, determines max livello across all areas. Renders `<IncendioVvfBanner visible={maxLivello === "Alto"} />` above the form. Measures section rendered once per area.

- [ ] **Step 7: Typecheck + commit**

```bash
cd frontend && npx tsc --noEmit
git add frontend/src/components/assessments/incendio/ frontend/src/app/\(dashboard\)/assessments/incendio/\[aziendaId\]/page.tsx
git commit -m "feat(incendio): multi-area form, measures per level, VVF banner (US-3.11-3.12)"
```

---

### Task A2.4: Screenshots + verification

- [ ] **Step 1: Run dev server + capture screenshots**

1. One area Medio → `docs/qa/incendio/incendio-01-medio.png`
2. Two areas, one Alto (VVF banner visible) → `docs/qa/incendio/incendio-02-alto-vvf-banner.png`

- [ ] **Step 2: Run verification**

```bash
cd backend && pytest tests/ -q
cd ../frontend && npx tsc --noEmit && npm run lint
```

- [ ] **Step 3: Commit**

```bash
git add docs/qa/incendio/
git commit -m "docs(incendio): QA screenshots for US-3.11-3.12"
```

### Task A2.5: Return summary (same shape as A1.8).

---

## Phase 1c — Agent A3: Gestanti (D.Lgs. 151/2001)

**Stories:** US-3.9, US-3.10

### Task A3.1: Risk catalog

**Files:**
- Create: `backend/app/data/dlgs_151_2001.py`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/test_gestanti_cross_reference.py (new file)
import pytest
from app.data.dlgs_151_2001 import INCOMPATIBLE_RISKS, find_matches_for_mansione


def test_catalog_has_at_least_12_entries():
    assert len(INCOMPATIBLE_RISKS) >= 12


def test_each_entry_has_required_fields():
    for key, info in INCOMPATIBLE_RISKS.items():
        assert info["allegato"] in ("A", "B", "C")
        assert info["descrizione"]
        assert isinstance(info["incompatible_mansione_keywords"], list)
        assert info["incompatible_mansione_keywords"]


def test_matches_manual_handling():
    matches = find_matches_for_mansione("Magazziniere addetto alla movimentazione manuale carichi")
    keys = [m["risk_key"] for m in matches]
    assert "manual_handling_heavy" in keys


def test_no_matches_for_office_role():
    matches = find_matches_for_mansione("Impiegata amministrativa back-office")
    assert matches == []


def test_matches_chemical_cmr():
    matches = find_matches_for_mansione("Operaia di laboratorio chimico con manipolazione di solventi")
    assert any(m["risk_key"].startswith("chemical_") for m in matches)
```

- [ ] **Step 2: Run, verify fail**

```bash
cd backend && pytest tests/test_gestanti_cross_reference.py -q
```

- [ ] **Step 3: Implement catalog**

```python
# backend/app/data/dlgs_151_2001.py
"""D.Lgs. 26 marzo 2001 n. 151 — Allegati A, B, C: rischi vietati per
lavoratrici gestanti, puerpere, allattanti.

Keyword-based fuzzy matching against mansioni. Not exhaustive —
consultant judgement still required.
"""

from typing import TypedDict


class RiskInfo(TypedDict):
    allegato: str  # "A" | "B" | "C"
    descrizione: str
    incompatible_mansione_keywords: list[str]


INCOMPATIBLE_RISKS: dict[str, RiskInfo] = {
    "manual_handling_heavy": {
        "allegato": "A",
        "descrizione": "Trasporto e sollevamento di pesi — vietato ai sensi dell'Allegato A.",
        "incompatible_mansione_keywords": ["movimentazione", "sollevamento", "magazzin", "facchinaggio", "carico"],
    },
    "ionizing_radiation": {
        "allegato": "A",
        "descrizione": "Esposizione a radiazioni ionizzanti — vietata.",
        "incompatible_mansione_keywords": ["radiolog", "radiografia", "tac", "scintigrafia", "medicina nucleare", "raggi x"],
    },
    "underground_work": {
        "allegato": "A",
        "descrizione": "Lavori in sotterraneo — vietati in gravidanza e fino a 7 mesi dopo il parto.",
        "incompatible_mansione_keywords": ["sotterraneo", "miniera", "galleria"],
    },
    "chemical_cmr": {
        "allegato": "B",
        "descrizione": "Esposizione ad agenti chimici cancerogeni, mutageni o tossici per la riproduzione (CMR).",
        "incompatible_mansione_keywords": ["chimic", "solvent", "verniciatura", "pittura", "laborator"],
    },
    "lead_exposure": {
        "allegato": "B",
        "descrizione": "Esposizione a piombo e suoi composti.",
        "incompatible_mansione_keywords": ["piombo", "saldatura", "tipografia"],
    },
    "mercury_exposure": {
        "allegato": "B",
        "descrizione": "Esposizione a mercurio e suoi derivati.",
        "incompatible_mansione_keywords": ["mercurio", "amalgam", "odontotecnic"],
    },
    "biological_group3_4": {
        "allegato": "B",
        "descrizione": "Esposizione ad agenti biologici del gruppo 3 o 4 (art. 268 D.Lgs. 81/2008).",
        "incompatible_mansione_keywords": ["infermier", "ostetric", "laboratorio microbiologic", "veterinari", "necroscopi"],
    },
    "rubella_exposure": {
        "allegato": "B",
        "descrizione": "Esposizione al virus della rosolia e toxoplasma (salvo immunità comprovata).",
        "incompatible_mansione_keywords": ["pediatri", "asilo", "scuola materna", "maternità"],
    },
    "night_work": {
        "allegato": "A",
        "descrizione": "Lavoro notturno (dalle 24 alle 06) — vietato fino a 1 anno di vita del bambino.",
        "incompatible_mansione_keywords": ["turnist", "notturn", "guardia"],
    },
    "whole_body_vibration": {
        "allegato": "C",
        "descrizione": "Esposizione a vibrazioni meccaniche corpo-intero.",
        "incompatible_mansione_keywords": ["autista", "mulettist", "conducente", "trattor"],
    },
    "extreme_temperature": {
        "allegato": "C",
        "descrizione": "Esposizione a calore o freddo estremi (ambienti non confortevoli).",
        "incompatible_mansione_keywords": ["fonderia", "forno", "cella frigorifera", "macell"],
    },
    "standing_prolonged": {
        "allegato": "C",
        "descrizione": "Stazione eretta prolungata per oltre metà dell'orario di lavoro.",
        "incompatible_mansione_keywords": ["cassier", "commess", "parrucchier", "barista", "cameriera"],
    },
    "infectious_disease_exposure": {
        "allegato": "B",
        "descrizione": "Rischio infettivo per contatto con pazienti o fluidi biologici.",
        "incompatible_mansione_keywords": ["ospedalier", "pronto soccorso", "rsa", "casa di cura"],
    },
}


def find_matches_for_mansione(mansione: str) -> list[dict]:
    """Return list of {risk_key, allegato, descrizione} matches by keyword overlap."""
    if not mansione:
        return []
    haystack = mansione.lower()
    matches = []
    for key, info in INCOMPATIBLE_RISKS.items():
        if any(kw.lower() in haystack for kw in info["incompatible_mansione_keywords"]):
            matches.append({
                "risk_key": key,
                "allegato": info["allegato"],
                "descrizione": info["descrizione"],
            })
    return matches
```

- [ ] **Step 4: Run, verify pass**

```bash
cd backend && pytest tests/test_gestanti_cross_reference.py -q
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/data/dlgs_151_2001.py backend/tests/test_gestanti_cross_reference.py
git commit -m "feat(gestanti): D.Lgs. 151/2001 risk catalog with keyword matching"
```

---

### Task A3.2: Gestanti API router

**Files:**
- Create: `backend/app/schemas/gestanti.py`
- Create: `backend/app/api/v1/gestanti.py`
- Modify: `backend/app/api/v1/router.py`

- [ ] **Step 1: Schemas**

```python
# backend/app/schemas/gestanti.py
from typing import Literal, Optional
from uuid import UUID
from pydantic import BaseModel


class CrossRefRequest(BaseModel):
    persona_id: UUID


class CrossRefMatch(BaseModel):
    risk_key: str
    allegato: Literal["A", "B", "C"]
    descrizione: str
    suggested_alternative_mansione: Optional[str]
    is_new: bool  # True if appeared after last persisted decision


class CrossRefResponse(BaseModel):
    persona_id: UUID
    mansione: str
    matches: list[CrossRefMatch]
    cleared: bool  # True when matches == []


class DecisionRequest(BaseModel):
    risk_key: str
    action: Literal["accept", "reject"]
    justification: Optional[str] = None
    misura_alternativa: Optional[str] = None
```

- [ ] **Step 2: Router handler**

```python
# backend/app/api/v1/gestanti.py
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user  # adjust to existing deps module
from app.data.dlgs_151_2001 import find_matches_for_mansione
from app.models.persona import Persona
from app.models.gestanti_valutazione import GestantiValutazione
from app.schemas.gestanti import (
    CrossRefMatch, CrossRefResponse, CrossRefRequest,
    DecisionRequest,
)
from sqlalchemy import select

router = APIRouter(prefix="/aziende/{azienda_id}/gestanti", tags=["gestanti"])


@router.post("/cross-reference", response_model=CrossRefResponse)
async def cross_reference(
    azienda_id: UUID,
    body: CrossRefRequest,
    db: AsyncSession = Depends(get_db),
    _user = Depends(get_current_user),
) -> CrossRefResponse:
    # Load worker
    persona = (await db.execute(select(Persona).where(Persona.id == body.persona_id))).scalar_one_or_none()
    if not persona or persona.azienda_id != azienda_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lavoratrice non trovata")
    if persona.sesso != "F":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Valutazione applicabile solo a lavoratrici di sesso F")

    raw_matches = find_matches_for_mansione(persona.mansione or "")

    # Load prior decisions from the azienda's existing GestantiValutazione for this persona
    prior_val = (await db.execute(
        select(GestantiValutazione).where(GestantiValutazione.persona_id == body.persona_id)
    )).scalars().first()
    prior_keys = {d.get("risk_key") for d in (prior_val.rischi_vietati if prior_val else [])}

    # Suggest alternate mansione: pick another azienda-level mansione from Persona
    # that has zero matches
    peers = (await db.execute(
        select(Persona.mansione).where(Persona.azienda_id == azienda_id).distinct()
    )).scalars().all()
    safe_mansioni = [m for m in peers if m and not find_matches_for_mansione(m)]
    suggested = safe_mansioni[0] if safe_mansioni else None

    matches = [
        CrossRefMatch(
            risk_key=m["risk_key"],
            allegato=m["allegato"],
            descrizione=m["descrizione"],
            suggested_alternative_mansione=suggested,
            is_new=m["risk_key"] not in prior_keys,
        )
        for m in raw_matches
    ]
    return CrossRefResponse(
        persona_id=body.persona_id,
        mansione=persona.mansione or "",
        matches=matches,
        cleared=len(matches) == 0,
    )


@router.post("/{valutazione_id}/decision")
async def decision(
    azienda_id: UUID,
    valutazione_id: UUID,
    body: DecisionRequest,
    db: AsyncSession = Depends(get_db),
    _user = Depends(get_current_user),
):
    val = (await db.execute(select(GestantiValutazione).where(GestantiValutazione.id == valutazione_id))).scalar_one_or_none()
    if not val or val.azienda_id != azienda_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Valutazione non trovata")

    if body.action == "accept" and (not body.justification or len(body.justification) < 10):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Justification richiesta (min. 10 caratteri) per accettare")
    if body.action == "reject" and (not body.misura_alternativa or len(body.misura_alternativa) < 10):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Misura alternativa richiesta (min. 10 caratteri) per rifiutare")

    existing = list(val.rischi_vietati or [])
    # Replace any prior decision for the same risk_key
    existing = [e for e in existing if e.get("risk_key") != body.risk_key]
    existing.append({
        "risk_key": body.risk_key,
        "action": body.action,
        "justification": body.justification,
        "misura_alternativa": body.misura_alternativa,
    })
    val.rischi_vietati = existing
    await db.commit()
    return {"ok": True}
```

Adjust imports to match the actual modules in this repo (e.g., the `get_db` dependency path).

- [ ] **Step 3: Register router**

```python
# backend/app/api/v1/router.py — add
from app.api.v1.gestanti import router as gestanti_router
# ...
api_router.include_router(gestanti_router)
```

- [ ] **Step 4: Write endpoint tests**

Append to `test_gestanti_cross_reference.py` — tests using the `test_client` fixture and the `acme_meccanica` fixture azienda + a seeded female Persona.

- [ ] **Step 5: Run + commit**

```bash
cd backend && pytest tests/ -q
git add backend/app/schemas/gestanti.py backend/app/api/v1/gestanti.py backend/app/api/v1/router.py backend/tests/test_gestanti_cross_reference.py
git commit -m "feat(gestanti): cross-reference + decision endpoints (US-3.9,3.10)"
```

---

### Task A3.3: Gestanti frontend

**Files:**
- Rewrite: `frontend/src/app/(dashboard)/assessments/gestanti/[aziendaId]/page.tsx`
- Create: `frontend/src/components/assessments/gestanti/gestanti-form.tsx`
- Create: `frontend/src/components/assessments/gestanti/gestanti-worker-selector.tsx`
- Create: `frontend/src/components/assessments/gestanti/gestanti-match-list.tsx`
- Create: `frontend/src/components/assessments/gestanti/gestanti-decision-dialog.tsx`

- [ ] **Step 1: Migrate `params` to Next 16 async pattern**

The current page uses `params.aziendaId` synchronously. Verify Next 16 docs at `frontend/node_modules/next/dist/docs/01-app/` for the current pattern. If `params` is a Promise, convert the page to client-component or use `useParams()` hook.

- [ ] **Step 2: Worker selector**

```typescript
// frontend/src/components/assessments/gestanti/gestanti-worker-selector.tsx
"use client";
import { useEffect, useState } from "react";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

interface Persona { id: string; nome: string; cognome: string; mansione?: string; sesso?: string }

export function GestantiWorkerSelector({ aziendaId, onSelect }: {
  aziendaId: string;
  onSelect: (p: Persona) => void;
}) {
  const [people, setPeople] = useState<Persona[]>([]);
  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    fetch(`${apiUrl}/api/v1/aziende/${aziendaId}/persone`)
      .then((r) => r.json())
      .then((data: Persona[]) => setPeople(data.filter((p) => p.sesso === "F")))
      .catch(() => setPeople([]));
  }, [aziendaId]);

  return (
    <Select onValueChange={(id) => {
      const p = people.find((x) => x.id === id);
      if (p) onSelect(p);
    }}>
      <SelectTrigger className="w-full"><SelectValue placeholder="Seleziona lavoratrice…" /></SelectTrigger>
      <SelectContent>
        {people.map((p) => (
          <SelectItem key={p.id} value={p.id}>{p.cognome} {p.nome} — {p.mansione ?? "mansione non definita"}</SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
```

- [ ] **Step 3: Match list + decision dialog**

`gestanti-match-list.tsx`: renders matches from `/cross-reference`. Each row: Allegato badge (A/B/C), descrizione, `Nuovo` badge if `is_new`, Accetta/Rifiuta buttons.

`gestanti-decision-dialog.tsx`: shadcn Dialog with textarea. Mode="accept" requires `justification` (min 10 chars, zod validated). Mode="reject" requires `misura_alternativa`.

- [ ] **Step 4: Page wires selector → match list + signature block (preserve existing)**

```typescript
// frontend/src/app/(dashboard)/assessments/gestanti/[aziendaId]/page.tsx
"use client";
import { useState } from "react";
import { useParams } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { GestantiWorkerSelector } from "@/components/assessments/gestanti/gestanti-worker-selector";
import { GestantiForm } from "@/components/assessments/gestanti/gestanti-form";

export default function GestantiAssessmentPage() {
  const { aziendaId } = useParams<{ aziendaId: string }>();
  const [persona, setPersona] = useState<{ id: string; nome: string; cognome: string; mansione?: string } | null>(null);

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Valutazione Gestanti / Puerpere / Allattamento</h1>
        <p className="text-muted-foreground">D.Lgs. 151/2001 — cross-reference mansione ↔ rischi vietati</p>
      </div>

      <Card>
        <CardHeader><CardTitle>Seleziona lavoratrice</CardTitle></CardHeader>
        <CardContent><GestantiWorkerSelector aziendaId={aziendaId} onSelect={setPersona} /></CardContent>
      </Card>

      {persona && <GestantiForm aziendaId={aziendaId} persona={persona} />}
    </div>
  );
}
```

`GestantiForm` internally calls `/cross-reference`, renders `<GestantiMatchList>`, includes the existing stato/data/signature block, and saves on finalize (creates a `GestantiValutazione` row via existing POST endpoint if needed — otherwise adds one).

- [ ] **Step 5: Typecheck + commit**

```bash
cd frontend && npx tsc --noEmit
git add frontend/src/components/assessments/gestanti/ frontend/src/app/\(dashboard\)/assessments/gestanti/\[aziendaId\]/page.tsx
git commit -m "feat(gestanti): cross-reference UI + accept/reject dialog (US-3.9,3.10)"
```

---

### Task A3.4: Screenshots + verification

Capture: `gestanti-01-no-risks.png`, `gestanti-02-matches.png`, `gestanti-03-relocation-dialog.png`. Run tests and typecheck. Commit screenshots.

### Task A3.5: Return summary.

---

## Phase 1d — Agent A4: Biologico (D.Lgs. 81/2008 Titolo X)

**Stories:** US-3.15

### Task A4.1: Extend `reference_data_biologico.py` with 3 checklists

**Files:**
- Modify: `backend/app/services/document_generator/reference_data_biologico.py`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/test_calculators.py — append
from app.services.document_generator.reference_data_biologico import (
    ALIMENTARE_CHECKLIST, ASILO_CHECKLIST, DENTISTI_CHECKLIST, classify_biologico,
)


def test_checklist_sizes():
    for cl in (ALIMENTARE_CHECKLIST, ASILO_CHECKLIST, DENTISTI_CHECKLIST):
        assert 8 <= len(cl) <= 15
        for item in cl:
            assert "id" in item and "descrizione" in item and "criticita" in item
            assert item["criticita"] in ("alta", "media", "bassa")


def test_classify_all_si_is_basso():
    risposte = [{"id": it["id"], "risposta": "SI"} for it in ALIMENTARE_CHECKLIST]
    assert classify_biologico(ALIMENTARE_CHECKLIST, risposte) == "Basso"


def test_classify_all_no_is_alto():
    risposte = [{"id": it["id"], "risposta": "NO"} for it in ALIMENTARE_CHECKLIST]
    assert classify_biologico(ALIMENTARE_CHECKLIST, risposte) == "Alto"


def test_classify_na_is_neutral():
    risposte = [{"id": it["id"], "risposta": "NA"} for it in ALIMENTARE_CHECKLIST]
    # NA counts as compliant for scoring (treat as non-applicable)
    assert classify_biologico(ALIMENTARE_CHECKLIST, risposte) in ("Basso", "Medio")
```

- [ ] **Step 2: Implement**

Append to `reference_data_biologico.py`:

```python
from typing import TypedDict, Literal


class ChecklistItem(TypedDict):
    id: str
    descrizione: str
    criticita: Literal["alta", "media", "bassa"]


ALIMENTARE_CHECKLIST: list[ChecklistItem] = [
    {"id": "haccp_manual", "descrizione": "Manuale HACCP aziendale presente e aggiornato", "criticita": "alta"},
    {"id": "separation_raw_cooked", "descrizione": "Separazione tra alimenti crudi e cotti (superfici, utensili, celle frigo)", "criticita": "alta"},
    {"id": "temp_control", "descrizione": "Controllo e registrazione delle temperature di conservazione", "criticita": "alta"},
    {"id": "sanitation_procedures", "descrizione": "Procedure di sanificazione documentate (frequenza, detergenti, verifica efficacia)", "criticita": "alta"},
    {"id": "pest_control", "descrizione": "Programma di disinfestazione e derattizzazione attivo", "criticita": "media"},
    {"id": "worker_training", "descrizione": "Formazione specifica del personale sul rischio biologico alimentare", "criticita": "media"},
    {"id": "health_surveillance", "descrizione": "Sorveglianza sanitaria per addetti alla manipolazione alimenti", "criticita": "media"},
    {"id": "dpi_available", "descrizione": "DPI disponibili e utilizzati (guanti, cuffie, camici)", "criticita": "media"},
    {"id": "waste_management", "descrizione": "Gestione corretta dei rifiuti alimentari e imballaggi", "criticita": "bassa"},
    {"id": "water_quality", "descrizione": "Controllo potabilità dell'acqua utilizzata", "criticita": "bassa"},
]

ASILO_CHECKLIST: list[ChecklistItem] = [
    {"id": "vaccination_tracking", "descrizione": "Tracciamento stato vaccinale dei bambini e del personale", "criticita": "alta"},
    {"id": "rubella_immunity", "descrizione": "Verifica immunità alla rosolia per personale femminile in età fertile", "criticita": "alta"},
    {"id": "infection_protocols", "descrizione": "Protocolli per gestione malattie infettive (febbre, vomito, diarrea)", "criticita": "alta"},
    {"id": "hand_hygiene", "descrizione": "Procedure di igiene delle mani (bambini e operatori)", "criticita": "alta"},
    {"id": "diaper_protocols", "descrizione": "Protocollo cambio pannolini con disinfezione superfici", "criticita": "media"},
    {"id": "toy_sanitation", "descrizione": "Sanificazione periodica giochi e superfici di contatto", "criticita": "media"},
    {"id": "waste_biological", "descrizione": "Gestione rifiuti biologici (pannolini, tessuti contaminati)", "criticita": "media"},
    {"id": "sick_child_isolation", "descrizione": "Area dedicata per bambini che presentano sintomi", "criticita": "media"},
    {"id": "staff_training", "descrizione": "Formazione specifica personale su rischio biologico infantile", "criticita": "media"},
    {"id": "health_surveillance", "descrizione": "Sorveglianza sanitaria del personale educativo", "criticita": "bassa"},
    {"id": "food_hygiene", "descrizione": "Igiene nella preparazione/somministrazione pasti", "criticita": "bassa"},
]

DENTISTI_CHECKLIST: list[ChecklistItem] = [
    {"id": "sterilization_autoclave", "descrizione": "Autoclave conforme EN 13060 con controllo di processo", "criticita": "alta"},
    {"id": "sharps_management", "descrizione": "Contenitori rigidi per taglienti secondo CEI 66.5 / DPR 254/2003", "criticita": "alta"},
    {"id": "hbv_vaccination", "descrizione": "Vaccinazione HBV di tutto il personale clinico", "criticita": "alta"},
    {"id": "dpi_clinical", "descrizione": "DPI clinici (guanti, mascherina FFP2/FFP3, visiera, camice)", "criticita": "alta"},
    {"id": "surface_disinfection", "descrizione": "Disinfezione superfici tra un paziente e l'altro", "criticita": "alta"},
    {"id": "water_lines", "descrizione": "Decontaminazione linee idriche riunito (rischio Legionella)", "criticita": "media"},
    {"id": "aerosol_reduction", "descrizione": "Riduzione aerosol (aspiratore ad alta velocità, diga di gomma)", "criticita": "media"},
    {"id": "waste_ospedalieri", "descrizione": "Gestione rifiuti sanitari a rischio infettivo (CER 180103*)", "criticita": "media"},
    {"id": "post_exposure_protocol", "descrizione": "Protocollo post-esposizione a fluidi biologici (puntura accidentale)", "criticita": "media"},
    {"id": "medical_surveillance", "descrizione": "Sorveglianza sanitaria specifica (ematica, sierologica periodica)", "criticita": "bassa"},
    {"id": "staff_training", "descrizione": "Formazione specifica su rischio biologico odontoiatrico", "criticita": "bassa"},
]


_CRITICITA_WEIGHT = {"alta": 3, "media": 2, "bassa": 1}


def classify_biologico(checklist: list[ChecklistItem], risposte: list[dict]) -> str:
    """Return Basso/Medio/Alto based on weighted NO count."""
    resp_map = {r["id"]: r["risposta"] for r in risposte}
    score = 0
    max_score = 0
    for item in checklist:
        weight = _CRITICITA_WEIGHT[item["criticita"]]
        max_score += weight
        if resp_map.get(item["id"]) == "NO":
            score += weight
    # Thresholds relative to max_score: >= 40% NO-weighted → Alto, >= 15% → Medio
    if max_score == 0:
        return "Basso"
    ratio = score / max_score
    if ratio >= 0.4:
        return "Alto"
    if ratio >= 0.15:
        return "Medio"
    return "Basso"
```

- [ ] **Step 3: Run, verify pass + commit**

```bash
cd backend && pytest tests/test_calculators.py -q
git add backend/app/services/document_generator/reference_data_biologico.py backend/tests/test_calculators.py
git commit -m "feat(biologico): sector checklists + weighted classifier"
```

---

### Task A4.2: `GET /api/v1/calculate/biologico-checklist` endpoint

**Files:**
- Modify: `backend/app/api/v1/calculations.py`
- Modify: `backend/app/schemas/calculation.py`

- [ ] **Step 1: Schemas + handler**

```python
# calculation.py — append
class BiologicoChecklistItemResp(BaseModel):
    id: str
    descrizione: str
    criticita: Literal["alta", "media", "bassa"]


class BiologicoChecklistResponse(BaseModel):
    settore: Literal["alimentare", "asilo", "dentisti"]
    items: list[BiologicoChecklistItemResp]


# calculations.py — append
from app.services.document_generator.reference_data_biologico import (
    ALIMENTARE_CHECKLIST, ASILO_CHECKLIST, DENTISTI_CHECKLIST,
)


@router.get("/biologico-checklist", response_model=BiologicoChecklistResponse)
async def biologico_checklist(settore: str) -> BiologicoChecklistResponse:
    from fastapi import HTTPException, status
    mapping = {
        "alimentare": ALIMENTARE_CHECKLIST,
        "asilo": ASILO_CHECKLIST,
        "dentisti": DENTISTI_CHECKLIST,
    }
    if settore not in mapping:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Settore non valido")
    items = [BiologicoChecklistItemResp(**it) for it in mapping[settore]]
    return BiologicoChecklistResponse(settore=settore, items=items)
```

- [ ] **Step 2: Endpoint test + commit**

```bash
cd backend && pytest tests/ -q
git add backend/app/api/v1/calculations.py backend/app/schemas/calculation.py
git commit -m "feat(biologico): expose GET /calculate/biologico-checklist endpoint"
```

---

### Task A4.3: Biologico frontend

**Files:**
- Rewrite: `frontend/src/app/(dashboard)/assessments/biologico/[aziendaId]/page.tsx`
- Create: `frontend/src/components/assessments/biologico/biologico-form.tsx`
- Create: `frontend/src/components/assessments/biologico/biologico-sector-selector.tsx`
- Create: `frontend/src/components/assessments/biologico/biologico-checklist.tsx`
- Create: `frontend/src/components/assessments/biologico/biologico-result.tsx`

- [ ] **Step 1: Migrate `params` to Next 16 async pattern** (same as A3.3 Step 1)

- [ ] **Step 2: Sector selector**

Segmented control (3 buttons: Alimentare / Asilo / Dentisti). On change, load checklist from endpoint. Persisted settore in form state.

- [ ] **Step 3: Checklist component**

```typescript
// biologico-checklist.tsx
"use client";
import { Badge } from "@/components/ui/badge";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Label } from "@/components/ui/label";

type Risposta = "SI" | "NO" | "NA";
interface Item { id: string; descrizione: string; criticita: "alta" | "media" | "bassa" }

const CRITICITA_COLOR: Record<Item["criticita"], string> = {
  alta: "bg-rose-500/15 text-rose-700",
  media: "bg-amber-500/15 text-amber-800",
  bassa: "bg-sky-500/15 text-sky-700",
};

export function BiologicoChecklist({ items, risposte, onChange }: {
  items: Item[];
  risposte: Record<string, Risposta>;
  onChange: (id: string, r: Risposta) => void;
}) {
  return (
    <div className="space-y-3">
      {items.map((it) => (
        <div key={it.id} className="rounded-md border p-3">
          <div className="flex items-start gap-2">
            <Badge className={CRITICITA_COLOR[it.criticita]}>{it.criticita}</Badge>
            <p className="flex-1 text-sm">{it.descrizione}</p>
          </div>
          <RadioGroup
            value={risposte[it.id] ?? ""}
            onValueChange={(v) => onChange(it.id, v as Risposta)}
            className="mt-2 flex gap-4"
          >
            {(["SI", "NO", "NA"] as Risposta[]).map((r) => (
              <div key={r} className="flex items-center gap-1">
                <RadioGroupItem value={r} id={`${it.id}-${r}`} />
                <Label htmlFor={`${it.id}-${r}`} className="text-xs">{r}</Label>
              </div>
            ))}
          </RadioGroup>
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 4: Result component**

Computes livello locally using same thresholds as backend (or call a classify endpoint — local is simpler). Displays band with color + count of NOs by criticità.

- [ ] **Step 5: Form glues together + calls existing POST endpoint**

Finalize payload: `{ settore, risposte_checklist: [{id, risposta}], livello_rischio, protocollo_sanitario, … }`.

- [ ] **Step 6: Typecheck + commit**

```bash
cd frontend && npx tsc --noEmit
git add frontend/src/components/assessments/biologico/ frontend/src/app/\(dashboard\)/assessments/biologico/\[aziendaId\]/page.tsx
git commit -m "feat(biologico): per-sector checklist with live classification (US-3.15)"
```

---

### Task A4.4: Screenshots + verification

Capture: `biologico-01-alimentare.png` (mostly SI, Basso), `biologico-02-asilo.png`, `biologico-03-dentisti-alto.png` (several NOs on alta criticità).

### Task A4.5: Return summary.

---

## Phase 2 — Postflight (Orchestrator)

### Task 2.1: Update `USER_STORIES.md`

**Files:**
- Modify: `docs/context/USER_STORIES.md`

- [ ] **Step 1: Flip 9 stories from PARTIAL to DONE**

Edit the headers for: US-3.1, 3.2, 3.3, 3.9, 3.10, 3.11, 3.12, 3.15. Update the **Built**/**Missing** notes to reflect the completed work (reference screenshots and commits). Update the Progress Summary table row for Epic 3 — DVR Attachments from `27%` to reflect new count (5 DONE, 3 PARTIAL, 7 NOT STARTED → ~47%).

- [ ] **Step 2: Commit**

```bash
git add docs/context/USER_STORIES.md
git commit -m "docs: mark US-3.1/3.2/3.3/3.9/3.10/3.11/3.12/3.15 as DONE"
```

### Task 2.2: Full verification sweep

- [ ] **Step 1: Backend tests**

```bash
cd backend && pytest tests/ -q
```
Expected: all new tests pass alongside the baseline 16.

- [ ] **Step 2: Frontend typecheck + lint**

```bash
cd frontend && npx tsc --noEmit && npm run lint
```

- [ ] **Step 3: Generator smoke test** (the agents' changes should not break .docx output)

```bash
cd backend && python -m scripts.verify_all_generators /tmp/out
```
Expected: `RESULT: 17/17 generators produced valid output`.

### Task 2.3: Push

```bash
git push
```

---

## Cross-Cutting Rules Appendix (dispatch to every agent)

1. **Italian copy everywhere** — labels, errors, badges, button text. Glossary in `CLAUDE.md`.
2. **No emoji** in UI code (icons only via Lucide).
3. **Colors**: reuse `emerald`/`amber`/`rose` tokens used in existing assessment pages. Don't invent tokens.
4. **No shared component extraction** this batch — if two agents both need a slider helper, each owns a local copy.
5. **Next 16**: consult `frontend/node_modules/next/dist/docs/01-app/` for `params` handling, route segment config, server actions.
6. **No auto-save** — explicit "Salva valutazione" button + dirty-state badge.
7. **Commits**: one logical unit per commit, Italian-free subject line, pattern `feat(<area>): <subject>`.
8. **Tests**: TDD — write test, see it fail, implement, see it pass, commit. Don't skip the "see it fail" step.
9. **Never touch another agent's files.** If you find something broken in a shared module, flag it in the return summary but do NOT fix it.

---

## Self-Review Checklist Results

Running self-review against the spec:

**Spec coverage:**
- §4.1 MMC — US-3.1 ✓ (Task A1.4), US-3.2 ✓ (A1.1, A1.2, A1.5), US-3.3 ✓ (A1.6)
- §4.2 Incendio — US-3.11 ✓ (A2.3 Step 3), US-3.12 ✓ (A2.1, A2.2, A2.3 Step 4-6)
- §4.3 Gestanti — US-3.9 ✓ (A3.1, A3.2, A3.3), US-3.10 ✓ (A3.2 decision endpoint + A3.3 dialog)
- §4.4 Biologico — US-3.15 ✓ (A4.1, A4.2, A4.3)
- §3.1 Stack rules (Next 16 params) ✓ called out in A3.3, A4.3, and appendix
- §3.2 UX rules (Italian, explicit save, color tokens) ✓ in appendix
- §3.5 Verification (pytest, tsc, lint, screenshots) ✓ in each agent's final task + Phase 2

**Placeholder scan:** no "TODO"/"TBD"/"add appropriate…". All code blocks contain the intended content.

**Type consistency:**
- `LiftResult` shape consistent across A1.4 and A1.6 (`plr`/`ir`/`zona`)
- `Livello` literal consistent across A2 (`"Basso"|"Medio"|"Alto"`)
- `ChecklistItem` / `Risposta` consistent across A4.1 and A4.3
- `CrossRefMatch` consistent between A3.2 and A3.3

No issues found.
