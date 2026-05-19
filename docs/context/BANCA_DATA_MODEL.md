> **NIUEXA** | AI-Powered Business Automation
> *N2O DVR — Banca ESG-Social Add-on*
> Version 1.0 | May 2026 | Gregor Maric
> Confidential — Niuexa & N2O SRL

---

# Data Model — Banca ESG-Social Add-on

This document describes:
1. New entities introduced by the Banca add-on
2. Two-level tenancy model (organization × banca)
3. Changes to existing entities (`Azienda`, `Persona`)
4. RBAC matrix
5. New API surface
6. Migration plan from the current schema

The existing N2O DVR data model (`docs/context/DATA_MODEL.md`) remains the authoritative reference for shared entities. This doc only describes the **delta**.

---

## Entity overview (new + extended)

```
                       Organization (existing: N2O studio)
                              │
                              │ owns N2O staff users
                              │
   Banca (NEW)                ▼
       │                 (N2O Consulente)
       ├── BancaBranding (NEW, 1:1)
       │
       ├── BancaUser (NEW, N: bank staff with roles banca_admin / banca_viewer)
       │
       └── BancaCorporateClient (NEW, N:M ↔ Azienda)
                │
                ├── InvitoBanca (NEW, 1:N: token invitations)
                ├── AutodichiarazioneSnapshot (NEW, 1:N annual immutable submissions)
                ├── AutodichiarazioneDraft (NEW, 1:0..1 in-progress draft)
                └── RevShareLedger (NEW, 1:N when Tier 2 purchased)

   Azienda (EXISTING, extended)
       │
       ├── existing relations (Persona, Ambiente, …)
       │
       ├── RegistroInfortuni (NEW, 1:N per anno)
       └── CertificazioneSicurezza (NEW, 1:N)

   CCNL (NEW lookup, seeded)
```

---

## 1. New entities

### `Banca`

The bank tenant. One row per partner bank.

| Field | Type | Notes |
|---|---|---|
| id | UUID | PK |
| slug | str (32) | Unique URL slug (`democredit`, `bcc-roma`) |
| ragione_sociale | str | "Banca di Credito Cooperativo di Roma" |
| codice_abi | str(5) | ABI bank code, optional |
| status | enum | `setup_in_corso` / `attiva` / `sospesa` / `chiusa` |
| ad_name | str | Name of the AD signing endorsement mail |
| ad_email | str | Address used in invitation `from` (display name) |
| reply_to_email | str | Reply-to address for invitations |
| dpa_signed_at | datetime \| null | When the DPA was signed |
| dpa_version | str | Template version used |
| contract_started_at | date | |
| contract_ends_at | date | |
| infrastructure_fee_per_client_eur | numeric | e.g. 4.00 |
| revshare_pct | numeric | e.g. 20.00 |
| setup_fee_eur | numeric | One-time |
| domain_strategy | enum | `path` (`/esg/{slug}`) / `subdomain` (`esg.bancaxyz.it`) |
| custom_domain | str \| null | If subdomain, the FQDN |
| created_at | datetime | |
| created_by_user_id | UUID FK users.id | Niuexa admin who created |

**Unique constraints**: `slug` is globally unique.

### `BancaBranding`

Per-bank theming config.

| Field | Type | Notes |
|---|---|---|
| banca_id | UUID FK | PK |
| logo_url | str | Signed URL on Render Disk / S3 |
| primary_color | str(7) | `#RRGGBB` |
| secondary_color | str(7) | |
| accent_color | str(7) | |
| font_family | enum | `inter` / `plus-jakarta` / `roboto` (curated list) |
| welcome_copy | text | Markdown, max 1000 chars |
| cta_copy_submit | str | Default "Firma e invia" |
| email_signature_html | text | Custom email footer |
| updated_at | datetime | |

### `BancaUser`

Bank staff with access to the Banca admin dashboard.

| Field | Type | Notes |
|---|---|---|
| id | UUID | PK |
| banca_id | UUID FK | |
| email | str | Unique within banca |
| display_name | str | |
| role | enum | `banca_admin` / `banca_viewer` |
| invited_at | datetime | |
| accepted_at | datetime \| null | |
| last_login_at | datetime \| null | |
| status | enum | `invited` / `active` / `revoked` |

### `BancaCorporateClient`

The link table between an `Azienda` and a `Banca`. An `Azienda` can be cliente of multiple banks.

