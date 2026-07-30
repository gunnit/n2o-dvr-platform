---
paths:
  - "backend/app/core/permissions.py"
  - "backend/app/api/**"
  - "backend/tests/test_permissions.py"
  - "frontend/src/lib/permissions.ts"
  - "frontend/src/hooks/**"
---

# Roles and capabilities

`app/core/permissions.py` answers *what this person may do* and fails with `403`. That is a separate gate from `app/billing/*`, which answers *what the organization bought* and fails with `402`. Both apply to the same endpoints; neither substitutes for the other.

- **Gate on a capability, not a role**: `Depends(require_capability(DOCUMENTS_GENERATE))`. `require_role("admin")` survives only where the gate really is about the role as a category — `test_no_endpoint_still_hardcodes_the_admin_role` fails the build if a new one appears under `app/api/`.
- **The three personas nest**: `operatore_campo` ⊂ `operatore_ufficio` ⊂ `admin`, enforced by `validate_matrix()`. Roughly: field collects (survey, assessments, AI, reading documents), office also finalises (`documents:generate`), admin also owns the portfolio, the money and the team.
- **Reads are never role-gated away.** Every role holds `documents:read` and `aziende:read` — the same D.Lgs. 81/2008 retention reason the paywall never gates downloads.
- **The frontend renders navigation from the capability list `GET /auth/me` returns** (`frontend/src/lib/permissions.ts` + `usePermissions()`), never from a second copy of the matrix. Hiding a button is cosmetic; the 403 is the rule. `backend/tests/test_permissions.py` reads the TypeScript to keep the two in step.
