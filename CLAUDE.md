# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# N2O DVR Automation Platform

## Project Overview

Automated generation of Italian workplace safety documentation (16 documents across 13 types, anchored by the DVR Master) for N2O SRL, a safety consultancy. The system replaces manual data entry with a digital survey form and AI-powered document generation, targeting 60-70% time reduction.

**Client**: N2O SRL (Luca Marchetti & team) - workplace safety consultants
**Builder**: Niuexa (Gregor Maric, Co-CEO & CTO)
**Core principle**: "Il nostro deve essere solo una questione di revisione, non di inserimento del dato." (Review only, not data entry)

## Domain Glossary

| Term | Full Name | Description |
|------|-----------|-------------|
| DVR | Documento di Valutazione dei Rischi | Master risk assessment document (~187 pages) |
| MMC | Movimentazione Manuale dei Carichi | Manual handling assessment (NIOSH method) |
| VDT | Videoterminali | Display screen equipment assessment |
| SDS/SdS | Schede di Sicurezza | Safety Data Sheets (chemical) |
| PEE | Piano di Emergenza ed Evacuazione | Emergency & evacuation plan |
| DUVRI | Doc. Unico Valutazione Rischi Interferenze | Interference risk assessment (contractors) |
| POS | Piano Operativo di Sicurezza | Construction site safety plan |
| HACCP | Hazard Analysis Critical Control Points | Food safety management system |
| RSPP | Responsabile Servizio Prevenzione Protezione | Safety prevention manager |
| RLS | Rappresentante dei Lavoratori per la Sicurezza | Workers' safety representative |
| DdL | Datore di Lavoro | Employer |
| D.Lgs. 81/2008 | Testo Unico Sicurezza | Core Italian workplace safety law |

## Key Formulas

- **Risk Index**: `I = 2*D + P` (NOT the standard P x D). Range 3-12. Levels: 3-4=Accettabile, 5-6=Modesto, 7-8=Grave, 9-12=Gravissimo
- **NIOSH PLR**: `PLR = CP x A x B x C x D x E x F`. IR = P/PLR. Green<=0.75, Yellow 0.75-1.0, Red>1.0
- **VDT Exposure**: >= 20 hours/week = Exposed
- **Fire Risk**: INF+SI+PI (each 1-3). Sum 3-4=Low, 5-7=Medium, 8-9=High

## Language & Content

- All generated documents: **Italian**
- Code, comments, variable names: **English**
- UI labels: **Italian** (with English fallback where needed)

## Privacy & Data Rules

- **NEVER send to AI APIs**: codice fiscale, identity documents, personal health data
- AI is used ONLY for: SDS chemical extraction, company description generation, improvement measures suggestions
- All AI output requires human review before final inclusion
- GDPR compliance required throughout

## Google Drive Access

Access client documents via Google OAuth credentials:
- **Token**: `credentials/token.json` (has Drive, Docs, Sheets, Gmail, Calendar scopes)
- **Client secret**: `credentials/client_secret_501670694075-*.json`
- **Main folder**: `13aHCy8D78JwJzgffxYbqe7Nmyed84may`
- **Templates folder**: `16IicFhfHg4Fzh12_DM_J3tNFy4j8Cbpa` (DOCUMENTI D.LGS. 81.08)
- **HACCP forms folder**: `1dS-QEGaSTmCZjYRzu6Ldsf47mzTOnidR`

```python
# Access pattern
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import json

with open('credentials/token.json') as f:
    token_data = json.load(f)
creds = Credentials(
    token=token_data['token'],
    refresh_token=token_data['refresh_token'],
    token_uri=token_data['token_uri'],
    client_id=token_data['client_id'],
    client_secret=token_data['client_secret'],
    scopes=token_data['scopes']
)
service = build('drive', 'v3', credentials=creds)
```

## Document Output

- Format: `.docx` with professional formatting, cover page, logo, table of contents
- Template-based generation using python-docx
- Each document shares a common data layer (Azienda, Persona, Ambiente entities)

## Project Documentation (`docs/context/`)

All project docs are branded with Niuexa header/footer, version 1.0, April 2026. Read the relevant doc BEFORE working on any module.

### Business & Scope (read first for any task)

