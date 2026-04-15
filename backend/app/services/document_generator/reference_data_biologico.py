"""Sector-specific knowledge bases for Rischio Biologico generators.

Each entry: list of {nome, gruppo, via, patologia}.
Groups per D.Lgs. 81/2008 Allegato XLVI (agenti biologici gruppi 1..4).
"""

ALIMENTARE_AGENTI = [
    {"nome": "Salmonella spp.", "gruppo": "2", "via": "Ingestione", "patologia": "Salmonellosi, tossinfezione alimentare"},
    {"nome": "Listeria monocytogenes", "gruppo": "2", "via": "Ingestione", "patologia": "Listeriosi, gastroenterite"},
    {"nome": "Escherichia coli (STEC/EHEC)", "gruppo": "2", "via": "Ingestione", "patologia": "Gastroenterite emorragica, SEU"},
    {"nome": "Staphylococcus aureus", "gruppo": "2", "via": "Ingestione/contatto", "patologia": "Tossinfezione alimentare"},
    {"nome": "Clostridium botulinum", "gruppo": "2", "via": "Ingestione", "patologia": "Botulismo"},
    {"nome": "Clostridium perfringens", "gruppo": "2", "via": "Ingestione", "patologia": "Tossinfezione gastroenterica"},
    {"nome": "Norovirus", "gruppo": "2", "via": "Oro-fecale", "patologia": "Gastroenterite acuta virale"},
    {"nome": "Epatite A", "gruppo": "2", "via": "Oro-fecale", "patologia": "Epatite acuta"},
    {"nome": "Campylobacter jejuni", "gruppo": "2", "via": "Ingestione", "patologia": "Enterite"},
]
ALIMENTARE_MISURE = [
    "Catena del freddo: prodotti freschi a 0-4 C, surgelati a -18 C",
    "Cottura a cuore >= 75 C per minimo 15 secondi (carne, pollame, pesce)",
    "Evitare contaminazioni crociate: attrezzature e superfici dedicate per prodotti crudi/cotti",
    "Sanificazione giornaliera superfici di lavoro con detergente + disinfettante",
    "Lavaggio frequente delle mani con acqua e sapone; disinfezione in situazioni critiche",
    "Registrazione temperature secondo schede SA-03 (frigo) e SA-04 (congelatore)",
    "Verifica scadenze e rotazione FIFO dei prodotti",
]
ALIMENTARE_DPI = [
    "Camice/divisa dedicata, cambio quotidiano",
    "Copricapo che contenga i capelli",
    "Guanti monouso per manipolazione alimenti ready-to-eat",
    "Mascherina in presenza di raffreddori o sintomi respiratori",
    "Calzature antiscivolo chiuse",
]
ALIMENTARE_PROTOCOLLO = (
    "Sorveglianza sanitaria ai sensi del Reg. CE 852/2004: visita medica pre-assunzione, "
    "esami coprocolturali se sintomi gastroenterici, vaccinazione antiepatite A raccomandata "
    "per gli addetti alla preparazione/somministrazione. Sospensione dal servizio alimentare "
    "in caso di sintomatologia gastroenterica fino a guarigione certificata."
)

