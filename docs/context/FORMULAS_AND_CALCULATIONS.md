> **NIUEXA** | AI-Powered Business Automation  
> *N2O DVR Automation Platform — Project Documentation*  
> Version 1.0 | April 2026 | Gregor Maric  
> Confidential — Niuexa & N2O SRL

---

# Formulas & Calculations

## 1. DVR Risk Index (DVR Master + POS)

**Standard**: D.Lgs. 81/2008
**Formula**: `I = 2*D + P`

> **IMPORTANT**: This is NOT the classic P x D formula. Damage (D) is weighted double relative to Probability (P).

### Input
- P (Probabilita): 1-4 (1=Bassa, 2=Medio-Bassa, 3=Medio-Alta, 4=Elevata)
- D (Danno): 1-4 (1=Trascurabile, 2=Modesta, 3=Notevole, 4=Ingente)

### Output
- I (Indice): 3-12

### Risk Levels
| I Range | Level | Italian |
|---------|-------|---------|
| 3-4 | Acceptable | ACCETTABILE |
| 5-6 | Moderate | MODESTO |
| 7-8 | Serious | GRAVE |
| 9-12 | Very Serious | GRAVISSIMO |

---

## 2. NIOSH Lifting Equation (Allegato MMC)

**Standard**: NIOSH (National Institute for Occupational Safety and Health) / UNI EN ISO 11228-1:2022

### Step 1: Recommended Weight Limit (PLR)

**Formula**: `PLR = CP x A x B x C x D x E x F`

| Factor | Name | Calculation | Notes |
|--------|------|-------------|-------|
| CP | Weight Constant (kg) | M>18: 25kg, F>18: 15kg | From sex and age |
| A | Height Factor | Lookup from lifting height (cm) | Standard anthropometric table |
| B | Vertical Displacement | Lookup from displacement (cm) | |
| C | Horizontal Distance | Lookup from distance (cm) | |
| D | Asymmetry Factor | Lookup from angle (degrees) | |
| E | Grip Quality | Buona=1.0, Sufficiente=0.95, Scarsa=0.9 | |
| F | Frequency Factor | Lookup table (17 rows) | Based on actions/min and duration |

### Step 2: Risk Index (IR)

**Formula**: `IR = P / PLR`

Where P = actual weight lifted (kg)

### Classification
| IR Range | Zone | Action |
|----------|------|--------|
| <= 0.75 | GREEN (Verde) | OK - No action needed |
| 0.75 - 1.0 | YELLOW (Giallo) | Attention - Monitor |
| > 1.0 | RED (Rosso) | Intervention required |

---

## 3. VDT Exposure Classification (Allegato VDT)

**Standard**: D.Lgs. 81/2008, Titolo VII

**Formula**: `Exposed = (weekly_hours >= 20)`

### Output
- Exposed (Esposto): SI -> mandatory eye exam (sorveglianza sanitaria oculistica)
- Not Exposed: NO -> no obligation

Trivial threshold. Per worker per VDT workstation.

---

## 4. Work-Related Stress Assessment (Allegato Stress)

**Standard**: INAIL Methodology

### Structure: 3 Areas with ~50 indicators

**Area A** - Company Indicators (10 indicators)
- Scoring: 0, 1, or 4 per indicator
- Range: 0-40
- Thresholds: 0-10=Low, 11-20=Medium, 21-40=High

**Area B** - Work Context (30 indicators)
- Scoring: SI=0, NO=1
- Range: 0-26 (some indicators grouped)
- Thresholds: 0-8=Low, 9-17=Medium, 18-26=High

**Area C** - Work Content (36 indicators)
- Scoring: SI=0, NO=1
- Range: 0-36 (some indicators grouped)
- Thresholds: 0-13=Low, 14-25=Medium, 26-36=High

### Total Score

**Formula**: `Total = Area_A + Area_B + Area_C`

| Total Range | Risk Level |
|-------------|------------|
| 0-17 | LOW (BASSO) |
| 18-34 | MEDIUM (MEDIO) |
| >= 35 | HIGH (ALTO) |

