> **NIUEXA** | AI-Powered Business Automation  
> *N2O DVR Automation Platform — Project Documentation*  
> Version 1.0 | April 2026 | Gregor Maric  
> Confidential — Niuexa & N2O SRL

---

# Architecture & Technical Design

## Tech Stack Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND                                  │
│   Next.js 16 · App Router · React 19 · TypeScript                │
│   shadcn/ui · Tailwind CSS 4 · Framer Motion · TanStack Table   │
│   Deployed on: Vercel                                            │
└──────────────────────────┬──────────────────────────────────────┘
                           │ REST API (HTTPS)
┌──────────────────────────▼──────────────────────────────────────┐
│                        BACKEND                                   │
│   FastAPI · Python 3.12+ · Pydantic v2 · SQLAlchemy 2.0 Async   │
│   python-docx · OpenAI SDK · Google APIs · Celery + Redis        │
│   Deployed on: Render.com                                        │
└───────┬──────────────┬───────────────┬──────────────────────────┘
        │              │               │
   ┌────▼────┐   ┌────▼────┐   ┌─────▼─────┐
   │ Postgres │   │  Redis  │   │  OpenAI   │
   │ Supabase │   │ Render  │   │ GPT-4.1   │
   └─────────┘   └─────────┘   └───────────┘
        │
   ┌────▼──────────┐
   │ Supabase       │
   │ Storage        │
   │ (SDS, photos)  │
   └───────┬───────┘
           │
   ┌───────▼───────┐
   │ Google Drive   │
   │ (final .docx)  │
   └───────────────┘
```

---

## 1. Frontend — Next.js 16

### Framework & Rendering

| Decision | Choice | Why |
|----------|--------|-----|
| Framework | **Next.js 16** (App Router) | Server Components, Server Actions, built-in i18n, image optimization, edge-ready |
| Language | **TypeScript** (strict) | Type safety across the entire frontend |
| Rendering | **SSR + Client Components** | SSR for SEO/speed; Client Components for interactive survey forms |
| Deployment | **Vercel** | Zero-config for Next.js, edge functions, automatic preview deployments |

### UI & Design System

| Decision | Choice | Why |
|----------|--------|-----|
| Component library | **shadcn/ui** | Beautiful, accessible, fully customizable — not a dependency, components live in your code |
| Styling | **Tailwind CSS 4** | Utility-first, great DX, native dark mode, design tokens via CSS variables |
| Animations | **Framer Motion** | Page transitions, micro-interactions, form step animations, loading states |
| Icons | **Lucide React** | Consistent icon set, tree-shakeable, already integrated with shadcn/ui |
| Data tables | **TanStack Table v8** | Headless table logic — sorting, filtering, pagination, column visibility for risk assessment tables |
| Charts | **Recharts** | Risk level visualizations, dashboard KPIs, NIOSH zone charts |
| Forms | **React Hook Form + Zod** | Performant form handling with schema validation — critical for the multi-step survey |
| Theme | **Dark/Light + Custom** | CSS variables-based theming with shadcn/ui, user preference saved |
| Fonts | **Inter + JetBrains Mono** | Clean sans-serif for UI, monospace for data/codes |

### Key UI Patterns

**Multi-Step Survey Wizard**
- Framer Motion animated step transitions (slide + fade)
- Progress bar with step names in Italian
- Auto-save per step (debounced to API)
- Steps: Azienda → Persone → Ambienti → Attrezzature → Rischi → Sostanze Chimiche → Riepilogo
- Each step validates before advancing (Zod schemas)
- Responsive: works on iPad/tablet in the field

**Risk Assessment Interface**
- Inline-editable DataTable for P/D scoring per environment
- Color-coded risk levels (green → yellow → orange → red)
- Real-time I = 2*D + P calculation as user adjusts sliders
- Expandable rows showing risk details and prevention measures

**Document Generation Dashboard**
- Card-based grid showing all 16 document types
- Status badges: Draft / Generating / Ready / Delivered
- One-click generate with progress indicator (WebSocket)
- Preview panel (PDF.js or iframe)
- Batch generate all documents for a client

**SDS AI Extraction**
- Drag-and-drop zone for PDF batch upload (up to 20)
- Real-time extraction progress per file
- Side-by-side: original PDF ↔ extracted data table
- Editable cells for human correction before save

### Internationalization

```
app/
  [lang]/              # Dynamic locale segment
    layout.tsx         # Shared layout with sidebar
    dashboard/
    survey/
    documents/
    settings/