| Field | Type | Notes |
|---|---|---|
| id | UUID | PK |
| banca_id | UUID FK | |
| azienda_id | UUID FK | |
| status | enum | `da_invitare` / `invitato` / `accesso_effettuato` / `draft_in_corso` / `submitted` / `overdue` / `escluso` |
| invitato_at | datetime \| null | |
| ultimo_accesso_at | datetime \| null | |
| ultima_submission_id | UUID FK | → AutodichiarazioneSnapshot |
| consente_consulenza_n2o | bool | If true, the Azienda is also linked to N2O's `organization_id` |
| reminder_enabled | bool | Default true |
| gestore_user_id | UUID FK \| null | Bank staff "owner" of this relationship |
| dvr_pro_active | bool | Cache: has the Azienda subscribed to Tier 2? |
| created_at | datetime | |

**Unique constraints**: `(banca_id, azienda_id)` unique. An Azienda cannot be linked to the same Banca twice.

### `InvitoBanca`

Magic-link invitations sent to Corporate DdL.

| Field | Type | Notes |
|---|---|---|
| id | UUID | PK |
| banca_corporate_client_id | UUID FK | |
| token | str(64) | URL-safe random, indexed |
| backup_code | str(6) | Numeric, salted-hashed |
| email_to | str | Snapshot of DdL email at send time |
| sent_at | datetime | |
| expires_at | datetime | Default +14 days |
| used_at | datetime \| null | One-shot |
| reminder_round | int | 0 = original, 1/2/3 = reminders |

### `AutodichiarazioneDraft`

In-progress wizard state. Mutable.

| Field | Type | Notes |
|---|---|---|
| id | UUID | PK |
| banca_corporate_client_id | UUID FK | Unique (one draft per relationship) |
| anno_riferimento | int | Default current year |
| current_step | int | 1..5 |
| payload | JSONB | Form state |
| updated_at | datetime | Auto-save timestamp |

### `AutodichiarazioneSnapshot`

Final immutable submission. Append-only.

| Field | Type | Notes |
|---|---|---|
| id | UUID | PK |
| banca_corporate_client_id | UUID FK | |
| anno_riferimento | int | |
| submitted_at | datetime | |
| submitted_by_email | str | DdL email at submission |
| submitted_by_ip | str | Audit |
| signature_png | bytea | Signature canvas image |
| payload | JSONB | Frozen copy of all 12 MEF answers |
| pdf_sha256 | str(64) | Integrity hash |
| pdf_path | str | Render Disk path |
| semaphore | enum | `green` / `yellow` / `red` |
| niuexa_template_version | str | For audit reproducibility |

**Constraints**:
- DB trigger preventing UPDATE on this table (raises exception).
- Unique `(banca_corporate_client_id, anno_riferimento)`.

### `RegistroInfortuni`

Annual safety stats per company. Maps to MEF Priority-1 indicators 32, 33, 34.

| Field | Type | Notes |
|---|---|---|
| id | UUID | PK |
| azienda_id | UUID FK | |
| anno_riferimento | int | |
| infortuni_inail_n | int | Indicator 32 (count) |
| infortuni_inail_ore_lavorate | int \| null | Denominator for tasso |
| infortuni_inail_tasso | numeric \| null | Computed: n × 200000 / ore |
| giornate_perse_n | int | Indicator 33 |
| decessi_n | int | Indicator 34 |
| note | text \| null | Free-text context |
| created_at | datetime | |
| source | enum | `autodichiarazione` / `manual` / `import` |

**Unique constraints**: `(azienda_id, anno_riferimento)`.

### `CertificazioneSicurezza`

Tracks third-party certifications.

| Field | Type | Notes |
|---|---|---|
| id | UUID | PK |
| azienda_id | UUID FK | |
| tipo | enum | `iso_45001` / `sa_8000` / `parita_di_genere_uni_pdr_125` / `altro` |
| ente_certificatore | str | |
| numero_certificato | str | |
| data_emissione | date | |
| data_scadenza | date \| null | |
| documento_path | str \| null | Optional uploaded PDF |

### `CCNL`

Lookup table for collective labor agreements.

| Field | Type | Notes |
|---|---|---|
| codice_cnel | str | PK, e.g. "F011" |
| descrizione | str | "Metalmeccanici industria" |
| settore_macro | str | "industria" / "terziario" / "edilizia" / etc. |
| attivo | bool | |

Seeded from CNEL public list (~ 900 CCNL — start with top 30 most common).

