# Demo Runbook — N2O DVR Automation Platform

**Data**: 16 aprile 2026
**Ambiente**: Locale (localhost)
**Azienda demo**: ACME MECCANICA COMPOSITA SRL (fixture)
**Tempo consigliato**: 15–20 minuti

---

## 1. Setup ambiente locale

Prerequisiti: Docker, Python 3.12+, Node 20+, npm, un Redis e un Postgres in esecuzione (via `docker-compose` o installati localmente).

### 1.1 Avvio servizi di supporto

```bash
# Dalla root del progetto
docker compose up -d postgres redis
```

### 1.2 Backend FastAPI + Celery worker

```bash
# Terminale 1 — API
cd backend
source .venv/bin/activate        # oppure: python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
export DATABASE_URL=postgresql+asyncpg://postgres:dev@localhost:5432/n2o
export REDIS_URL=redis://localhost:6379/0

# Migrazioni Alembic
alembic upgrade head

# Seed dati di riferimento (categorie rischio, pericoli, tipi doc)
python -m app.db.seed

# Fixture azienda demo (ACME Meccanica)
python -m app.db.fixtures.acme_meccanica

# Avvio API
uvicorn app.main:app --reload --port 8000
```

```bash
# Terminale 2 — Celery worker (necessario per la generazione documenti)
cd backend
source .venv/bin/activate
celery -A app.celery_app worker --loglevel=info
```

### 1.3 Frontend Next.js

```bash
# Terminale 3
cd frontend
npm install
npm run dev
```

### 1.4 URL locali

| Servizio | URL |
|---|---|
| Frontend | http://localhost:3000 |
| API (Swagger) | http://localhost:8000/docs |
| Postgres | localhost:5432 — user `postgres`, pass `dev`, db `n2o` |
| Redis | localhost:6379 |

---

## 2. Credenziali e profili utente

### 2.1 Admin (pre-seed)

| Campo | Valore |
|---|---|
| Email | `admin@acme-meccanica.test` |
| Password | `Acme2026!` |
| Ruolo | `admin` |
| Organizzazione | N2O SRL (demo) |
| Nome | Luca Marchetti (demo admin) |

Viene creato automaticamente da `python -m app.db.fixtures.acme_meccanica` (file sorgente: `backend/app/db/fixtures/acme_meccanica.py:56`).

### 2.2 Profili aggiuntivi (operatori ufficio e campo)

L'endpoint `POST /api/v1/auth/register` crea sempre utenti con ruolo `admin`. Per creare i profili `operatore_ufficio` e `operatore_campo` (usati dalle user stories) eseguire lo snippet seguente dopo il seed ACME.

Salvare come `backend/scripts/seed_demo_users.py` ed eseguire con `python -m scripts.seed_demo_users` dalla cartella `backend/`:

```python
import asyncio
from sqlalchemy import select
from passlib.context import CryptContext
from app.db.session import async_session_factory
from app.models.user import User
from app.models.organization import Organization

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

DEMO_USERS = [
    ("ufficio@acme-meccanica.test", "Ufficio2026!", "Maria Ufficio (demo)", "operatore_ufficio"),
    ("campo@acme-meccanica.test",   "Campo2026!",   "Paolo Campo (demo)",   "operatore_campo"),
]

async def main():
    async with async_session_factory() as s:
        org = (await s.execute(select(Organization).where(Organization.name == "N2O SRL (demo)"))).scalar_one()
        for email, pw, name, role in DEMO_USERS:
            exists = (await s.execute(select(User).where(User.email == email))).scalar_one_or_none()
            if exists:
                print(f"[skip] {email} già presente")
                continue
            s.add(User(
                organization_id=org.id,
                email=email,
                hashed_password=pwd.hash(pw),
                full_name=name,
                role=role,
            ))
            print(f"[ok]   {email} / {pw}  (role={role})")
        await s.commit()

asyncio.run(main())
```

| Email | Password | Ruolo | Persona |
|---|---|---|---|
| `admin@acme-meccanica.test` | `Acme2026!` | `admin` | N2O — Consulente senior |
| `ufficio@acme-meccanica.test` | `Ufficio2026!` | `operatore_ufficio` | N2O — Consulente ufficio |
| `campo@acme-meccanica.test` | `Campo2026!` | `operatore_campo` | Cliente — operatore sul campo |