```

- **Primary**: Italian (`it`)
- **Fallback**: English (`en`)
- Library: `next-intl` for App Router
- All UI labels, error messages, and help text translated
- Document content is always Italian (domain requirement)

### Responsive & PWA

- Mobile-first with Tailwind breakpoints
- Tablet-optimized survey form (min-width: 768px target)
- PWA manifest for home screen install on tablets
- Offline support for survey form (service worker + IndexedDB cache)
- Photo capture via native camera API on mobile

---

## 2. Backend — FastAPI

### Framework

| Decision | Choice | Why |
|----------|--------|-----|
| Framework | **FastAPI 0.115+** | Async-native, auto OpenAPI docs, Pydantic v2 integration, dependency injection |
| Python | **3.12+** | Performance improvements, better type hints, pattern matching |
| ORM | **SQLAlchemy 2.0** (async) | Mature, well-documented, async support, Alembic migrations |
| Migrations | **Alembic** | Industry standard for SQLAlchemy schema migrations |
| Task queue | **Celery + Redis** | Document generation runs async (187-page .docx takes time) |
| Validation | **Pydantic v2** | Native FastAPI integration, JSON Schema generation, ~5x faster than v1 |
| Auth | **JWT + OAuth2** | FastAPI security utilities, Supabase Auth integration |
| CORS | **FastAPI CORS middleware** | Allow frontend origin (Vercel) |

### API Structure

```
backend/
├── app/
│   ├── main.py                    # FastAPI app, middleware, startup
│   ├── config.py                  # Pydantic BaseSettings (.env)
│   ├── dependencies.py            # Shared DI (db session, current user)
│   │
│   ├── models/                    # SQLAlchemy ORM models
│   │   ├── azienda.py
│   │   ├── persona.py
│   │   ├── ambiente.py
│   │   ├── attrezzatura.py
│   │   ├── sostanza_chimica.py
│   │   ├── valutazione_rischio.py
│   │   ├── mmc.py
│   │   ├── vdt.py
│   │   ├── stress.py
│   │   ├── incendio.py
│   │   ├── microclima.py
│   │   └── user.py
│   │
│   ├── schemas/                   # Pydantic request/response schemas
│   │   ├── azienda.py             # AziendaCreate, AziendaResponse, etc.
│   │   ├── persona.py
│   │   ├── survey.py              # Full survey submission schema
│   │   ├── sds.py                 # SDSExtractionResult
│   │   └── document.py            # DocumentGenerationRequest
│   │
│   ├── api/
│   │   └── v1/
│   │       ├── router.py          # Combines all route files
│   │       ├── aziende.py         # CRUD endpoints
│   │       ├── persone.py
│   │       ├── ambienti.py
│   │       ├── attrezzature.py
│   │       ├── survey.py          # Survey submission + auto-save
│   │       ├── documents.py       # Generate, status, download
│   │       ├── sds.py             # Upload + AI extraction
│   │       ├── rischi.py          # Risk assessment CRUD + calculations
│   │       └── auth.py            # Login, register, refresh
│   │
│   ├── services/                  # Business logic layer
│   │   ├── document_generator/
│   │   │   ├── base.py            # Abstract document generator
│   │   │   ├── dvr_master.py      # DVR generation engine
│   │   │   ├── allegato_mmc.py
│   │   │   ├── allegato_vdt.py
│   │   │   ├── allegato_stress.py
│   │   │   ├── allegato_gestanti.py
│   │   │   ├── allegato_incendio.py
│   │   │   ├── allegato_microclima.py
│   │   │   ├── pee.py
│   │   │   ├── haccp.py
│   │   │   ├── duvri.py
│   │   │   └── pos.py
│   │   ├── ai_service.py          # OpenAI API wrapper
│   │   ├── sds_extractor.py       # SDS PDF → structured data
│   │   ├── risk_calculator.py     # All formula calculations
│   │   ├── gdrive_service.py      # Google Drive upload/download
│   │   └── reference_data.py      # Standard risk library, NIOSH tables
│   │
│   ├── core/
│   │   ├── security.py            # JWT creation, password hashing
│   │   ├── middleware.py           # Logging, error handling
│   │   └── exceptions.py          # Custom exception classes
│   │
│   └── db/
│       ├── session.py             # Async engine + session factory
│       ├── base.py                # Declarative base
│       └── seed.py                # Reference data seeding
│
├── alembic/                       # Database migrations
│   ├── versions/
│   └── env.py
├── tests/
├── requirements.txt
├── Dockerfile
└── render.yaml                    # Render deployment config
```

### Key API Endpoints

```
Auth
  POST   /api/v1/auth/login              # JWT token pair
  POST   /api/v1/auth/refresh            # Refresh access token