ASILO_AGENTI = [
    {"nome": "Virus sinciziale respiratorio (VRS)", "gruppo": "2", "via": "Aerogena/contatto", "patologia": "Bronchiolite, polmonite"},
    {"nome": "Rotavirus", "gruppo": "2", "via": "Oro-fecale", "patologia": "Gastroenterite infantile"},
    {"nome": "Virus varicella-zoster", "gruppo": "2", "via": "Aerogena/contatto", "patologia": "Varicella"},
    {"nome": "Virus parotite", "gruppo": "2", "via": "Aerogena/contatto", "patologia": "Parotite epidemica"},
    {"nome": "Virus morbillo", "gruppo": "2", "via": "Aerogena", "patologia": "Morbillo"},
    {"nome": "Virus rosolia", "gruppo": "2", "via": "Aerogena", "patologia": "Rosolia (rischio per gestanti)"},
    {"nome": "Streptococcus pyogenes", "gruppo": "2", "via": "Aerogena/contatto", "patologia": "Faringite, scarlattina"},
    {"nome": "Pediculus humanus capitis", "gruppo": "1", "via": "Contatto diretto", "patologia": "Pediculosi"},
    {"nome": "Sarcoptes scabiei", "gruppo": "2", "via": "Contatto diretto", "patologia": "Scabbia"},
    {"nome": "Parvovirus B19", "gruppo": "2", "via": "Aerogena", "patologia": "Megaloeritema (rischio per gestanti)"},
]
ASILO_MISURE = [
    "Aerazione frequente degli ambienti (almeno 4 volte/giorno)",
    "Sanificazione quotidiana di giochi, superfici e servizi igienici",
    "Lavaggio frequente delle mani per educatori e bambini",
    "Isolamento dei bambini con sintomi infettivi fino a idoneita al rientro",
    "Gestione biancheria sporca in contenitori dedicati",
    "Piano vaccinale del personale aggiornato",
    "Segnalazione casi di malattie infettive all'ASL",
]
ASILO_DPI = [
    "Guanti monouso per cambio pannolino e igiene",
    "Grembiule monouso impermeabile per sporco biologico",
    "Mascherina FFP2 in presenza di sintomi respiratori propri o dei bambini",
    "Kit di primo soccorso con disinfettante e garze sterili",
]
ASILO_PROTOCOLLO = (
    "Sorveglianza sanitaria preventiva del personale con: verifica del profilo vaccinale "
    "(morbillo-parotite-rosolia, varicella, pertosse), tampone faringeo in caso di faringite "
    "febbrile, test di gravidanza e mansione alternativa per gestanti non immuni a rosolia/varicella/CMV. "
    "Formazione specifica sulle malattie infettive infantili e sul lavaggio delle mani."
)

DENTISTI_AGENTI = [
    {"nome": "Virus dell'epatite B (HBV)", "gruppo": "3**", "via": "Parenterale/mucose", "patologia": "Epatite cronica B"},
    {"nome": "Virus dell'epatite C (HCV)", "gruppo": "3**", "via": "Parenterale", "patologia": "Epatite cronica C"},
    {"nome": "HIV", "gruppo": "3**", "via": "Parenterale/mucose", "patologia": "AIDS"},
    {"nome": "Mycobacterium tuberculosis", "gruppo": "3", "via": "Aerogena", "patologia": "Tubercolosi"},
    {"nome": "Streptococcus mutans / Treponema denticola", "gruppo": "2", "via": "Contatto/aerosol", "patologia": "Carie, parodontite"},
    {"nome": "Herpes simplex virus (HSV-1)", "gruppo": "2", "via": "Contatto/aerosol", "patologia": "Herpes labiale e erpete digitale"},
    {"nome": "Virus dell'influenza", "gruppo": "2", "via": "Aerogena", "patologia": "Influenza stagionale"},
    {"nome": "SARS-CoV-2", "gruppo": "3", "via": "Aerogena", "patologia": "COVID-19"},
]
DENTISTI_MISURE = [
    "Sterilizzazione strumenti riutilizzabili in autoclave classe B a 134 C per 3-4 minuti",
    "Uso di strumenti monouso dove possibile (anestesia, frese, tip aspiratori)",
    "Disinfezione superfici tra pazienti con disinfettanti di livello intermedio/alto",
    "Impiego di dighe di gomma per isolare il campo operatorio e ridurre aerosol",
    "Aspirazione ad alto volume per abbattere aerosol contaminati",
    "Smaltimento taglienti in appositi contenitori rigidi (D.Lgs. 152/2006)",
    "Profilassi post-esposizione in caso di incidente percutaneo (protocollo HBV/HCV/HIV)",
]
DENTISTI_DPI = [
    "Mascherina chirurgica o FFP2 (FFP3 in caso di manovre generanti aerosol su pazienti infetti)",
    "Occhiali protettivi o visiera trasparente",
    "Guanti monouso cambiati tra un paziente e l'altro",
    "Camice monouso impermeabile",
    "Copricapo",
]
DENTISTI_PROTOCOLLO = (
    "Sorveglianza sanitaria con periodicita annuale: profilo sierologico HBV/HCV/HIV, Quantiferon "
    "per TBC, verifica vaccinazioni (epatite B obbligatoria, antinfluenzale raccomandata, "
    "tetano). Registro esposizioni accidentali. Protocollo post-esposizione attivato entro 1 ora "
    "dall'evento con test di base, eventuale profilassi ARV e monitoraggio a 3/6/12 mesi."
)


