"""DUVRI interference rules engine (US-4.6).

Maps each contractor equipment / activity type to the typical interferenze
that arise on a shared workplace and the canonical prevention/protection
measures Italian safety consultants use to manage them. Rules are keyed by
contractor activity so the same equipment can fire multiple rules.

Format:
    rule_id (str, stable)         — used as the storage key for accept/reject
    contractor_eq                 — the activity / equipment label that fires
    titolo (str)                  — short Italian title for UI
    rischio (str)                 — one-sentence interference description
    misure (str)                  — prevention/protection narrative
    dpi (str | None)              — required PPE if applicable
    riferimento (str)             — legal/normative source

This is a starter catalog (~22 rules covering the common Italian DUVRI
scenarios). Rules can be extended by adding rows to ``_RULES`` below; no
schema or endpoint change is needed.
"""

from __future__ import annotations

from typing import TypedDict


class InterferenceRule(TypedDict):
    rule_id: str
    contractor_eq: str
    titolo: str
    rischio: str
    misure: str
    dpi: str | None
    riferimento: str


CONTRACTOR_EQUIPMENT_TYPES: list[str] = [
    "muletto",
    "transpallet_elettrico",
    "ponteggio",
    "piattaforma_aerea",
    "gru",
    "saldatrice",
    "fiamma_libera",
    "prodotti_chimici",
    "pulizie_pavimenti",
    "macchinari_rumorosi",
    "attrezzature_elettriche_portatili",
    "veicoli_trasporto",
    "scavo_movimento_terra",
    "lavori_in_quota",
    "demolizioni",
]


