> **NIUEXA** | AI-Powered Business Automation  
> *N2O DVR Automation Platform — Project Documentation*  
> Version 1.0 | April 2026 | Gregor Maric  
> Confidential — Niuexa & N2O SRL

---

# Document Structure Breakdown

## DVR Rischio Master (~187 pages, 111 tables)

| Section | Content | Static/Dynamic | Data Source | Automation |
|---------|---------|----------------|-------------|------------|
| **Parte I - Presentazione Azienda** | Anagrafica, dipendenti, descrizione azienda, org. sicurezza, ambienti, attrezzature, sostanze chimiche, fattori pericolo | DYNAMIC | Scheda Rilevazione | Digital form -> auto-populate |
| **Parte II - Metodologia** | Legal definitions, P/D formula, assessment scales | STATIC | D.Lgs. 81/2008 | Fixed template |
| **Parte III - Valutazione Rischi** | Per environment: identification sheet + SI/NO risk matrix + assessment tables per category (up to 7 sub-tables per env) | SEMI-DYNAMIC | Survey + expert judgment | Standard risk library per env type. Operator selects/modifies P and D |
| Parte III - Rischi Specifici | Per employee: list of role-specific risks | DYNAMIC | Role + assigned environments | Auto-derivable from role + env risks |
| Parte III - DPI | Per worker: assigned PPE with brand/model | DYNAMIC | Role + specific risks | PPE suggestion based on risks. Brand/model manual |
| Parte III - Formazione | Training program per role with periodicity | SEMI-DYNAMIC | Employee roles | Template per role. Periodicity from regulation |
| **Parte IV - Procedure Miglioramento** | Law management, health surveillance, training, PPE, infrastructure, sensitive workers, procurement, contracts | STATIC | Regulations | Fixed template (identical for all DVR) |
| Parte IV - Misure Miglioramento | Table: measure, procedure, resources, responsible, timeline | DYNAMIC | Risk assessment + inspection | AI can suggest measures based on identified risks |
| **Dichiarazione** | Signatures: DdL, RSPP, MC, RLS + date + location | DYNAMIC | Org. sicurezza | Auto-populate from master data |

---

## DVR Attachments (7 documents)

### Allegato MMC
| Section | Static/Dynamic | Automation |
|---------|----------------|------------|
| Methodology NIOSH | STATIC | Fixed template explaining NIOSH method, factor tables, formulas |
| Assessment Sheets | DYNAMIC | One sheet per worker with all parameters + PLR/IR calculation |
| Summary Table | DYNAMIC | All workers with Green/Yellow/Red classification |

### Allegato VDT
| Section | Static/Dynamic | Automation |
|---------|----------------|------------|
| Risk Factors + Workstations | SEMI-DYNAMIC | Theory static. Workstation list dynamic |
| Assessment Sheets | DYNAMIC | Per worker: hours/week, exposed/not exposed |
| Summary Table | DYNAMIC | All workers with exposure classification |

### Allegato Stress Lavoro-Correlato
| Section | Static/Dynamic | Automation |
|---------|----------------|------------|
| INAIL Methodology | STATIC | Fixed template |
| Indicator Checklist | DYNAMIC | ~50 SI/NO indicators in 3 areas. Digital form with real-time scoring |
| Results + Action Plan | DYNAMIC | Auto-calculated risk level + generated corrective measures |

### Allegato Gestanti
| Section | Static/Dynamic | Automation |
|---------|----------------|------------|
| Risk Mapping Table | SEMI-DYNAMIC | Risk factors vs effects vs provisions. Cross-reference with DVR |
| Acknowledgment Forms | DYNAMIC | Per female worker signature |

### Allegato Rischio Incendio
| Section | Static/Dynamic | Automation |
|---------|----------------|------------|
| Area Sheets | DYNAMIC | Environment characteristics + INF/SI/PI assessment |
| Summary Table | DYNAMIC | All areas with risk level |
| Prevention Measures | SEMI-DYNAMIC | Per area, based on risk level |