### `RevShareLedger`

Tracks revenue share owed to each Banca.

| Field | Type | Notes |
|---|---|---|
| id | UUID | PK |
| banca_id | UUID FK | |
| azienda_id | UUID FK | |
| stripe_payment_id | str | Idempotency key |
| amount_gross_eur | numeric | Total paid by PMI |
| amount_share_eur | numeric | Banca's cut |
| pct_applied | numeric | Snapshot of banca.revshare_pct at time of sale |
| period_yyyy_mm | str(7) | "2026-06" |
| status | enum | `accrued` / `invoiced` / `paid` |
| paid_at | datetime \| null | |

---

## 2. Two-level tenancy model

Existing tenancy uses `Azienda.organization_id` to scope by N2O studio. This stays.

We add a **second, orthogonal tenancy axis** via `BancaCorporateClient`:

| Scenario | organization_id | BancaCorporateClient row | Visibility |
|---|---|---|---|
| Azienda is consulente client only | set (N2O org) | none | N2O staff only |
| Azienda is bank client only | null (or "default org") | row(banca_x, azienda) | Banca X admin + DdL |
| Azienda is both | set (N2O org) | row(banca_x, azienda) + `consente_consulenza_n2o=true` | N2O staff + Banca X admin + DdL |

**Repository pattern (mandatory)**

All queries on `Azienda` and related entities MUST go through one of:

```python
# N2O context
AziendaRepo.for_organization(organization_id).all()

# Banca context
AziendaRepo.for_banca(banca_id).all()
# Internally: SELECT a.* FROM azienda a
#             JOIN banca_corporate_client bcc ON bcc.azienda_id = a.id
#             WHERE bcc.banca_id = :banca_id

# DdL context (single Azienda)
AziendaRepo.for_corporate_ddl(user_id, banca_id, azienda_id)
# Validates the (user, banca, azienda) tuple before returning
```

Direct `session.query(Azienda).all()` is **banned** in code paths reachable from banca routes. Enforced via lint rule + code review.

**Cross-tenant negative tests** in CI exercise:
- Banca A admin accessing Banca B's `BancaCorporateClient` → 404
- DdL of Azienda X accessing Azienda Y → 404
- N2O staff trying to read a bank-only Azienda without `consente_consulenza_n2o` → 404

---

## 3. Changes to existing entities

### `Azienda` — additive fields

| Field | Type | Notes |
|---|---|---|
| data_aggiornamento_dvr | date \| null | Used by autodichiarazione step 4 (existing `data_scadenza_dvr` can derive this) |
| ha_codice_etico | bool \| null | Indicator 26 (MEF) |
| ha_rspp_designato | bool \| null | Indicator 39 ish |
| ha_rls_designato | bool \| null | |
| ha_medico_competente | bool \| null | |
| ccnl_codice | str FK CCNL \| null | Indicator 36 |
| copertura_ccnl_pct | numeric | Default 100 |
| ha_procedure_segnalazione_ss | bool \| null | Indicator 39 |
| organization_id | UUID FK | **Now nullable** (for bank-only aziende) |

### `Persona` — additive fields

| Field | Type | Notes |
|---|---|---|
| ore_formazione_ss_anno_corrente | numeric | Indicator 31, aggregated by autodichiarazione |
| ore_formazione_obbligatoria | numeric | |
| categoria_protetta | bool | Indicator 29 |
| tipo_contratto | enum | `tempo_indeterminato` / `tempo_determinato` / `apprendista` / `somministrato` (indicator 35) |

---

## 4. RBAC matrix

| Role | Banca entities | Azienda (own org) | Azienda (bank-only) | Internal admin |
|---|---|---|---|---|
| `niuexa_admin` | Full CRUD on any Banca | Full | Full (audit only, logged) | Full |
| `niuexa_compliance` | Read all, generate DPA | Read | Read (audit only) | Partial |
| `banca_admin` | Read own Banca, manage `BancaUser`, manage clients | n/a | Read own bank's clients only | none |
| `banca_viewer` | Read own Banca | n/a | Read own bank's clients only | none |
| `n2o_consultant` (existing) | none | Full own org | Read iff `consente_consulenza_n2o` | none |
| `corporate_ddl` | none | n/a | Full own Azienda only | none |

---

## 5. API surface (new endpoints)

All endpoints are versioned under `/api/v1/banca/`.

### Banca admin (internal)