_RULES: list[InterferenceRule] = [
    # --- Movimentazione interna ---
    {
        "rule_id": "muletto_pedoni",
        "contractor_eq": "muletto",
        "titolo": "Investimento pedoni da carrello elevatore",
        "rischio": (
            "Movimento di muletti nelle aree con presenza di personale del "
            "committente: rischio investimento e urto contro persone."
        ),
        "misure": (
            "Delimitare i percorsi del muletto con segnaletica orizzontale e "
            "verticale; vietare il transito pedonale nelle aree di manovra; "
            "concordare orari di movimentazione fuori dalle fasce di maggiore "
            "presenza; muletto sempre con segnalatore acustico e luce lampeggiante."
        ),
        "dpi": "Gilet ad alta visibilita per il personale interferito",
        "riferimento": "D.Lgs. 81/2008 art. 26, all. IV punto 1.4",
    },
    {
        "rule_id": "transpallet_pedoni",
        "contractor_eq": "transpallet_elettrico",
        "titolo": "Urto da transpallet elettrico",
        "rischio": (
            "Spostamento merci con transpallet elettrico in corridoi e "
            "magazzini condivisi: rischio urto contro persone."
        ),
        "misure": (
            "Velocita massima 6 km/h; segnalatore acustico in retromarcia; "
            "concordare percorsi e segnalare gli spostamenti con anticipo."
        ),
        "dpi": "Calzature antinfortunistiche, gilet alta visibilita",
        "riferimento": "D.Lgs. 81/2008 art. 26",
    },
    # --- Lavori in quota ---
    {
        "rule_id": "ponteggio_caduta_oggetti",
        "contractor_eq": "ponteggio",
        "titolo": "Caduta di materiali da ponteggio",
        "rischio": (
            "Allestimento e utilizzo di ponteggi al di sopra di aree con "
            "attivita lavorative del committente: rischio caduta materiali e "
            "attrezzi sulle persone sottostanti."
        ),
        "misure": (
            "Allestire mantovane parasassi e teli di contenimento; interdire "
            "l'area sottostante con barriere e cartellonistica; programmare i "
            "lavori in quota fuori orario di lavoro del committente quando "
            "possibile."
        ),
        "dpi": "Casco di protezione obbligatorio in tutta l'area di influenza",
        "riferimento": "D.Lgs. 81/2008 titolo IV capo II, D.M. 02/09/2021",
    },
    {
        "rule_id": "piattaforma_aerea_passaggio",
        "contractor_eq": "piattaforma_aerea",
        "titolo": "Interferenza piattaforma aerea con percorsi committente",
        "rischio": (
            "Operativita di PLE in aree adiacenti a percorsi pedonali e "
            "veicolari del committente."
        ),
        "misure": (
            "Delimitare l'area di lavoro con cordoli o transenne; presenza di "
            "addetto a terra (manovratore di emergenza); divieto di sosta "
            "sotto la piattaforma."
        ),
        "dpi": "Imbragature per gli operatori PLE; casco in area di influenza",
        "riferimento": "D.Lgs. 81/2008 art. 71-73, all. VI",
    },
    {
        "rule_id": "lavori_quota_caduta_dall_alto",
        "contractor_eq": "lavori_in_quota",
        "titolo": "Caduta dall'alto durante lavorazioni in quota",
        "rischio": (
            "Lavori oltre 2 metri di altezza in ambienti del committente: "
            "rischio caduta dell'operatore e di materiali sulle persone "
            "sottostanti."
        ),
        "misure": (
            "Predisporre linee vita o sistemi anticaduta certificati; "
            "delimitare l'area sottostante; vietare il passaggio durante le "
            "lavorazioni; allegare al DUVRI il PIMUS quando applicabile."
        ),
        "dpi": "Imbracatura anticaduta + cordino + assorbitore di energia, casco",
        "riferimento": "D.Lgs. 81/2008 titolo IV, D.M. 22/07/2014",
    },
    # --- Sollevamento ---
    {
        "rule_id": "gru_carichi_sospesi",
        "contractor_eq": "gru",
        "titolo": "Caduta carichi sospesi",
        "rischio": (
            "Sollevamento di carichi sopra aree frequentate dal personale del "
            "committente."
        ),
        "misure": (
            "Interdire totalmente l'area di tiro durante le manovre; presenza "
            "di moviere qualificato; segnalazione acustica e luminosa; "
            "verifica funi e accessori prima di ogni uso."
        ),
        "dpi": "Casco obbligatorio in tutta l'area di influenza",
        "riferimento": "D.Lgs. 81/2008 art. 71, all. VII",
    },
    # --- Lavori a caldo / fiamma libera ---
    {
        "rule_id": "saldatura_incendio",
        "contractor_eq": "saldatrice",
        "titolo": "Innesco di incendio da saldatura",
        "rischio": (
            "Saldatura ad arco o a gas in presenza di materiali infiammabili "
            "del committente o di sostanze combustibili adiacenti."
        ),
        "misure": (
            "Permesso di lavoro a caldo (hot work permit) firmato dal RSPP "
            "del committente; rimozione preventiva di materiali infiammabili "
            "in raggio 10 m; estintore portatile a portata di mano; sorveglianza "
            "antincendio per 30 minuti dopo fine lavori."
        ),
        "dpi": "Maschera saldatura, guanti cuoio, schermo cuoio, scarpe isolanti",
        "riferimento": "D.M. 02/09/2021, D.Lgs. 81/2008 all. IV punto 4",
    },
    {
        "rule_id": "fiamma_libera_atex",
        "contractor_eq": "fiamma_libera",
        "titolo": "Esplosione in atmosfera potenzialmente esplosiva",
        "rischio": (
            "Uso di fiamme libere in zone con atmosfere potenzialmente "
            "esplosive (ATEX) o vicinanza a serbatoi/condotte di gas e "
            "solventi del committente."
        ),
        "misure": (
            "Verificare classificazione ATEX dei locali; permesso di lavoro a "
            "caldo specifico ATEX; bonifica preliminare con misurazione "
            "esplosimetrica; ventilazione forzata; sorveglianza continua."
        ),
        "dpi": "Indumenti antistatici, calzature antistatiche, maschera filtrante",
        "riferimento": "D.Lgs. 81/2008 titolo XI, D.M. 02/09/2021",
    },
    # --- Sostanze pericolose ---
    {
        "rule_id": "chimici_esposizione",
        "contractor_eq": "prodotti_chimici",
        "titolo": "Esposizione del personale committente a sostanze chimiche",
        "rischio": (
            "Utilizzo di prodotti chimici (pulizie, manutenzioni, vernici) "
            "che possono interferire con il personale del committente "
            "operante nelle vicinanze."
        ),
        "misure": (
            "Fornire al committente le SDS (Schede Dati Sicurezza) prima "
            "dell'inizio attivita; aerazione forzata o naturale; programmare "
            "interventi fuori orario di lavoro; segnalare i locali interessati."
        ),
        "dpi": "Maschera filtrante (in base SDS), guanti chimici, occhiali",
        "riferimento": "D.Lgs. 81/2008 titolo IX, Reg. CE 1907/2006 (REACH)",
    },
    # --- Pulizie / scivolamento ---
    {
        "rule_id": "pulizie_scivolamento",
        "contractor_eq": "pulizie_pavimenti",
        "titolo": "Scivolamento su pavimenti bagnati",
        "rischio": (
            "Pulizia pavimenti durante orari di attivita del committente: "
            "rischio scivolamento del personale interferito."
        ),
        "misure": (
            "Cartelli mobili 'Attenzione pavimento bagnato' bilingue; "
            "delimitare l'area pulita con coni segnaletici; programmare le "
            "pulizie a fine turno o nelle pause; usare detergenti antiscivolo."
        ),
        "dpi": "Calzature antiscivolo per gli operatori",
        "riferimento": "D.Lgs. 81/2008 art. 26, all. IV punto 1.3",
    },
    # --- Rumore / vibrazioni ---
    {
        "rule_id": "rumore_committente",
        "contractor_eq": "macchinari_rumorosi",
        "titolo": "Esposizione a rumore del personale committente",
        "rischio": (
            "Uso di macchinari rumorosi (martelli demolitori, frese, "
            "compressori) che superano LEX,8h 80 dBA per il personale del "
            "committente nelle vicinanze."
        ),
        "misure": (
            "Programmare le lavorazioni rumorose fuori orario; delimitare "
            "l'area di influenza acustica; fornire DPI udito al personale "
            "interferito; valutazione fonometrica preventiva quando dovuta."
        ),
        "dpi": "Cuffie/inserti auricolari (SNR adeguato) per personale interferito",
        "riferimento": "D.Lgs. 81/2008 titolo VIII capo II",
    },
    # --- Elettrico ---
    {
        "rule_id": "elettrico_folgorazione",
        "contractor_eq": "attrezzature_elettriche_portatili",
        "titolo": "Folgorazione da attrezzature elettriche portatili",
        "rischio": (
            "Uso di attrezzature elettriche portatili in ambienti del "
            "committente con possibile contatto accidentale o sovraccarichi "
            "su impianti condivisi."
        ),
        "misure": (
            "Verifica della conformita CE e della marcatura IMQ; uso di "
            "interruttori differenziali (Idn ≤ 30 mA); divieto di sovraccarico "
            "delle prese del committente; ispezione visiva di cavi e spine "
            "prima dell'uso."
        ),
        "dpi": "Calzature isolanti, guanti dielettrici per interventi su quadri",
        "riferimento": "D.Lgs. 81/2008 titolo III capo III, CEI 64-8",
    },
    # --- Veicoli ---
    {
        "rule_id": "veicoli_traffico_interno",
        "contractor_eq": "veicoli_trasporto",
        "titolo": "Interferenza veicoli su percorsi interni",
        "rischio": (
            "Carico/scarico merci con autocarri o furgoni nei piazzali del "
            "committente: rischio investimento, urto contro strutture e "
            "personale a piedi."
        ),
        "misure": (
            "Concordare orari di accesso e percorsi interni; presenza di "
            "operatore a terra durante le manovre; limite di velocita 10 km/h "
            "in piazzale; segnalazione acustica in retromarcia."
        ),
        "dpi": "Gilet ad alta visibilita per autista + operatore a terra",
        "riferimento": "D.Lgs. 81/2008 art. 26, codice della strada",
    },
    # --- Scavi / movimento terra ---
    {
        "rule_id": "scavo_caduta_persone",
        "contractor_eq": "scavo_movimento_terra",
        "titolo": "Caduta di persone in scavi e fronti instabili",
        "rischio": (
            "Esecuzione di scavi e movimento terra in aree del committente: "
            "rischio caduta di personale interferito nello scavo o cedimento "
            "del fronte di scavo."
        ),
        "misure": (
            "Recintare gli scavi su tutto il perimetro con rete arancione "
            "alta minimo 1,2 m; segnalazione luminosa notturna; armatura del "
            "fronte se profondita > 1,5 m; vietare deposito di materiali "
            "entro 2 m dal ciglio."
        ),
        "dpi": "Casco e calzature antinfortunistiche per operatori e interferiti",
        "riferimento": "D.Lgs. 81/2008 titolo IV capo II, all. XVIII",
    },
    # --- Demolizioni ---
    {
        "rule_id": "demolizione_polveri_macerie",
        "contractor_eq": "demolizioni",
        "titolo": "Polveri e macerie da demolizione",
        "rischio": (
            "Demolizioni totali o parziali in ambienti del committente: "
            "diffusione di polveri (potenzialmente contenenti silice o "
            "amianto) e proiezione di macerie."
        ),
        "misure": (
            "Verifica preventiva presenza amianto (D.M. 06/09/1994); confinamento "
            "dell'area con teli antipolvere; abbattimento polveri con "
            "nebulizzatori; programmazione fuori orario; interdizione totale "
            "dell'area."
        ),
        "dpi": "Maschera FFP3 (o con filtro P3 se amianto), tuta monouso, occhiali",
        "riferimento": "D.Lgs. 81/2008 titolo IX capo III, D.M. 06/09/1994",
    },
]


def list_equipment_types() -> list[str]:
    """Return the canonical contractor equipment types (UI selector source)."""
    return list(CONTRACTOR_EQUIPMENT_TYPES)


def evaluate_rules(contractor_equipment: list[str]) -> list[InterferenceRule]:
    """Return all rules that fire for any of the given contractor equipment.

    Order is preserved from the rule definition so the operator sees a stable
    list across re-evaluations. Duplicate rules across equipment overlap
    are suppressed.
    """
    if not contractor_equipment:
        return []
    seen: set[str] = set()
    matches: list[InterferenceRule] = []
    contractor_set = {eq.strip().lower() for eq in contractor_equipment if eq}
    for rule in _RULES:
        if rule["contractor_eq"] in contractor_set and rule["rule_id"] not in seen:
            seen.add(rule["rule_id"])
            matches.append(rule)
    return matches


def get_rule(rule_id: str) -> InterferenceRule | None:
    """Lookup a rule by its stable ID (used when persisting decisions)."""
    for rule in _RULES:
        if rule["rule_id"] == rule_id:
            return rule
    return None


def rule_count() -> int:
    """Number of rules in the catalog (test/monitoring)."""
    return len(_RULES)