Aziende (Companies)
  GET    /api/v1/aziende                  # List client companies
  POST   /api/v1/aziende                  # Create new company
  GET    /api/v1/aziende/{id}             # Get company details
  PUT    /api/v1/aziende/{id}             # Update company
  DELETE /api/v1/aziende/{id}             # Archive company

Survey
  POST   /api/v1/aziende/{id}/survey      # Submit complete survey
  PUT    /api/v1/aziende/{id}/survey/step/{n}  # Auto-save survey step
  GET    /api/v1/aziende/{id}/survey      # Get current survey state

Persone, Ambienti, Attrezzature
  CRUD   /api/v1/aziende/{id}/persone
  CRUD   /api/v1/aziende/{id}/ambienti
  CRUD   /api/v1/aziende/{id}/attrezzature

Risk Assessment
  GET    /api/v1/aziende/{id}/rischi                    # All risks per company
  PUT    /api/v1/aziende/{id}/ambienti/{aid}/rischi     # Update P/D scores
  GET    /api/v1/aziende/{id}/rischi/summary             # Risk matrix summary

SDS Extraction
  POST   /api/v1/aziende/{id}/sds/upload   # Batch upload PDFs (max 20)
  GET    /api/v1/aziende/{id}/sds/status    # Extraction progress
  PUT    /api/v1/aziende/{id}/sds/{sid}     # Correct extracted data
  POST   /api/v1/aziende/{id}/sds/confirm   # Finalize all extractions

Documents
  POST   /api/v1/aziende/{id}/documents/generate  # Trigger generation (async)
  GET    /api/v1/aziende/{id}/documents             # List generated docs
  GET    /api/v1/aziende/{id}/documents/{did}       # Download .docx
  GET    /api/v1/aziende/{id}/documents/{did}/status # Generation progress
  POST   /api/v1/aziende/{id}/documents/batch       # Generate all docs

Calculations (utility)
  POST   /api/v1/calculate/risk-index      # I = 2*D + P
  POST   /api/v1/calculate/niosh           # PLR + IR
  POST   /api/v1/calculate/pmv-ppd         # Thermal comfort
  POST   /api/v1/calculate/fire-risk       # INF + SI + PI

Reference Data
  GET    /api/v1/reference/risks/{env_type}       # Risk library by environment
  GET    /api/v1/reference/equipment/{env_type}    # Equipment checklists
  GET    /api/v1/reference/niosh-tables            # NIOSH lookup tables
```

---

## 3. Database — PostgreSQL (Supabase)

### Why Supabase

| Feature | Benefit for this project |
|---------|------------------------|
| Hosted PostgreSQL | No DB admin, automatic backups, EU region available |
| Auth | Built-in JWT auth with email/password + Google OAuth |
| Storage | S3-compatible buckets for SDS PDFs, photos, generated docs |
| Row Level Security | Multi-tenant data isolation per client company |
| Realtime | WebSocket subscriptions for document generation progress |
| Dashboard | Visual data browser for debugging and support |
| Edge Functions | Optional serverless for webhooks |

### Schema Design (Key Tables)

```sql
-- Multi-tenancy: all data scoped to an organization
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,                    -- "N2O SRL"
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id),
    email TEXT UNIQUE NOT NULL,
    role TEXT CHECK (role IN ('admin', 'operatore_ufficio', 'operatore_campo')),
    full_name TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Core entities (all scoped to organization)