### Allegato Microclima (Moderate)
| Section | Static/Dynamic | Automation |
|---------|----------------|------------|
| Measurements + Calculations | DYNAMIC | Measured parameters + auto-calculated PMV/PPD per environment |
| Corrective Measures | SEMI-DYNAMIC | Based on PMV results |

### Allegato Microclima Caldo Severo (PHS)
| Section | Static/Dynamic | Automation |
|---------|----------------|------------|
| PHS Methodology | STATIC | Fixed template explaining thermal balance equation (M-W = Cres+Eres+K+C+R+E+S) |
| Input Parameters | DYNAMIC | 13+ parameters: Ta, Tr, Pa, Va, walking direction/speed, posture, M, Icl, Fr, Ap, acclimatization, water access |
| Dlim Calculation | DYNAMIC | Maximum exposure time based on 3 criteria (rectal temperature, dehydration). Different limits for acclimatized vs non-acclimatized |
| Assessment Summary | DYNAMIC | Per role: Dlim, final rectal temperature, water loss |

### Allegato Rischio Biologico
| Section | Static/Dynamic | Automation |
|---------|----------------|------------|
| Biological Agents | SEMI-DYNAMIC | Sector-specific knowledge base |
| Prevention Measures | SEMI-DYNAMIC | Sector-specific, contextual |

Three sector variants:
- **Asilo (Nursery)**: ~17 pages, qualitative, pathogen knowledge base
- **Alimentare (Food/Meat)**: ~65 pages, Lombardy region specific, legacy .doc
- **Dentisti (Dental)**: ~84 pages, HBV/HCV/HIV protocols

---

## Complementary Documents (5 documents)

### PEE - Piano Emergenze (Azienda, ~28 pages)
| Section | Static/Dynamic | Automation |
|---------|----------------|------------|
| Emergency Procedures A-E | 80% STATIC | Standard procedures per event type (fire, earthquake, flood) |
| First Aid | STATIC | Detailed protocol |
| Emergency Numbers | SEMI-DYNAMIC | Local numbers |
| Environment Risk Classes | DYNAMIC | From fire risk assessment |
| Emergency Teams | DYNAMIC | From personnel roles |

### PEE - Piano Emergenze (Comune/Evento, ~40 pages)
Same structure adapted for public events. Volunteers instead of employees. Custom route/environment description. Pre-opening checklist. Additional RCP procedures.

### HACCP Manuale (~90 pages + 16 forms)
| Section | Static/Dynamic | Automation |
|---------|----------------|------------|
| 25+ SOP Sections | 85% STATIC | Standard operating procedures per food activity type |
| Blast Chiller Procedures | STATIC | 8 food types with specific protocols |
| CCP Analysis | SEMI-DYNAMIC | Customized per specific food activity. AI assistance possible |
| 16 Self-Check Forms | 90% STATIC | Fillable templates. Company name only dynamic field |

### DUVRI (~45 pages)
| Section | Static/Dynamic | Automation |
|---------|----------------|------------|
| Principal Company Data | DYNAMIC | Auto-populated from DVR |
| Contractor Data | DYNAMIC | Entered manually per contract |
| Interference Analysis | DYNAMIC | Per equipment type. Requires specific input |
| Schedule (Cronoprogramma) | DYNAMIC | Manual input |
| Safety Costs | DYNAMIC | Not subject to rebate |

### POS (~110 pages, 81 tables) - Most Complex
| Section | Static/Dynamic | Automation |
|---------|----------------|------------|
| Company Data | DYNAMIC | From DVR master data |
| Job Description Matrix | DYNAMIC | Detailed per role per phase |
| Work Phases (8 typical) | 50% DYNAMIC | Per phase: description, risks, NIOSH, noise, vibration |
| Risk Assessment per Phase | DYNAMIC | I = 2*D + P per risk per phase |
| Equipment per Phase | DYNAMIC | Listed with requirements |
| PPE per Phase | DYNAMIC | Based on phase risks |
| Emergency Procedures | SEMI-DYNAMIC | Site-specific |

---

*© 2026 Niuexa. Confidential — prepared for N2O SRL.*