| Document | What's Inside | When to Reference |
|----------|--------------|-------------------|
| `PROJECT_BRIEF.md` | Scope (15 deliverables, 16 docs), budget (EUR 14k), timeline (10-15 weeks), 5 phases, payment terms, stakeholders | Starting any new phase, scoping work, client context |
| `USER_STORIES.md` | 5 epics, 3 personas (campo/ufficio/admin), 30+ user stories (US-1.1 through US-5.4) | Building any UI, defining acceptance criteria |
| `DOCUMENT_CATALOG.md` | All 16 documents: page counts, table counts, static/dynamic ratios, complexity ratings, data shared with DVR | Deciding which document to build next, understanding dependencies |

### Technical Design (read before writing code)

| Document | What's Inside | When to Reference |
|----------|--------------|-------------------|
| `ARCHITECTURE.md` | Full tech stack (Next.js 16 + FastAPI + Supabase), DB schema with SQL, all API endpoints, deployment diagram, project folder structure, library versions, auth flow, config options | **Every coding session** — this is the system blueprint |
| `DATA_MODEL.md` | All entities (Azienda, Persona, Ambiente, Attrezzatura, SostanzaChimica) with field-level detail, types, privacy flags, cross-document usage, assessment entities (MMC, VDT, Stress, Incendio, Microclima) | Writing ORM models, building forms, API schemas |
| `DVR_TEMPLATE_MAPPING.md` | Structural analysis of DVR Master .docx — 111 tables cataloged, 2,445 paragraphs, 4 document parts with exact boundaries, environment risk block pattern (7 envs × identical structure), 41 dynamic/36 static/13 mixed tables, 269 dynamic cells mapped to data fields | **Building the DVR generation engine (Module 2)** — this IS the spec |

### Domain Knowledge (read for calculations, legal compliance, reference data)

| Document | What's Inside | When to Reference |
|----------|--------------|-------------------|
| `FORMULAS_AND_CALCULATIONS.md` | All 7 calculation methods: Risk Index (I=2*D+P), NIOSH (PLR/IR), VDT threshold, INAIL Stress scoring, Fire risk (INF+SI+PI), PMV/PPD thermal comfort, PHS severe heat. With input/output specs and Python library recommendations | Implementing any calculator, risk assessment logic |
| `LEGISLATION_REFERENCE.md` | 24 Italian/EU laws and standards with article numbers, URLs, and which documents they affect. Core: D.Lgs. 81/2008, D.Lgs. 151/2001, D.M. 03/09/2021, Reg. CE 852/2004, UNI EN ISO 7730/7933/11228 | Legal compliance, document boilerplate text, understanding requirements |
| `REFERENCE_DATA.md` | Extracted from real templates — NIOSH Factor tables (A-F with exact values, 18-row Factor F table), 60+ hazard items across 11 risk categories, 76 INAIL stress indicators with scoring rules, fire risk INF/SI/PI definitions, VDT checklist, P/D scale descriptions | **Database seeding**, populating survey form dropdowns, risk library, lookup tables |

### Planning & Structure (read for module planning, document generation)

| Document | What's Inside | When to Reference |
|----------|--------------|-------------------|
| `DOCUMENT_STRUCTURE.md` | Section-by-section breakdown of every document type: static vs dynamic classification per section, automation approach per section. Includes all DVR attachments and complementary docs | Planning document generators, understanding what's static boilerplate vs dynamic |
| `AUTOMATION_PLAN.md` | 15 modules (Modules 1-15) across Phases 2-4: input/output per module, method, time savings estimate, complexity rating. Summary table with savings ranges | Sprint planning, prioritizing modules, estimating effort |

### Key Cross-References

- **Building the survey form?** → USER_STORIES (Epic 1) + DATA_MODEL (entities) + REFERENCE_DATA (risk library + equipment checklists) + ARCHITECTURE (API endpoints)
- **Building DVR generator?** → DVR_TEMPLATE_MAPPING (the spec) + DOCUMENT_STRUCTURE (Part I-IV breakdown) + DATA_MODEL (field sources) + FORMULAS (risk index)
- **Building an attachment?** → DOCUMENT_CATALOG (which attachment) + DOCUMENT_STRUCTURE (section breakdown) + FORMULAS (relevant calculation) + REFERENCE_DATA (lookup tables)
- **AI integration?** → ARCHITECTURE (OpenAI setup + Pydantic schemas) + USER_STORIES (US-1.8 to US-1.10 for SDS, US-2.1/2.6 for AI generation)

## Template Documents (`templates/`)

32 real completed Italian safety documents — the ground truth for structure and formatting:

