# Organization Branding — Design Spec

**Date:** 2026-06-28
**Author:** Gregor Maric (Niuexa) + Claude
**Status:** Approved — in build

## Goal

Turn the hardcoded N2O consultancy identity (logo + letterhead) into
configurable per-organization data, managed by an admin in the app, applied to
both generated documents and the app UI. Moves the consultancy branding from
"redeploy to change" to "edit in Impostazioni".

## Scope decisions (confirmed with user)

1. **Tenancy:** branding lives **per-organization** (on the existing
   `Organization` model). Each org's admin configures their own. Costs nothing
   now (N2O is the only org) and makes the app white-label for free.
2. **Fields:** **full letterhead** — logo image + firm name + address + tax IDs
   + contacts + RSPP/declarant.
3. **Applies to:** **generated documents + app UI** (sidebar + login chrome).

## Current state (verified in code)

- Logo is a committed file `backend/assets/logo.png`, embedded by every
  generator via a module-level path constant (`_LOGO_PATH` / `LOGO_PATH`), with
  a graceful italic-text fallback already in place. Single chokepoint.
- Code-built documents (DVR master) carry consultancy branding **only as the
  cover logo** — there is no consultancy text letterhead in them today. (The
  cover identity block prints the *assessed client*, not the consultancy.)
- Legacy attachment templates (Stress, Gestanti) carry N2O letterhead baked in
  template header/footer XML; a `scrub_body` mechanism already exists for the
  donor body identity.
- Data model already has multi-tenant scaffolding:
  `Organization (name, created_at)` → `User (organization_id, role)` →
  `Azienda (organization_id, organization rel)`. No branding fields yet.
- Auth: `require_role("admin")` dependency; roles are
  `admin | operatore_ufficio | operatore_campo`. `get_current_org` exists.
- File upload/serve pattern established in `ambienti.py`
  (`FILE_STORAGE_PATH=/data` Render Disk → subdir → `{uuid}.{ext}`, served via
  `FileResponse`). Frontend `useApi().apiFetch` already handles `FormData`.

## Design

### 1. Data model
Add nullable branding columns to `Organization` (Alembic migration; all
nullable so nothing regresses). `Organization.name` doubles as the firm name on
the letterhead (no second name field):

- `logo_path: str | None` — path on Render Disk to uploaded logo
- `indirizzo, cap, citta, provincia` — letterhead address
- `partita_iva, codice_fiscale` — firm tax IDs (business identifiers, never sent to AI)
- `telefono, email, sito_web` — contacts
- `rspp_nome` — RSPP / declarant on the consultancy side

### 2. Backend API — `branding` router (`/api/v1/organizations`)
- `GET  /me/branding` — readable by any authenticated user (UI + doc gen read it)
- `PUT  /me/branding` — text fields, **admin-gated**
- `POST /me/branding/logo` — upload (admin), validated like foto upload,
  stored at `FILE_STORAGE_PATH/org_logos/{org_id}/{uuid}.{ext}`
- `GET  /me/branding/logo` — serve via `FileResponse` for UI
- `DELETE /me/branding/logo` — revert to bundled default

All reads/writes scoped to caller's `organization_id`; orgs can't see each
other's branding.

### 3. Document generation integration
- New `document_generator/branding.py`:
  - `Branding` dataclass (all letterhead fields + `logo_path`)
  - `Branding.default()` → N2O fallback (firm name "N2O SRL", default logo asset)
  - `Branding.from_organization(org)` → fields from DB row, falling back to
    defaults per-field
  - `resolve_logo_path(branding) -> Path` → org logo if the file exists, else
    committed `assets/logo.png`
- `BaseDocumentGenerator`:
  - `__init__` sets `self.branding = Branding.default()` (harness-safe default)
  - real `load_data()` sets `self.branding` from the azienda's org, **defensively**
    (any failure → default), so the monkey-patched test harness (which patches
    `load_data`) keeps producing valid output.
- Generators embed the logo via `resolve_logo_path(self.branding)` instead of
  the module constant.
- DVR master gets a reusable **consultancy-letterhead block** (`docx_utils
  .add_consultancy_letterhead(doc, branding)`) driven by branding, N2O default.
  Additive (no logo regression); other generators can adopt the same helper.

### 4. Frontend
- New admin page `/admin/branding`: logo upload with live preview + text-field
  form + save. Follows `/admin/users` page conventions and DESIGN.md.
- Sidebar + login chrome read the org logo (fallback to current Shield + "N2O
  DVR" text). New admin nav entry "Personalizzazione".

### 5. Authorization & isolation
- Writes require `require_role("admin")`. Reads open to authenticated users.
- Everything scoped to `get_current_org`.

## Testing
Matches repo style (no live DB fixture):
- Pure unit tests for `Branding` fallback + `resolve_logo_path`.
- Route-registration contract test for the new endpoints.
- Schema-shape test for the branding response/update models.
- Existing `test_generators.py` (all 17 generators produce valid docx) must
  stay green — guaranteed by the harness-safe default branding.

## Explicitly out of scope (easy follow-ons)
- Configurable document accent color (header hardcoded navy `#1A237E`).
- Multiple logos (separate cover vs header).
- Per-document-type branding overrides.
- Replacing the baked-in letterhead text inside legacy template header/footer
  XML per-org (N2O is the only org; no regression risk today).