> Nota: la differenziazione di ruolo è presente nel modello (`backend/app/models/user.py:19`) e viene propagata nel JWT (`app/core/security.py` → claim `role`). Eventuali restrizioni granulari per ruolo sulle rotte vanno verificate endpoint per endpoint durante la demo.

---

## 3. Dataset demo — ACME MECCANICA COMPOSITA SRL

Fixture realistica che copre tutti i moduli (file: `backend/app/db/fixtures/acme_meccanica.py`):

- **Attività**: lavorazioni meccaniche di precisione, mensa interna, saltuari cantieri cliente
- **Indirizzo**: Via dell'Industria 42, Parma (PR) — ATECO 25.62.00
- **18 persone**: datore di lavoro, RSPP, RLS, preposti, primo soccorso, antincendio, tornitori, saldatori, impiegati, magazzinieri, una lavoratrice gestante
- **6 ambienti**: ufficio, officina, magazzino, mensa, deposito chimico, area esterna
- **12 attrezzature**
- **8 sostanze chimiche** (con pittogrammi GHS)
- Valutazioni rischio pre-popolate per tutti gli ambienti + sorveglianze (VDT, MMC, stress, incendio, microclima, biologico, gestanti)
- Procedure di emergenza (PEE)

> La fixture è **idempotente**: eseguirla di nuovo non duplica i dati.

---

## 4. Flusso demo consigliato (20 min)