# ---------------------------------------------------------------------------
# Sector checklists (US-3.15, Wave 1 frontends)
# ---------------------------------------------------------------------------
# Each item drives the live risk classification in the operator UI. The
# operator answers each with SI / NO / NA. NO answers count against the
# sector, weighted by criticita. NA means the item is not applicable to the
# current client (e.g. no cold chain for a bakery) and is excluded from the
# denominator.
#
# Thresholds (ratio of weighted-NO to weighted-max):
#   ratio >= 0.40  -> ALTO
#   ratio >= 0.15  -> MEDIO
#   otherwise      -> BASSO
#
# Reference: D.Lgs. 81/2008 Titolo X, Reg. CE 852/2004 (alimentare),
# Linee guida ISS / ISPESL per asili nido e studi odontoiatrici.

CRITICITA_WEIGHTS: dict[str, int] = {"alta": 3, "media": 2, "bassa": 1}


ALIMENTARE_CHECKLIST = [
    {"id": "AL.01", "descrizione": "Procedure HACCP documentate e aggiornate", "criticita": "alta"},
    {"id": "AL.02", "descrizione": "Responsabile HACCP formalmente nominato", "criticita": "media"},
    {"id": "AL.03", "descrizione": "Formazione HACCP del personale valida (entro 3 anni)", "criticita": "alta"},
    {"id": "AL.04", "descrizione": "Separazione fisica tra prodotti crudi e cotti (attrezzature/superfici)", "criticita": "alta"},
    {"id": "AL.05", "descrizione": "Catena del freddo garantita (frigo 0-4 C, surgelati -18 C) con registrazione temperature", "criticita": "alta"},
    {"id": "AL.06", "descrizione": "Sanificazione quotidiana delle superfici con detergente + disinfettante", "criticita": "media"},
    {"id": "AL.07", "descrizione": "Lavaggio mani con dispenser dedicato nelle zone di preparazione", "criticita": "media"},
    {"id": "AL.08", "descrizione": "Lotta integrata a infestanti (derattizzazione, disinfestazione) con contratto attivo", "criticita": "media"},
    {"id": "AL.09", "descrizione": "Rotazione FIFO dei prodotti e controllo scadenze", "criticita": "bassa"},
    {"id": "AL.10", "descrizione": "DPI monouso disponibili (guanti, copricapo) e sostituiti ad ogni turno", "criticita": "media"},
    {"id": "AL.11", "descrizione": "Sospensione dal servizio alimentare del personale con sintomi gastroenterici", "criticita": "alta"},
    {"id": "AL.12", "descrizione": "Vaccinazione anti-epatite A raccomandata e offerta al personale", "criticita": "bassa"},
]


ASILO_CHECKLIST = [
    {"id": "AS.01", "descrizione": "Verifica profilo vaccinale del personale (MPR, varicella, pertosse)", "criticita": "alta"},
    {"id": "AS.02", "descrizione": "Valutazione specifica per gestanti non immuni a rosolia/varicella/CMV", "criticita": "alta"},
    {"id": "AS.03", "descrizione": "Protocollo di isolamento dei bambini con sintomi infettivi", "criticita": "alta"},
    {"id": "AS.04", "descrizione": "Aerazione ambienti almeno 4 volte al giorno", "criticita": "media"},
    {"id": "AS.05", "descrizione": "Sanificazione quotidiana di giochi, superfici e servizi igienici", "criticita": "media"},
    {"id": "AS.06", "descrizione": "Procedure di lavaggio mani per educatori e bambini", "criticita": "media"},
    {"id": "AS.07", "descrizione": "Guanti monouso e grembiule per cambio pannolino", "criticita": "alta"},
    {"id": "AS.08", "descrizione": "Contenitori dedicati per biancheria sporca e rifiuti potenzialmente infetti", "criticita": "media"},
    {"id": "AS.09", "descrizione": "Formazione annuale del personale su malattie infettive infantili", "criticita": "media"},
    {"id": "AS.10", "descrizione": "Procedura di segnalazione casi infettivi all'ASL territoriale", "criticita": "bassa"},
    {"id": "AS.11", "descrizione": "Kit di primo soccorso con disinfettante e garze sterili sempre disponibile", "criticita": "bassa"},
]