> **Note**: The INAIL published scale shows 67 as the upper bound of the HIGH range. However, the theoretical maximum (40+26+36 = 102) exceeds this. In practice, all scores >= 35 are classified as HIGH per INAIL methodology. The per-area ranges reflect grouped indicator scoring, not raw indicator counts.

**Special rule**: If "Interfaccia casa-lavoro" total = 0, it becomes -1.

---

## 5. Fire Risk Assessment (Allegato Incendio)

**Standard**: D.M. 03/09/2021

### Input (per homogeneous area)
- INF (Infiammabilita / Flammability): 1-3
- SI (Sviluppo Incendio / Fire Development): 1-3
- PI (Propagazione Incendio / Fire Propagation): 1-3

### Formula
`Risk Level = f(INF + SI + PI)`

| Sum | Level |
|-----|-------|
| 3-4 | LOW (Basso) |
| 5-7 | MEDIUM (Medio) |
| 8-9 | HIGH (Elevato) |

---

## 6. Thermal Comfort - PMV/PPD (Allegato Microclima)

**Standard**: UNI EN ISO 7730:2006

### Input (6 parameters)
| Parameter | Symbol | Unit | Example |
|-----------|--------|------|---------|
| Air temperature | Ta | C | 22.5 |
| Mean radiant temperature | Tr | C | 23.0 |
| Air velocity | Va | m/s | 0.1 |
| Relative humidity | Ur | % | 50 |
| Metabolic rate | M | met | 1.2 |
| Clothing insulation | Icl | clo | 1.0 |

### Output
- **PMV** (Predicted Mean Vote): -3 to +3
- **PPD** (Predicted Percentage of Dissatisfied): 5% to 100%

### PMV Scale
| PMV | Sensation | Italian |
|-----|-----------|---------|
| -3 | Cold | Freddo |
| -2 | Cool | Fresco |
| -1 | Slightly cool | Leggermente fresco |
| 0 | Neutral | Neutro (benessere) |
| +1 | Slightly warm | Leggermente caldo |
| +2 | Warm | Caldo |
| +3 | Hot | Molto caldo |

### Comfort Categories (ISO 7730)
| Category | PPD | PMV Range |
|----------|-----|-----------|
| A | < 6% | -0.2 < PMV < +0.2 |
| B | < 10% | -0.5 < PMV < +0.5 |
| C | < 15% | -0.7 < PMV < +0.7 |

### Implementation
- **Python**: `pythermalcomfort` library has PMV/PPD calculation
- **JavaScript**: CBE Thermal Comfort Tool
- The equation is iterative (not closed-form)

---

## 7. Severe Heat Stress - PHS (Allegato Microclima Caldo Severo)

**Standard**: UNI EN ISO 7933:2005

### Thermal Balance Equation
`M - W = Cres + Eres + K + C + R + E + S`

### Input
| Parameter | Description |
|-----------|-------------|
| ta | Air temperature (C) |
| tr | Mean radiant temperature (C) |
| pa | Partial water vapor pressure |
| va | Air velocity (m/s) |
| D | Walking direction angle |
| M | Metabolic rate |
| vw | Walking speed |
| angolo | Posture angle |
| Icl | Clothing insulation |
| Fr | Clothing area factor |
| Ap | Body surface fraction |
| acclimatato | Acclimatized (yes/no) |
| bere_libero | Free water access (yes/no) |

### Output
- Final rectal temperature
- Water loss
- **Dlim** (maximum exposure time) based on 3 criteria

### Implementation
- **Python**: `pythermalcomfort` library includes PHS method
- Most complex calculation in the system
- Different limits for acclimatized vs non-acclimatized workers

---

## Libraries for Implementation

| Library | Language | Covers | URL |
|---------|----------|--------|-----|
| pythermalcomfort | Python | PMV/PPD, PHS, SET, UTCI | PyPI |
| CBE Thermal Comfort | JavaScript | PMV/PPD, SET | GitHub |
| python-docx | Python | .docx generation | PyPI |

---

*© 2026 Niuexa. Confidential — prepared for N2O SRL.*
