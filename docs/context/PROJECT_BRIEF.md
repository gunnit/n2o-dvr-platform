> **NIUEXA** | AI-Powered Business Automation  
> *N2O DVR Automation Platform — Project Documentation*  
> Version 1.0 | April 2026 | Gregor Maric  
> Confidential — Niuexa & N2O SRL

---

# Project Brief

## Client

**N2O SRL** - Italian workplace safety consultancy based near Milan (Gorgonzola/Gessate area)
- **Key contact**: Luca Marchetti (team lead, domain expert)
- **Business**: Produces DVR and safety documentation for client companies across various sectors (offices, warehouses, food service, construction, dental clinics, kindergartens, etc.)

## The Problem

The current process for producing a single complete DVR package takes **up to one full week**:

| Pain Point | Current Time | Details |
|------------|-------------|---------|
| Chemical SDS entry | 3-4 days | For clients with ~600 chemical substances, manual data entry from safety data sheets |
| Company description | 30-45 min | Written manually from scratch each time |
| Risk assessment per room | Variable | Companies can have 1,000+ work environments |
| Equipment entry | 100% manual | No pre-loaded checklists |
| Employee data | 100% manual | Paper forms transcribed to Word |
| Post-production formatting | Significant | Manual Word formatting, headers, tables |

**Infrastructure risk**: The entire current application lives on a **single USB stick with no backup**. Total data loss is one accident away.

## The Solution

A web-based platform that:
1. **Replaces the paper survey** with a digital form (tablet/smartphone) used on-site
2. **Auto-generates 16 distinct documents** (13 document types) from the collected data
3. **Uses AI** for chemical SDS extraction, company descriptions, and improvement suggestions
4. **Outputs professional .docx files** ready for review (not data entry)

Target: **60-70% time reduction** per DVR package.

## Scope: 15 Deliverables

> 13 document types + 2 platform features (digital survey form, AI SDS extraction).
> Document types expand to **16 distinct documents** when counting sector-specific variants (3 biological risk, 2 emergency plan).

### Core (Phase 2)
1. **Digital Survey Form** - Replaces paper, used on-site
2. **DVR Master** (~187 pages) - The core risk assessment document
3. **AI SDS Extraction** - Batch upload chemical safety data sheets

### DVR Attachments (Phase 3)
4. **MMC** - Manual handling (NIOSH calculation)
5. **VDT** - Display screen equipment
6. **Stress Lavoro-Correlato** - Work-related stress (INAIL method)
7. **Gestanti** - Pregnant worker assessment
8. **Rischio Incendio** - Fire risk assessment
9. **Microclima** - Thermal comfort (PMV/PPD)
10. **Microclima Caldo Severo** - Severe heat (PHS method)
11. **Rischio Biologico** - Biological risk (sector-specific: nursery, food, dental)

### Complementary Documents (Phase 4)
12. **PEE** - Emergency & evacuation plan
13. **HACCP** - Food safety manual + 16 self-check forms
14. **DUVRI** - Contractor interference risk
15. **POS** - Construction site safety plan

## Key Design Principle

> "Il nostro deve essere solo una questione di revisione, non di inserimento del dato."
> *"For us it should only be a matter of review, not data entry."*
> -- Luca Marchetti, meeting of Feb 26, 2026

The operator's role shifts from **data entry** to **review and validation**. The system does the heavy lifting; humans ensure accuracy and apply expert judgment.

## Shared Data Architecture

All documents share a common data layer:
- **Azienda** (company) data entered once, propagated across all generated documents
- **Persona** (people) with roles, qualifications, assignments
- **Ambiente** (work environments) with risk profiles
- **Attrezzatura** (equipment) with CE marking
- **Sostanze Chimiche** (chemicals) extracted by AI from SDS

## Timeline & Budget

| Phase | Duration | Cost |
|-------|----------|------|
| 1. Setup & Analysis | 1-2 weeks | EUR 1,200 |
| 2. Core (Survey + DVR + AI) | 3-4 weeks | EUR 4,800 |
| 3. DVR Attachments (8 modules) | 3-4 weeks | EUR 4,200 |
| 4. Complementary Docs (4 types, 5 docs) | 2-3 weeks | EUR 2,500 |
| 5. Test & Go-Live | 1-2 weeks | EUR 1,300 |
| **Total** | **10-15 weeks** | **EUR 14,000** |

Payment: 30% kickoff / 30% Phase 2 complete / 40% go-live.

## Privacy & Compliance

- GDPR compliant data processing
- Personal data (codice fiscale, ID docs) never sent to AI APIs
- AI used only for: SDS extraction, company descriptions, improvement suggestions
- All AI output requires human review
- European cloud hosting with daily backups

## Stakeholders

| Person | Role | Responsibility |
|--------|------|---------------|
| Gregor Maric | Niuexa Co-CEO & CTO | System design & development |
| Luca Marchetti | N2O Team Lead | Domain expertise, requirements, validation |
| N2O Operators | End users | Field surveys, document review |

---

*© 2026 Niuexa. Confidential — prepared for N2O SRL.*