| Template | Format | Parseable | Phase |
|----------|--------|-----------|-------|
| DVR RISCHIO MASTER | .docx (4.8 MB) | Yes — fully mapped in DVR_TEMPLATE_MAPPING.md | 2 |
| ALLEGATO RISCHIO MMC | .docx (2.3 MB) | Yes — NIOSH tables extracted to REFERENCE_DATA.md | 3 |
| ALLEGATO RISCHIO VDT | .docx (2.2 MB) | Yes — VDT criteria extracted | 3 |
| ALLEGATO STRESS DA LAVORO CORRELATO | .docx (2.2 MB) | Yes — 76 indicators extracted | 3 |
| ALLEGATO GESTANTI | .docx (120 KB) | Yes | 3 |
| ALLEGATO RISCHIO INCENDIO | .docx (112 KB) | Yes — fire scoring extracted | 3 |
| ALLEGATO MICROCLIMA | .pdf (367 KB) | No — PDF, needs manual review | 3 |
| ALLEGATO MICROCLIMA CALDO SEVERO | .pdf (2.5 MB) | No — PDF, needs manual review | 3 |
| ALLEGATO RISCHIO BIOLOGICO ALIMENTARE | .doc (2.4 MB) | No — legacy .doc binary | 3 |
| RISCHIO BIOLOGICO - ASILO | .pdf (3.3 MB) | No — PDF | 3 |
| RISCHIO BIOLOGICO - DENTISTI | .doc (6.6 MB) | No — legacy .doc binary | 3 |
| DUVRI | .docx (353 KB) | Yes | 4 |
| HACCP | .docx (712 KB) | Yes | 4 |
| PIANO GESTIONE EMERGENZE - AZIENDA | .docx (1.1 MB) | Yes | 4 |
| PIANO GESTIONE EMERGENZE - COMUNE | .docx (7.2 MB) | Yes | 4 |
| POS | .docx (12.9 MB) | Yes | 4 |
| `haccp/` subfolder | 15 .docx + 1 .xlsx | Yes — 16 HACCP self-check forms (SA-01 to SA-16) | 4 |

**5 templates are unparseable** (PDF/legacy .doc) — all Phase 3 attachments. Will need manual analysis or conversion before those modules are built.

## Project Status

**Phase: Ready to Build** — Planning/Analysis complete. All 11 context docs written, architecture decided, templates analyzed, reference data extracted. Next step: Phase 2 project setup and core development.

## Development Phases

1. **Setup & Analysis** (1-2 weeks) - Architecture, data model, environment
2. **Core Development** (3-4 weeks) - Digital survey form, DVR Master engine, AI integration
3. **DVR Attachments** (3-4 weeks) - MMC, VDT, SDS AI, Stress, Gestanti, Microclima, Biologico, Incendio
4. **Complementary Docs** (2-3 weeks) - PEE, HACCP, DUVRI, POS
5. **Test & Go-Live** (1-2 weeks) - Real case validation, operator training

## Tech Stack

- **Frontend**: Next.js 16 (App Router) + shadcn/ui + Tailwind CSS 4 + Framer Motion + TanStack Table
- **Backend**: FastAPI (Python 3.12+) + Pydantic v2 + SQLAlchemy 2.0 Async + Celery + Redis
- **Database**: PostgreSQL on Supabase (EU region) with Row Level Security
- **AI**: OpenAI GPT-4.1 (SDS extraction via vision/structured outputs) + GPT-4.1-mini (descriptions, suggestions)
- **Document generation**: python-docx + pythermalcomfort (PMV/PPD, PHS calculations)
- **Storage**: Supabase Storage (uploads) + Google Drive (final delivery)
- **Auth**: Supabase Auth (JWT) verified by FastAPI
- **Deployment**: Vercel (frontend) + Render.com (backend + workers)
- **Google APIs**: Drive, Docs, Sheets, Gmail, Calendar (OAuth tokens in `credentials/`)

## Analysis Spreadsheet

The comprehensive analysis of all documents, data model, formulas, legislation, and automation plan is in Google Drive:
https://docs.google.com/spreadsheets/d/1jPt5668oSpxtiki-X4s9ZnAWBPmRJbsp/edit?rtpof=true

8 tabs: Panoramica Documenti, Modello Dati, Piano Automazione, Schede HACCP, Formule e Calcoli, Struttura Documenti, Normativa di Riferimento, Mappatura Doc-Normativa