1. **Login** (http://localhost:3000/login) con admin@acme-meccanica.test / Acme2026!
2. **Dashboard** → mostrare stato azienda ACME (già popolata)
3. **Anagrafica azienda** → `/aziende` → dettaglio ACME → mostrare anagrafica + caricamento visura PDF (US-2.1)
4. **Survey** → `/survey/[aziendaId]` → navigazione matrice rischi (11 categorie × 6 ambienti)
5. **Valutazione MMC** → `/assessments/mmc/[aziendaId]` → NIOSH precompilato (Antonio Marrone — mansione tornitore)
6. **Valutazione VDT** → `/assessments/vdt/[aziendaId]` → sorveglianze scadute / in scadenza
7. **Valutazione Stress** (INAIL) → `/assessments/stress/[aziendaId]`
8. **Valutazione Incendio** → `/assessments/incendio/[aziendaId]` → INF+SI+PI
9. **Gestanti** → `/assessments/gestanti/[aziendaId]` → restrizioni mansione
10. **HACCP** → `/assessments/haccp/[aziendaId]` → configurazione CCP e schede
11. **POS** → `/assessments/pos/[aziendaId]` → Phase Builder (US-4.7, mergiato ieri)
12. **Generazione documenti** → `/documents` → selezione multipla (es. `dvr_master` + `allegato_mmc`) → **Genera** → attesa Celery → download `.docx`
13. **Area admin** → `/admin/ai-feedback` → audit trail feedback AI
14. **Backup** → `/settings/backups` → stato backup su Google Drive

---

## 5. Funzionalità da testare (aree)

### 5.1 Anagrafica e survey (Epic 1)

- [ ] Creazione nuova azienda (`/aziende/new`) — verificare form e validazioni (fix QA recente: `qa-fix-02-aziende-new-form.png`)
- [ ] Upload visura camerale → estrazione dati con `visura_extractor` (US-2.1)
- [ ] Navigazione survey (fix QA recente: `qa-fix-03-survey-navigation.png`)
- [ ] Gestione persone (datore di lavoro, RSPP, RLS, preposti)
- [ ] Gestione ambienti e attrezzature
- [ ] Inserimento sostanze chimiche (SDS) — verificare estrazione AI

### 5.2 Valutazioni di rischio (Epic 3)

- [ ] **MMC**: calcolo PLR = CP × A × B × C × D × E × F e IR = P/PLR (verde ≤0.75, giallo 0.75–1.0, rosso >1.0)
- [ ] **VDT**: soglia ≥20 h/settimana → esposto + scadenziario sorveglianze
- [ ] **Stress INAIL**: 76 indicatori, scoring automatico
- [ ] **Incendio**: INF+SI+PI → basso (3–4) / medio (5–7) / alto (8–9)
- [ ] **Microclima**: PMV/PPD, versione "moderato" e "caldo severo" (PHS)
- [ ] **Gestanti**: restrizioni e mansioni alternative
- [ ] **Biologico**: varianti alimentare / asilo / dentisti
- [ ] **HACCP**: configurazione CCP + 16 schede (SA-01…SA-16)
- [ ] **DUVRI**: rischi da interferenze appaltatori
- [ ] **POS**: phase builder (US-4.7)
- [ ] **PEE**: procedure di emergenza azienda e comune

### 5.3 Generazione documenti (Epic 2 + 5)

- [ ] Kick-off generazione batch (coda Celery)
- [ ] Polling stato (`/aziende/{id}/documents`)
- [ ] Download `.docx` (verificare apertura in Word/LibreOffice, coerenza cover, TOC, logo)
- [ ] Snapshot JSON del documento generato (US-2.9)
- [ ] Guardia "stale snapshot": modifica dati → documento esistente marcato stale (US-5.2, mergiato ieri)
- [ ] Dipendenze campi (tooltip US-5.2 AC2)

### 5.4 AI e area admin

- [ ] Suggerimento misure di miglioramento (revisione umana obbligatoria)
- [ ] Audit AI feedback → `/admin/ai-feedback`
- [ ] Backup su Google Drive → `/settings/backups`

---

## 6. Tipi di documento generabili

Tutti i 16 output dell'Allegato MMC sono code-complete (servizio `backend/app/services/document_generator/`):

- `dvr_master` — DVR master (valutazione rischi completa)
- `allegato_mmc`, `allegato_vdt`, `allegato_stress`, `allegato_incendio`
- `allegato_microclima` (moderato + severo)
- `allegato_biologico_alimentare`, `allegato_biologico_asilo`, `allegato_biologico_dentisti`
- `allegato_gestanti`
- `pee_azienda`, `pee_comune`
- `haccp_manuale`, `haccp_forms`
- `duvri`, `pos`

Verifica fine-a-fine: `python -m scripts.verify_all_generators`

---

## 7. Limitazioni note / work-in-progress

- **Registrazione self-service** crea solo ruolo `admin` (vedi §2.2 — serve script per ruoli operatori).
- **Integrazione NextAuth + backend JWT** ancora in consolidamento (controlli di sessione lato frontend).
- **Backup Google Drive** — da verificare il trigger automatico su generazione documento.
- **Tre QA fix** applicati il 15/04: banner registrazione, form `/aziende/new`, navigazione survey (screenshot non ancora committati: `qa-fix-0[1-3]-*.png`).

---

## 8. Troubleshooting rapido

| Problema | Azione |
|---|---|
| Generazione documento resta in `pending` | Verificare che il Celery worker sia attivo (Terminale 2) |
| Login KO | Rilanciare `python -m app.db.fixtures.acme_meccanica` |
| Migration errori | `alembic downgrade base && alembic upgrade head` su DB vuoto |
| CORS error | In dev il frontend chiama `http://localhost:8000` — controllare `NEXT_PUBLIC_API_URL` in `frontend/.env.local` |
| Celery non trova Redis | `docker compose ps redis`, oppure `export REDIS_URL=redis://localhost:6379/0` |

---

## 9. Riferimenti rapidi file/path

- Fixture ACME: `backend/app/db/fixtures/acme_meccanica.py`
- Seed dati di riferimento: `backend/app/db/seed.py`
- Auth endpoints: `backend/app/api/v1/auth.py`
- Modello User (ruoli): `backend/app/models/user.py`
- Generatori documenti: `backend/app/services/document_generator/`
- Calcolatori: `backend/app/services/{risk,stress,vdt,microclima}_calculator.py`
- Pagine dashboard: `frontend/src/app/(dashboard)/`
- Deploy Render: `backend/render.yaml` (servizi `n2o-dvr-api`, `n2o-dvr-worker`, `n2o-dvr-db`, `n2o-dvr-redis`)

---

*Documento generato per la demo del 16/04/2026 — Gregor Maric, Niuexa.*
