# Deployment — N2O DVR Platform

Stack: FastAPI + Celery worker on **Render**, Next.js 16 on **Vercel**, Postgres + Redis on **Render** (managed).

---

## 1. Backend (Render)

The blueprint lives at `backend/render.yaml` and declares 4 resources:

| Resource | Name | Notes |
|---|---|---|
| Managed Postgres | `n2o-dvr-db` | Starter plan, EU region recommended |
| Redis | `n2o-dvr-redis` | `maxmemoryPolicy: noeviction` (broker must not drop jobs) |
| Web service | `n2o-dvr-api` | FastAPI + uvicorn |
| Worker service | `n2o-dvr-worker` | Celery worker for doc generation |

### 1.1 First deploy

1. Connect the GitHub repo to Render.
2. **New → Blueprint**, pick `backend/render.yaml`.
3. Render provisions Postgres, Redis, API, Worker. Plug the Postgres & Redis connection strings into API/Worker env vars automatically (already wired in the blueprint).
4. Fill in these **manual** env vars (the blueprint marks them `sync: false`):
   - `OPENAI_API_KEY` on both `n2o-dvr-api` and `n2o-dvr-worker`
5. Upload the **Google Drive OAuth token** on `n2o-dvr-worker`:
   - Service → **Environment** → **Secret Files**
   - Filename: `token.json`
   - Contents: paste `credentials/token.json` from the local repo
   - The worker env var `GOOGLE_DRIVE_TOKEN_JSON` already points at `/etc/secrets/token.json`; if the file isn't uploaded, Drive uploads silently no-op (the doc generation itself still succeeds).
6. Verify `CORS_ORIGINS` in `backend/render.yaml:30` matches your Vercel URL. Default is `https://n2o-dvr.vercel.app` — update before first deploy if your Vercel project name differs.

### 1.2 Post-deploy one-offs

Shell into the API service (Render → Shell) and run the demo-data scripts if needed:

```bash
python -m app.db.fixtures.acme_meccanica   # optional: seed the ACME demo
python -m scripts.seed_demo_users          # optional: add operator-role demo users
```

`alembic upgrade head` runs automatically via `preDeployCommand`.

### 1.3 Environment reference (backend)

| Var | Where | Source |
|---|---|---|
| `DATABASE_URL` | api, worker | Auto from `n2o-dvr-db` |
| `REDIS_URL` | api, worker | Auto from `n2o-dvr-redis` |
| `AUTH_SECRET` | api | Auto-generated |
| `OPENAI_API_KEY` | api, worker | **Set manually** |
| `GOOGLE_DRIVE_FOLDER_ID` | worker | Hardcoded to N2O's production Drive folder |
| `GOOGLE_DRIVE_TOKEN_JSON` | worker | `/etc/secrets/token.json` (Secret File) |
| `FILE_STORAGE_PATH` | api, worker | `/data` (persistent disk) |
| `CORS_ORIGINS` | api | `["https://n2o-dvr.vercel.app"]` |

---

## 2. Frontend (Vercel)

### 2.1 Project setup

- **New project** → import this repo.
- **Root Directory**: `frontend`
- Framework preset: **Next.js** (auto-detected).

### 2.2 Environment variables

Set these in **Project Settings → Environment Variables** (all three environments: Production, Preview, Development):

| Var | Value |
|---|---|
| `NEXT_PUBLIC_API_URL` | `https://n2o-dvr-api.onrender.com` (or whatever Render assigns) |
| `AUTH_SECRET` | A long random string — used by NextAuth to encrypt session cookies. Generate via `openssl rand -base64 32`. |
| `NEXTAUTH_URL` | `https://<your-vercel-project>.vercel.app` (prod only; auto-detected on preview) |

`AUTH_SECRET` is **independent** from the backend's `AUTH_SECRET`. They don't need to match — backend signs its own JWTs, NextAuth encrypts its own cookies.

### 2.3 Post-deploy

Deploy happens on push to `main`. First deploy creates the production URL; copy it back into `backend/render.yaml:30` (`CORS_ORIGINS`) and redeploy the API if the value differs from `https://n2o-dvr.vercel.app`.

---

## 3. Known gaps (acceptable for v1, track for follow-up)

| Gap | Impact | Workaround |
|---|---|---|
| **US-1.6 signature feature is half-built.** Migration `c1d2e3f4a5b6_add_azienda_signature.py` adds 3 columns to `aziende`, but the backend model, schemas, and `/sign` `/signature` `/revision` routes don't exist. The frontend "Conferma firma" button at `survey-wizard.tsx:324` posts to a 404. | Signature step in the survey wizard is broken. | Skip the signature step during the real demo; the columns sit unused in Postgres. Feature will be completed in a follow-up phase. |
| **Self-registration creates a new organization with the registrant as admin.** This is standard SaaS flow (admin of *their own* org), not a privilege escalation — organizations are tenant-scoped. | By design. | To invite operators into an existing org, use `backend/scripts/seed_demo_users.py` as a template — it adds users to the ACME org. A real invite flow is tracked for a later milestone. |
| **NextAuth ↔ backend JWT refresh.** There's no refresh flow; the backend JWT TTL is 7 days (`ACCESS_TOKEN_EXPIRE_MINUTES` in `backend/app/config.py`). NextAuth's own session TTL is 30 days. After 7 days of activity the user is bounced back to `/login`. | User has to log in once a week. | Acceptable for v1. Add `/auth/refresh` + NextAuth `jwt` callback if weekly re-login is a problem. |
| **SDS (safety-data-sheet) extraction runs inline on FastAPI** (`backend/app/api/v1/sostanze_chimiche.py:172`, `BackgroundTasks`), not on Celery. A 20-file batch with a 60s OpenAI timeout per file can pin one uvicorn worker for ~20 minutes. | Concurrent users may see slower API responses during batch SDS uploads. | Small teams (single-digit users) won't notice. Move to Celery when usage grows. |
| **Unused `backend/Dockerfile`.** The Render blueprint uses `runtime: python`, not Docker. The Dockerfile doesn't copy `templates/`. | None in production. | Either delete or fix alongside a future Docker migration. |
| **Runbook §1.2 instruction to run `python -m app.db.seed` is stale.** `app/db/seed.py` references tables that don't exist and logs "would seed". Reference data now lives in Python modules (`app/services/reference_data.py`, `app/data/*`). | Confusing for operators; no functional impact. | Ignore the runbook line; don't need to run `seed.py`. |

---

## 4. Troubleshooting

| Symptom | Likely cause |
|---|---|
| API won't start, logs show "Could not parse SQLAlchemy URL" | Only happened with the old version of `session.py`. If it recurs, confirm `DATABASE_URL` starts with `postgres://` or `postgresql://` — the normalizer handles both. |
| Generated .docx is blank / missing cover page | `templates/` didn't get copied during build. Check the API build log for `cp -r ../templates ./templates`. |
| "Conferma firma" returns 404 | Expected — US-1.6 signature feature not yet implemented. See gaps table §3. |
| Registration returns HTTP 422 | Old form was sending `null` for `organization_name`; fixed by making the field optional with a fallback. Confirm the frontend build is current. |
| Drive uploads always log "Google Drive token.json not found" | Secret File not uploaded. See §1.1 step 5. |
| Admin AI Feedback panel shows 0 rows across orgs | Intentional after the cross-tenant fix — admins see only their own org's feedback now. |

---

*Last updated 2026-04-16 — after the pre-deploy audit pass.*