CREATE TABLE aziende (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id),
    ragione_sociale TEXT NOT NULL,
    sede_legale_via TEXT,
    sede_legale_citta TEXT,
    sede_operativa_via TEXT,
    sede_operativa_citta TEXT,
    attivita TEXT,
    codice_ateco TEXT,
    orario_lavoro TEXT,
    metratura_totale NUMERIC,
    zona_sismica INTEGER CHECK (zona_sismica BETWEEN 1 AND 4),
    descrizione_attivita TEXT,           -- AI-generated
    contesto_territoriale TEXT,          -- AI-generated
    survey_status TEXT DEFAULT 'draft',  -- draft/in_progress/completed
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE persone (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    azienda_id UUID REFERENCES aziende(id) ON DELETE CASCADE,
    nominativo TEXT NOT NULL,
    codice_fiscale TEXT,                 -- NEVER sent to AI
    mansione TEXT,
    tipologia_contrattuale TEXT,
    sesso TEXT CHECK (sesso IN ('M', 'F')),
    fascia_eta TEXT CHECK (fascia_eta IN ('>18', '15-18')),
    ruolo_rspp BOOLEAN DEFAULT false,
    ruolo_rls BOOLEAN DEFAULT false,
    ruolo_primo_soccorso BOOLEAN DEFAULT false,
    ruolo_antincendio BOOLEAN DEFAULT false,
    ruolo_preposto BOOLEAN DEFAULT false,
    ruolo_datore_lavoro BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Many-to-many: workers assigned to environments
CREATE TABLE persone_ambienti (
    persona_id UUID REFERENCES persone(id) ON DELETE CASCADE,
    ambiente_id UUID REFERENCES ambienti(id) ON DELETE CASCADE,
    PRIMARY KEY (persona_id, ambiente_id)
);

CREATE TABLE ambienti (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    azienda_id UUID REFERENCES aziende(id) ON DELETE CASCADE,
    nome TEXT NOT NULL,                  -- "UFFICIO AMMINISTRATIVO"
    tipo TEXT NOT NULL,                  -- Enum: Ufficio, Magazzino, Cucina, etc.
    superficie_mq NUMERIC,
    preposto_id UUID REFERENCES persone(id),
    descrizione_attivita TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE attrezzature (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    azienda_id UUID REFERENCES aziende(id) ON DELETE CASCADE,
    descrizione TEXT NOT NULL,
    marcatura_ce BOOLEAN DEFAULT false,
    verifiche_periodiche BOOLEAN DEFAULT false
);

CREATE TABLE sostanze_chimiche (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    azienda_id UUID REFERENCES aziende(id) ON DELETE CASCADE,
    nome_prodotto TEXT NOT NULL,
    produttore TEXT,
    attivita_uso TEXT,
    pittogrammi TEXT[],                  -- Array: ['GHS02', 'GHS07']
    stato_miscela TEXT,                  -- Liquido/Solido/Gas
    frasi_h TEXT[],                      -- Hazard statements
    frasi_p TEXT[],                      -- Precautionary statements
    ai_extracted BOOLEAN DEFAULT false,  -- Was this AI-extracted from SDS?
    ai_confidence NUMERIC,               -- Extraction confidence score
    human_reviewed BOOLEAN DEFAULT false, -- Has operator reviewed?
    sds_file_path TEXT,                  -- Storage path to original PDF
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE valutazioni_rischio (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ambiente_id UUID REFERENCES ambienti(id) ON DELETE CASCADE,
    categoria_rischio TEXT NOT NULL,      -- 11 categories
    applicabile BOOLEAN DEFAULT false,
    pericolo TEXT,
    condizioni_esposizione TEXT,
    rischio TEXT,
    misure_prevenzione TEXT,
    probabilita_p INTEGER CHECK (probabilita_p BETWEEN 1 AND 4),
    danno_d INTEGER CHECK (danno_d BETWEEN 1 AND 4),
    indice_i INTEGER GENERATED ALWAYS AS (2 * danno_d + probabilita_p) STORED,
    livello_rischio TEXT GENERATED ALWAYS AS (
        CASE
            WHEN (2 * danno_d + probabilita_p) <= 4 THEN 'ACCETTABILE'
            WHEN (2 * danno_d + probabilita_p) <= 6 THEN 'MODESTO'
            WHEN (2 * danno_d + probabilita_p) <= 8 THEN 'GRAVE'
            ELSE 'GRAVISSIMO'
        END
    ) STORED
);

-- Assessment tables for each attachment type follow the same pattern
-- (mmc_valutazioni, vdt_valutazioni, stress_valutazioni, etc.)
-- Full schemas defined during Module development

CREATE TABLE documenti_generati (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    azienda_id UUID REFERENCES aziende(id) ON DELETE CASCADE,
    tipo_documento TEXT NOT NULL,         -- 'dvr_master', 'allegato_mmc', etc.
    versione INTEGER DEFAULT 1,
    status TEXT DEFAULT 'pending',        -- pending/generating/ready/error
    file_path TEXT,                       -- Supabase Storage path
    gdrive_file_id TEXT,                 -- Google Drive file ID (after upload)
    generation_started_at TIMESTAMPTZ,
    generation_completed_at TIMESTAMPTZ,
    generated_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT now()
);
```

### Row Level Security (Multi-Tenant)

```sql
-- Users can only see data belonging to their organization
ALTER TABLE aziende ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users see own org data" ON aziende
    FOR ALL
    USING (organization_id = (
        SELECT organization_id FROM users WHERE id = auth.uid()
    ));

-- Same pattern applied to all tables via azienda_id chain
```

---

## 4. AI Integration — OpenAI

### Model Selection

| Use Case | Model | Why | Est. Cost |
|----------|-------|-----|-----------|
| **SDS PDF extraction** | `gpt-4.1` | Vision + structured outputs — reads PDF pages as images + text, extracts into Pydantic schema | ~$0.02/page |
| **Company description** | `gpt-4.1-mini` | Text generation from structured data, cheaper for creative writing | ~$0.005/request |
| **Improvement measures** | `gpt-4.1-mini` | Suggests measures based on risk profile, cost-effective | ~$0.005/request |
| **Batch SDS (600 sheets)** | `gpt-4.1` + Batch API | 50% cost discount on batch, async processing | ~$6-12 per client |

### SDS Extraction Architecture

```python
from pydantic import BaseModel, Field
from openai import OpenAI

class SDSExtraction(BaseModel):
    """Structured output schema for chemical Safety Data Sheet extraction."""
    nome_prodotto: str = Field(description="Product commercial name")
    produttore: str = Field(description="Manufacturer/supplier name")
    pittogrammi: list[str] = Field(description="GHS pictogram codes, e.g. ['GHS02', 'GHS07']")
    stato_miscela: str = Field(description="Physical state: Liquido, Solido, or Gas")
    frasi_h: list[str] = Field(description="Hazard statements, e.g. ['H225', 'H319']")
    frasi_p: list[str] = Field(description="Precautionary statements, e.g. ['P210', 'P305+P351+P338']")
    punto_infiammabilita: str | None = Field(description="Flash point if listed")
    classificazione_pericolo: str | None = Field(description="Hazard classification text")

client = OpenAI()

# Upload SDS PDF via Files API
file = client.files.create(
    file=open("sds_document.pdf", "rb"),
    purpose="user_data"
)

# Extract with structured output + vision
response = client.responses.parse(
    model="gpt-4.1",
    input=[
        {
            "role": "system",
            "content": (
                "You are an expert chemical safety data sheet (SDS/SdS) analyst. "
                "Extract the requested fields from this Italian SDS document. "
                "Be precise with GHS pictogram codes and H/P phrase numbers. "
                "If a field is not found, return null."
            )
        },
        {
            "role": "user",
            "content": [
                {"type": "input_text", "text": "Extract all safety data from this SDS:"},
                {"type": "input_file", "file_id": file.id}
            ]
        }
    ],
    text_format=SDSExtraction,
)

extraction = response.output_parsed  # Typed SDSExtraction object
```

### Privacy Guardrails

```python
# In ai_service.py — NEVER send personal data to OpenAI
PROHIBITED_FIELDS = ['codice_fiscale', 'documento_identita', 'dati_sanitari']

def sanitize_for_ai(data: dict) -> dict:
    """Strip personal/health data before sending to AI API."""
    return {k: v for k, v in data.items() if k not in PROHIBITED_FIELDS}
```

---

## 5. Document Generation — python-docx

### Architecture

```
Document Generator Pipeline:

  Survey Data (DB)
        │
        ▼
  ┌─────────────┐
  │ Data Loader  │  ← Fetches all entities for an Azienda
  └──────┬──────┘
         │
         ▼
  ┌─────────────┐
  │ Template     │  ← Loads .docx template from templates/
  │ Engine       │     Identifies placeholder sections
  └──────┬──────┘
         │
         ▼
  ┌─────────────┐
  │ Section      │  ← Each Part has its own generator
  │ Generators   │     Part I: company data
  │  (per Part)  │     Part II: methodology (static)
  └──────┬──────┘     Part III: risk assessment per environment
         │            Part IV: improvement measures
         ▼
  ┌─────────────┐
  │ Formatter    │  ← Cover page, TOC, headers, footers, N2O logo
  └──────┬──────┘
         │
         ▼
  ┌─────────────┐
  │ Output       │  ← Save to Supabase Storage
  │ .docx file   │     Upload to Google Drive
  └─────────────┘     Update status in documenti_generati
```

### Key Libraries

| Library | Version | Purpose |
|---------|---------|---------|
| `python-docx` | 1.1+ | .docx creation and manipulation |
| `pythermalcomfort` | 2.10+ | PMV/PPD and PHS calculations |
| `openpyxl` | 3.1+ | HACCP Excel forms generation |
| `Pillow` | 10+ | Image processing for cover pages and photos |

---

## 6. File Storage Strategy

| File Type | Storage | Lifecycle |
|-----------|---------|-----------|
| SDS PDFs (uploaded) | Supabase Storage `/sds/{azienda_id}/` | Permanent — reference material |
| Site photos (uploaded) | Supabase Storage `/photos/{azienda_id}/` | Permanent — embedded in docs |
| Generated .docx | Supabase Storage `/documents/{azienda_id}/` | Versioned — keep all versions |
| Final delivery | Google Drive (client folder) | Uploaded after operator approval |
| Document templates | Git repo `/templates/` | Version controlled |

---

## 7. Authentication & Authorization

### Strategy: Supabase Auth + FastAPI JWT Verification

```
┌──────────┐     ┌──────────┐     ┌──────────┐
│ Frontend  │────▶│ Supabase │────▶│ FastAPI   │
│ Next.js   │     │ Auth     │     │ Verify    │
│           │◀────│ JWT      │     │ JWT       │
└──────────┘     └──────────┘     └──────────┘
```

1. User logs in via Supabase Auth (email/password or Google OAuth)
2. Frontend receives JWT access + refresh tokens
3. Frontend sends JWT in `Authorization: Bearer` header
4. FastAPI middleware verifies JWT signature with Supabase public key
5. User's `organization_id` extracted from JWT claims
6. All DB queries scoped to that organization

### Roles

| Role | Italian | Permissions |
|------|---------|-------------|
| `admin` | Amministratore | Full CRUD, manage users, generate all docs, settings |
| `operatore_ufficio` | Operatore in Ufficio | Edit surveys, adjust risks, generate docs, review AI output |
| `operatore_campo` | Operatore sul Campo | Create/edit surveys, upload photos/SDS, read-only docs |

---

## 8. Deployment Architecture

### Production

```
┌─────────────────────────────────────────────────────┐
│                     Vercel                           │
│  ┌─────────────────────────────────┐                │
│  │ Next.js 16 Frontend             │                │
│  │ • SSR + Edge Functions          │                │
│  │ • CDN for static assets         │                │
│  │ • Auto-deploy from main branch  │                │
│  └─────────────────────────────────┘                │
└─────────────────────────────────────────────────────┘
                        │
                   HTTPS API calls
                        │
┌─────────────────────────────────────────────────────┐
│                   Render.com                         │
│  ┌──────────────────┐  ┌──────────────────┐        │
│  │ FastAPI Backend   │  │ Celery Worker    │        │
│  │ Web Service       │  │ Background       │        │
│  │ (auto-scale)      │  │ Service          │        │
│  └──────────────────┘  └──────────────────┘        │
│  ┌──────────────────┐                               │
│  │ Redis             │                               │
│  │ (task queue +     │                               │
│  │  caching)         │                               │
│  └──────────────────┘                               │
└─────────────────────────────────────────────────────┘
                        │
┌─────────────────────────────────────────────────────┐
│                   Supabase (EU Region)               │
│  ┌──────────────┐ ┌───────────┐ ┌────────────┐     │
│  │ PostgreSQL   │ │ Auth      │ │ Storage    │     │
│  │ Database     │ │ (JWT)     │ │ (S3-compat)│     │
│  └──────────────┘ └───────────┘ └────────────┘     │
└─────────────────────────────────────────────────────┘
```

### Environment Variables

```bash
# Backend (.env)
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=eyJ...
SUPABASE_JWT_SECRET=your-jwt-secret

OPENAI_API_KEY=sk-...
OPENAI_MODEL_EXTRACTION=gpt-4.1
OPENAI_MODEL_GENERATION=gpt-4.1-mini

GOOGLE_CLIENT_ID=501670694075-...
GOOGLE_CLIENT_SECRET=...
GOOGLE_DRIVE_FOLDER_ID=13aHCy8D78JwJzgffxYbqe7Nmyed84may

REDIS_URL=redis://...
CORS_ORIGINS=["https://n2o-dvr.vercel.app"]

# Frontend (.env.local)
NEXT_PUBLIC_API_URL=https://n2o-dvr-api.onrender.com
NEXT_PUBLIC_SUPABASE_URL=https://xxxxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...
```

---

## 9. Development Workflow

### Local Development

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev    # → http://localhost:3000

# Database
# Use Supabase local dev (supabase CLI)
supabase start
```

### Git Branching

```
main (production — auto-deploys)
  └── develop (staging)
        ├── feature/survey-form
        ├── feature/dvr-generator
        └── feature/sds-extraction
```

### CI/CD

- **Frontend**: Vercel auto-deploys from `main`, preview deploys on PRs
- **Backend**: Render auto-deploys from `main`, manual deploy for staging
- **Database**: Alembic migrations run on deploy via release command

---

## 10. Key Libraries & Versions

### Backend (Python)

```txt
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
sqlalchemy[asyncio]>=2.0.30
asyncpg>=0.29.0
alembic>=1.13.0
pydantic>=2.7.0
pydantic-settings>=2.3.0
python-docx>=1.1.0
openai>=1.68.0
google-api-python-client>=2.130.0
google-auth>=2.30.0
celery[redis]>=5.4.0
pythermalcomfort>=2.10.0
python-multipart>=0.0.9
pillow>=10.3.0
openpyxl>=3.1.0
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
httpx>=0.27.0
```

### Frontend (Node.js)

```json
{
  "dependencies": {
    "next": "^16.1.0",
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "typescript": "^5.5.0",
    "@supabase/supabase-js": "^2.45.0",
    "@supabase/ssr": "^0.4.0",
    "next-intl": "^4.0.0",
    "@tanstack/react-table": "^8.20.0",
    "react-hook-form": "^7.52.0",
    "@hookform/resolvers": "^3.9.0",
    "zod": "^3.23.0",
    "framer-motion": "^11.3.0",
    "recharts": "^2.12.0",
    "lucide-react": "^0.400.0",
    "tailwindcss": "^4.0.0",
    "class-variance-authority": "^0.7.0",
    "clsx": "^2.1.0",
    "tailwind-merge": "^2.4.0",
    "sonner": "^1.5.0",
    "react-dropzone": "^14.2.0"
  }
}
```

---

## 11. Configuration & Customization

The system is **fully configurable** through an admin settings interface:

| Setting | Scope | Description |
|---------|-------|-------------|
| Risk library | Per environment type | Add/edit/remove standard risks, default P/D values, prevention measures |
| Equipment checklists | Per environment type | Customize equipment lists shown in survey per environment type |
| Document templates | Global | Upload custom .docx templates with different branding per client |
| AI prompts | Global | Edit system prompts for company description, improvement measures |
| NIOSH lookup tables | Global | Standard NIOSH factors (editable for custom scenarios) |
| Stress indicators | Global | INAIL ~50 indicators with scoring rules |
| User roles | Per organization | Assign permissions per user |
| Theme | Per user | Dark/light mode, accent color |
| Language | Per user | Italian (default) or English interface |
| Document output | Per company | Cover page logo, header/footer text, revision numbering |

---

*© 2026 Niuexa. Confidential — prepared for N2O SRL.*
