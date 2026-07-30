---
paths:
  - "backend/app/services/document_generator/**"
  - "backend/app/services/*calculator*.py"
  - "backend/scripts/**"
---

# Document generation

Output is `.docx` via python-docx: professional formatting, cover page, logo, table of contents. Every document draws on the same data layer (Azienda, Persona, Ambiente, Attrezzatura, SostanzaChimica) — see `docs/context/DATA_MODEL.md` for field-level detail and privacy flags.

**Generated text is Italian.** Code and identifiers stay English.

## Specs to read first

- `docs/context/DVR_TEMPLATE_MAPPING.md` — *is* the spec for the DVR Master engine: 111 tables cataloged, 4 document parts with exact boundaries, the environment risk block pattern (7 environments × identical structure), 269 dynamic cells mapped to data fields.
- `docs/context/DOCUMENT_STRUCTURE.md` — per-section static vs. dynamic classification for every document type.
- `docs/context/REFERENCE_DATA.md` — the lookup tables (NIOSH factor tables including the 18-row Factor F, 60+ hazard items across 11 categories, 76 INAIL stress indicators, fire INF/SI/PI definitions, VDT checklist, P/D scale descriptions).
- `docs/context/RISCHIO_CHIMICO_MAPPING.md` — MoVaRisCh allegato.

## Formulas

Full input/output specs in `docs/context/FORMULAS_AND_CALCULATIONS.md`. The ones that get "corrected" by mistake:

- **Risk index: `I = 2*D + P`** — not the standard `P × D`. Range 3–12: 3–4 accettabile, 5–6 modesto, 7–8 grave, 9–12 gravissimo.
- **NIOSH: `PLR = CP × A × B × C × D × E × F`**, `IR = P / PLR`. Green ≤ 0.75, yellow 0.75–1.0, red > 1.0.
- **VDT exposure**: ≥ 20 hours/week = exposed.
- **Fire risk**: `INF + SI + PI`, each 1–3. Sum 3–4 low, 5–7 medium, 8–9 high.
- Thermal comfort (PMV/PPD) and severe heat (PHS) come from `pythermalcomfort` — don't hand-roll them.

## Verifying a change

`templates/` holds the real completed documents that are the ground truth for structure. After changing a generator, audit the output rather than eyeballing it — the `dvr-auditor` subagent checks a generated DVR section-by-section against the template spec and reports empty placeholders, hardcoded boilerplate and missing data.