```
POST   /admin/banche                       — create Banca
GET    /admin/banche                       — list (niuexa_admin only)
GET    /admin/banche/{slug}                — read
PATCH  /admin/banche/{slug}                — update Banca metadata
POST   /admin/banche/{slug}/branding       — upload/update branding
POST   /admin/banche/{slug}/clienti/import — CSV import of corporate clients
GET    /admin/banche/{slug}/audit          — paginated audit log
POST   /admin/banche/{slug}/dpa/genera     — generate DPA PDF
GET    /admin/banche/{slug}/revenue        — revshare ledger
```

### Banca staff (banca_admin / banca_viewer)

```
GET    /banca/{slug}/dashboard             — coverage + tiles
GET    /banca/{slug}/clienti               — list w/ filters
GET    /banca/{slug}/clienti/{azienda_id}  — drill-down
POST   /banca/{slug}/clienti/{id}/invita   — single invite
POST   /banca/{slug}/clienti/inviti-bulk   — bulk invite
POST   /banca/{slug}/export/csv            — CSV export job
POST   /banca/{slug}/export/ispezione      — ZIP package job
GET    /banca/{slug}/users                 — list banca users
POST   /banca/{slug}/users                 — invite banca user
DELETE /banca/{slug}/users/{id}            — revoke
```

### Corporate DdL (PMI)

```
POST   /auth/magic-link/{token}            — accept invitation
POST   /auth/code                          — backup code auth
GET    /esg/{slug}                         — landing
GET    /esg/{slug}/wizard                  — wizard state
PATCH  /esg/{slug}/wizard                  — save draft step
POST   /esg/{slug}/wizard/submit           — finalize + sign
GET    /esg/{slug}/storico                 — past submissions
GET    /esg/{slug}/pdf/{snapshot_id}       — download signed PDF
POST   /esg/{slug}/gdpr/export             — DSAR export
POST   /esg/{slug}/gdpr/delete             — anonymization request
POST   /esg/{slug}/upsell/dvr-pro/checkout — Stripe Checkout session
```

### Webhooks

```
POST   /webhooks/stripe                    — payment success → RevShareLedger
```

---

## 6. Migration plan

Single Alembic migration `bxxx_banca_addon_schema.py` introduces all new tables + additive columns. Order:

1. Create lookup tables: `ccnl`.
2. Create core: `banca`, `banca_branding`, `banca_user`.
3. Create per-azienda tables: `registro_infortuni`, `certificazione_sicurezza`.
4. Add nullable columns to `azienda`, `persona`.
5. Create relational tables: `banca_corporate_client`, `invito_banca`.
6. Create submission tables: `autodichiarazione_draft`, `autodichiarazione_snapshot` (with append-only trigger).
7. Create ledger: `revshare_ledger`.
8. Create `audit_log_banca` (with append-only trigger).
9. Seed `ccnl` from CNEL list (top 30).
10. Backfill: existing `Azienda.organization_id` remains; no banca links exist yet — new banche populate via UI.

**Reversibility**: down migration drops all new tables and removes additive columns. Safe because no production data depends on them yet.

**Downtime**: zero — all changes are additive.

---

## 7. Privacy & data classification

| Field | Class | Special handling |
|---|---|---|
| `Azienda.ragione_sociale`, P.IVA, sede | Public business data | None |
| DdL email, signature | Personal data | GDPR processing basis: contract / consent on invitation accept |
| `RegistroInfortuni.decessi_n` | Sensitive (potential health correlations) | Aggregate only in bank dashboards; never expose individual incident details |
| Stripe payment | Financial | PCI handled by Stripe; we store only `payment_id` |
| Signature PNG | Personal | Encrypted at rest if possible; otherwise access-logged |
| Audit log | Internal | Append-only, queryable by niuexa_admin only |

---

## 8. Indexes & performance

Critical indexes:
- `banca_corporate_client(banca_id, status)` — dashboard tiles
- `banca_corporate_client(azienda_id)` — reverse lookup
- `autodichiarazione_snapshot(banca_corporate_client_id, anno_riferimento)` — latest submission
- `audit_log_banca(banca_id, created_at)` — audit query
- `revshare_ledger(banca_id, period_yyyy_mm, status)` — monthly settlement
- `invito_banca(token)` — magic-link lookup (unique)
- `invito_banca(banca_corporate_client_id, expires_at)` — reminder selection

For banks > 5000 corporate clients, dashboard aggregates should be cached for 60 seconds in Redis to keep p95 under 2s.