DENTISTI_CHECKLIST = [
    {"id": "DE.01", "descrizione": "Vaccinazione anti-epatite B obbligatoria verificata per tutto il personale clinico", "criticita": "alta"},
    {"id": "DE.02", "descrizione": "Sterilizzazione strumenti riutilizzabili in autoclave classe B con test biologici periodici", "criticita": "alta"},
    {"id": "DE.03", "descrizione": "Uso di dighe di gomma per isolamento del campo operatorio", "criticita": "media"},
    {"id": "DE.04", "descrizione": "Aspirazione ad alto volume per abbattere aerosol", "criticita": "alta"},
    {"id": "DE.05", "descrizione": "Smaltimento taglienti in contenitori rigidi a norma (D.Lgs. 152/2006)", "criticita": "alta"},
    {"id": "DE.06", "descrizione": "DPI completi (mascherina FFP2/FFP3, visiera, guanti, camice) per ogni paziente", "criticita": "alta"},
    {"id": "DE.07", "descrizione": "Protocollo post-esposizione percutanea (HBV/HCV/HIV) documentato e attivabile entro 1 ora", "criticita": "alta"},
    {"id": "DE.08", "descrizione": "Registro esposizioni accidentali aggiornato", "criticita": "media"},
    {"id": "DE.09", "descrizione": "Sorveglianza sanitaria annuale con profilo sierologico HBV/HCV/HIV + Quantiferon TBC", "criticita": "media"},
    {"id": "DE.10", "descrizione": "Disinfezione superfici tra pazienti con prodotti di livello intermedio/alto", "criticita": "media"},
    {"id": "DE.11", "descrizione": "Formazione periodica su precauzioni standard e rischio biologico", "criticita": "bassa"},
    {"id": "DE.12", "descrizione": "Separazione delle aree sporche/pulite nello sterilizzatorio", "criticita": "media"},
]


def get_checklist(settore: str) -> list[dict]:
    """Return the checklist catalog for the given settore.

    Raises ValueError if settore is not one of alimentare / asilo / dentisti.
    """
    key = (settore or "").strip().lower()
    if key == "alimentare":
        return list(ALIMENTARE_CHECKLIST)
    if key == "asilo":
        return list(ASILO_CHECKLIST)
    if key == "dentisti":
        return list(DENTISTI_CHECKLIST)
    raise ValueError(f"Settore non riconosciuto: {settore!r}")


def classify_biologico(settore: str, risposte: list[dict]) -> dict:
    """Classify a Biologico assessment from sector checklist responses.

    Input:
      - settore: "alimentare" | "asilo" | "dentisti"
      - risposte: list of {"id": str, "risposta": "SI" | "NO" | "NA"}

    Algorithm:
      - For each checklist item, if the operator answered NO, add its
        criticita weight (alta=3, media=2, bassa=1) to `no_weight`.
      - If the answer is NA, exclude the item from `max_weight` (denominator).
      - If the answer is SI or missing, include it in `max_weight` but not
        in `no_weight`.
      - Compute ratio = no_weight / max_weight (0.0 if denominator is 0).
      - ratio >= 0.40 -> ALTO
        ratio >= 0.15 -> MEDIO
        otherwise     -> BASSO

    Returns {no_weight, max_weight, ratio, livello, unanswered}.
    """
    catalog = get_checklist(settore)
    index = {item["id"]: item for item in catalog}
    risposte_by_id: dict[str, str] = {}
    for r in risposte or []:
        rid = r.get("id")
        risp = (r.get("risposta") or "").upper()
        if rid and risp in {"SI", "NO", "NA"}:
            risposte_by_id[rid] = risp

    no_weight = 0
    max_weight = 0
    unanswered: list[str] = []
    for item in catalog:
        weight = CRITICITA_WEIGHTS[item["criticita"]]
        answer = risposte_by_id.get(item["id"])
        if answer is None:
            unanswered.append(item["id"])
            max_weight += weight
            continue
        if answer == "NA":
            # Not applicable -> excluded from denominator.
            continue
        max_weight += weight
        if answer == "NO":
            no_weight += weight

    ratio = (no_weight / max_weight) if max_weight else 0.0
    if ratio >= 0.40:
        livello = "ALTO"
    elif ratio >= 0.15:
        livello = "MEDIO"
    else:
        livello = "BASSO"

    return {
        "settore": (settore or "").lower(),
        "no_weight": no_weight,
        "max_weight": max_weight,
        "ratio": round(ratio, 4),
        "livello": livello,
        "unanswered": unanswered,
    }
