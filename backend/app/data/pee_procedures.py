"""Standard emergency procedures (A-E) for the PEE (US-4.2).

Source: D.M. 02/09/2021 "Criteri per la gestione dei luoghi di lavoro in
esercizio ed in emergenza", D.Lgs. 81/2008 art. 46, and common Italian
safety-consultant boilerplate. See LEGISLATION_REFERENCE.md.

Each event type exposes five standard procedures with the canonical letter
prefix operators expect on printed plans:

  A - Rilevamento e allarme
  B - Comunicazione e allerta
  C - Primo intervento / messa in sicurezza
  D - Evacuazione
  E - Cessato allarme e ripristino

The data here is consumed (1) as the default pre-fill when an operator opens
the PEE procedures review screen and (2) as the baseline the "Reset alle
procedure standard" action restores to. Per-client customizations live on
``pee_plans.scenari`` (JSONB) — no migration required.

Two client-driven behaviours live here as well:

* **Tipologia di allarme** — the standard "A" step for *incendio* and
  *evacuazione generale* embeds the alarm type configured on the plan
  (``pee_plans.tipologia_allarme``) via the ``{tipologia_allarme}``
  placeholder. Callers pass the configured value to
  ``get_standard_procedures`` / ``merge_with_overrides``; when nothing is
  configured the sensible default below is used.
* **NUE 112** — per the Numero Unico di Emergenza reform, standard texts
  reference only the NUE 112 (never 113/115/118), and
  ``normalize_emergency_number`` maps legacy national emergency numbers to
  "112" when rendering the emergency-contacts table. Company-internal
  numbers pass through untouched.
"""

import re
from typing import Literal, TypedDict


class Procedura(TypedDict):
    lettera: str
    titolo: str
    testo: str


class EventoEmergenza(TypedDict):
    codice: str
    titolo: str
    procedure: list[Procedura]


EventCode = Literal[
    "incendio",
    "terremoto",
    "allagamento",
    "fuga_gas",
    "evacuazione_generale",
]

EVENT_CODES: list[EventCode] = [
    "incendio",
    "terremoto",
    "allagamento",
    "fuga_gas",
    "evacuazione_generale",
]

PROCEDURE_LETTERS: list[str] = ["A", "B", "C", "D", "E"]

PROCEDURE_TITLES: dict[str, str] = {
    "A": "Rilevamento e allarme",
    "B": "Comunicazione e allerta",
    "C": "Primo intervento / messa in sicurezza",
    "D": "Evacuazione",
    "E": "Cessato allarme e ripristino",
}

# ---------------------------------------------------------------------------
# Tipologia di allarme
# ---------------------------------------------------------------------------

#: Default alarm type prefilled in the plan config and used in generated
#: documents when the operator has not configured one yet.
DEFAULT_TIPOLOGIA_ALLARME = "Sirena"

#: Common alarm types offered as select options in the frontend. The field
#: itself stays free text so "Altro" custom values round-trip unchanged.
TIPOLOGIE_ALLARME: list[str] = [
    "Sirena",
    "Campanella",
    "Avviso a voce",
    "Tromba da stadio",
    "Segnale luminoso",
]

#: Placeholder embedded in standard texts, substituted at render time.
TIPOLOGIA_ALLARME_PLACEHOLDER = "{tipologia_allarme}"


def _resolve_tipologia(tipologia_allarme: str | None) -> str:
    value = (tipologia_allarme or "").strip()
    return value or DEFAULT_TIPOLOGIA_ALLARME


# ---------------------------------------------------------------------------
# NUE 112 normalization
# ---------------------------------------------------------------------------

#: Legacy national emergency numbers that the NUE reform routes through 112.
LEGACY_EMERGENCY_NUMBERS: frozenset[str] = frozenset(
    {"112", "113", "115", "117", "118", "1515", "1530"}
)

NUE_LABEL = "Numero Unico di Emergenza (NUE)"


def normalize_emergency_number(value: str | None) -> str:
    """Render legacy national emergency numbers as the NUE "112".

    Only values composed *entirely* of legacy emergency numbers (e.g.
    "115", "115 / 118") are normalized, so company-internal numbers and
    extensions ("0521 456789", "int. 115") are never mangled.
    """
    raw = (value or "").strip()
    tokens = re.findall(r"\d+", raw)
    if (
        tokens
        and all(t in LEGACY_EMERGENCY_NUMBERS for t in tokens)
        and not re.search(r"[A-Za-z]", raw)
    ):
        return "112"
    return raw


_STANDARD: dict[EventCode, EventoEmergenza] = {
    "incendio": {
        "codice": "incendio",
        "titolo": "Incendio",
        "procedure": [
            {
                "lettera": "A",
                "titolo": PROCEDURE_TITLES["A"],
                "testo": (
                    "Chi scopre il principio di incendio avverte immediatamente il "
                    "coordinatore dell'emergenza e attiva l'allarme antincendio "
                    "previsto dal piano ({tipologia_allarme})."
                ),
            },
            {
                "lettera": "B",
                "titolo": PROCEDURE_TITLES["B"],
                "testo": (
                    "Il coordinatore allerta i Vigili del Fuoco tramite il Numero "
                    "Unico di Emergenza (NUE) 112 indicando luogo, natura "
                    "dell'emergenza e eventuali persone coinvolte. Contestualmente "
                    "attiva la squadra di emergenza interna."
                ),
            },
            {
                "lettera": "C",
                "titolo": PROCEDURE_TITLES["C"],
                "testo": (
                    "Gli addetti antincendio intervengono con estintori portatili "
                    "se il focolaio e' circoscritto e di modesta entita'. In caso "
                    "di propagazione non tentare lo spegnimento: procedere "
                    "all'evacuazione."
                ),
            },
            {
                "lettera": "D",
                "titolo": PROCEDURE_TITLES["D"],
                "testo": (
                    "Tutti i lavoratori seguono la segnaletica UNI EN ISO 7010 "
                    "verso le vie di fuga e raggiungono ordinatamente il punto di "
                    "raccolta. Non utilizzare ascensori. Chiudere porte e "
                    "finestre senza chiave."
                ),
            },
            {
                "lettera": "E",
                "titolo": PROCEDURE_TITLES["E"],
                "testo": (
                    "Il coordinatore, d'intesa con i Vigili del Fuoco, dichiara "
                    "il cessato allarme. Registrare l'evento nel registro "
                    "antincendio e verificare l'agibilita' dei locali prima della "
                    "ripresa attivita'."
                ),
            },
        ],
    },
    "terremoto": {
        "codice": "terremoto",
        "titolo": "Terremoto",
        "procedure": [
            {
                "lettera": "A",
                "titolo": PROCEDURE_TITLES["A"],
                "testo": (
                    "Al percepimento delle prime scosse, i lavoratori mantengono "
                    "la calma e si riparano sotto strutture portanti (tavoli, "
                    "vani porta) o in campo aperto, lontano da vetrate e oggetti "
                    "sospesi."
                ),
            },
            {
                "lettera": "B",
                "titolo": PROCEDURE_TITLES["B"],
                "testo": (
                    "Il coordinatore valuta i danni strutturali visibili e "
                    "contatta il Numero Unico di Emergenza (NUE) 112 se sono "
                    "presenti feriti o crolli. Allerta anche i referenti aziendali."
                ),
            },
            {
                "lettera": "C",
                "titolo": PROCEDURE_TITLES["C"],
                "testo": (
                    "Gli addetti al primo soccorso prestano assistenza ai feriti "
                    "senza spostarli se si sospettano traumi alla colonna. Non "
                    "rimuovere macerie senza indicazioni dei soccorritori."
                ),
            },
            {
                "lettera": "D",
                "titolo": PROCEDURE_TITLES["D"],
                "testo": (
                    "Cessato il sisma, evacuare ordinatamente l'edificio verso "
                    "il punto di raccolta, prestando attenzione a lesioni "
                    "strutturali, caduta di calcinacci e ostacoli. Non rientrare "
                    "per recuperare oggetti."
                ),
            },
            {
                "lettera": "E",
                "titolo": PROCEDURE_TITLES["E"],
                "testo": (
                    "Il coordinatore, dopo il nulla osta di tecnico abilitato o "
                    "Vigili del Fuoco, autorizza il rientro. Registrare l'evento "
                    "e programmare la verifica strutturale dell'edificio."
                ),
            },
        ],
    },
    "allagamento": {
        "codice": "allagamento",
        "titolo": "Allagamento",
        "procedure": [
            {
                "lettera": "A",
                "titolo": PROCEDURE_TITLES["A"],
                "testo": (
                    "Chi rileva una perdita d'acqua significativa o l'ingresso "
                    "di acqua dall'esterno avverte il coordinatore e interrompe, "
                    "se possibile in sicurezza, l'afflusso (chiusura valvole, "
                    "rimozione attrezzature elettriche)."
                ),
            },
            {
                "lettera": "B",
                "titolo": PROCEDURE_TITLES["B"],
                "testo": (
                    "Il coordinatore attiva la squadra di emergenza e, se "
                    "l'allagamento coinvolge impianti elettrici o causa rischio "
                    "statico, allerta i Vigili del Fuoco tramite il Numero Unico "
                    "di Emergenza (NUE) 112."
                ),
            },
            {
                "lettera": "C",
                "titolo": PROCEDURE_TITLES["C"],
                "testo": (
                    "Disalimentare i circuiti elettrici interessati dal quadro "
                    "generale. Mettere in sicurezza sostanze chimiche e materiali "
                    "sensibili all'acqua."
                ),
            },
            {
                "lettera": "D",
                "titolo": PROCEDURE_TITLES["D"],
                "testo": (
                    "Evacuare i locali allagati dirigendosi verso zone sicure e "
                    "asciutte (piani superiori o punto di raccolta esterno). "
                    "Prestare attenzione a cadute e folgorazioni."
                ),
            },
            {
                "lettera": "E",
                "titolo": PROCEDURE_TITLES["E"],
                "testo": (
                    "Dopo il prosciugamento e la verifica degli impianti "
                    "elettrici a cura di personale qualificato, il coordinatore "
                    "autorizza il rientro. Registrare l'evento e programmare il "
                    "ripristino degli impianti."
                ),
            },
        ],
    },
    "fuga_gas": {
        "codice": "fuga_gas",
        "titolo": "Fuga di gas",
        "procedure": [
            {
                "lettera": "A",
                "titolo": PROCEDURE_TITLES["A"],
                "testo": (
                    "Chi percepisce odore di gas o attiva il rilevatore avverte "
                    "immediatamente il coordinatore. Non azionare interruttori "
                    "elettrici, telefoni cellulari o fiamme libere."
                ),
            },
            {
                "lettera": "B",
                "titolo": PROCEDURE_TITLES["B"],
                "testo": (
                    "Il coordinatore attiva l'evacuazione immediata, contatta il "
                    "Numero Unico di Emergenza (NUE) 112 e il pronto intervento "
                    "gas del distributore locale. Interdice l'accesso all'area."
                ),
            },
            {
                "lettera": "C",
                "titolo": PROCEDURE_TITLES["C"],
                "testo": (
                    "Se possibile in sicurezza, chiudere la valvola generale del "
                    "gas. Ventilare i locali aprendo porte e finestre. Non "
                    "tentare riparazioni autonome."
                ),
            },
            {
                "lettera": "D",
                "titolo": PROCEDURE_TITLES["D"],
                "testo": (
                    "Evacuazione rapida e ordinata verso il punto di raccolta, "
                    "tenendosi sopravvento rispetto all'edificio. Nessuno "
                    "rientra fino al nulla osta dei Vigili del Fuoco."
                ),
            },
            {
                "lettera": "E",
                "titolo": PROCEDURE_TITLES["E"],
                "testo": (
                    "Dopo la verifica dell'impianto e delle concentrazioni di "
                    "gas a cura dei Vigili del Fuoco o del distributore, "
                    "autorizzare il rientro. Registrare l'evento e richiedere "
                    "manutenzione straordinaria."
                ),
            },
        ],
    },
    "evacuazione_generale": {
        "codice": "evacuazione_generale",
        "titolo": "Evacuazione generale",
        "procedure": [
            {
                "lettera": "A",
                "titolo": PROCEDURE_TITLES["A"],
                "testo": (
                    "All'attivazione del segnale di evacuazione generale "
                    "({tipologia_allarme}), tutti i lavoratori "
                    "interrompono l'attivita' in sicurezza (spegnere macchine, "
                    "chiudere impianti a rischio)."
                ),
            },
            {
                "lettera": "B",
                "titolo": PROCEDURE_TITLES["B"],
                "testo": (
                    "Il coordinatore conferma l'evacuazione generale via "
                    "diffusione sonora o comunicazione diretta e informa, se "
                    "necessario, gli enti esterni tramite il Numero Unico di "
                    "Emergenza (NUE) 112."
                ),
            },
            {
                "lettera": "C",
                "titolo": PROCEDURE_TITLES["C"],
                "testo": (
                    "Gli addetti al primo soccorso verificano la presenza di "
                    "persone con difficolta' motorie o di orientamento e "
                    "organizzano l'assistenza all'esodo (es. con sedia di "
                    "evacuazione)."
                ),
            },
            {
                "lettera": "D",
                "titolo": PROCEDURE_TITLES["D"],
                "testo": (
                    "Dirigersi verso l'uscita seguendo la segnaletica, senza "
                    "correre, senza tornare indietro. Chiudere porte senza "
                    "chiave. Non utilizzare ascensori. Raggiungere il punto di "
                    "raccolta."
                ),
            },
            {
                "lettera": "E",
                "titolo": PROCEDURE_TITLES["E"],
                "testo": (
                    "Al punto di raccolta gli addetti effettuano l'appello. "
                    "Segnalare immediatamente al coordinatore eventuali assenze. "
                    "Il rientro e' autorizzato solo dal coordinatore dopo la "
                    "verifica degli ambienti."
                ),
            },
        ],
    },
}


def get_standard_procedures(
    tipologia_allarme: str | None = None,
) -> list[EventoEmergenza]:
    """Return a deep-copied list of all standard events with their A-E procedures.

    ``tipologia_allarme`` replaces the ``{tipologia_allarme}`` placeholder in
    the standard texts (point A of incendio / evacuazione generale); when
    ``None`` the default alarm type is used.
    """
    tipologia = _resolve_tipologia(tipologia_allarme)
    return [
        {
            "codice": e["codice"],
            "titolo": e["titolo"],
            "procedure": [
                {
                    **p,
                    "testo": p["testo"].replace(
                        TIPOLOGIA_ALLARME_PLACEHOLDER, tipologia
                    ),
                }
                for p in e["procedure"]
            ],
        }
        for e in _STANDARD.values()
    ]


def get_standard_procedure(
    evento: str, lettera: str, tipologia_allarme: str | None = None
) -> Procedura | None:
    """Return one standard procedure by event code + letter, or None."""
    event = _STANDARD.get(evento)  # type: ignore[arg-type]
    if not event:
        return None
    tipologia = _resolve_tipologia(tipologia_allarme)
    for p in event["procedure"]:
        if p["lettera"] == lettera.upper():
            return {
                **p,
                "testo": p["testo"].replace(TIPOLOGIA_ALLARME_PLACEHOLDER, tipologia),
            }
    return None


def merge_with_overrides(
    overrides: list[dict] | None,
    tipologia_allarme: str | None = None,
) -> list[dict]:
    """Merge standard procedures with per-client overrides.

    ``overrides`` follows the same shape as ``get_standard_procedures`` output
    but each procedure may carry a ``personalizzata: True`` flag and a modified
    ``testo``. Returns a fresh list with ``personalizzata`` on every item
    (False when the text matches the standard). ``tipologia_allarme`` is
    substituted into the standard texts only — operator-personalized texts are
    rendered verbatim.
    """
    standard = get_standard_procedures(tipologia_allarme)
    by_code: dict[str, dict] = {e["codice"]: e for e in standard}

    override_map: dict[tuple[str, str], str] = {}
    for override_evt in overrides or []:
        code = override_evt.get("codice")
        if not isinstance(code, str):
            continue
        for proc in override_evt.get("procedure") or []:
            letter = proc.get("lettera")
            text = proc.get("testo")
            if (
                isinstance(letter, str)
                and isinstance(text, str)
                and proc.get("personalizzata")
            ):
                override_map[(code, letter.upper())] = text

    merged: list[dict] = []
    for code, evt in by_code.items():
        procedure = []
        for p in evt["procedure"]:
            text = override_map.get((code, p["lettera"]))
            if text is not None:
                procedure.append(
                    {
                        "lettera": p["lettera"],
                        "titolo": p["titolo"],
                        "testo": text,
                        "personalizzata": True,
                    }
                )
            else:
                procedure.append(
                    {
                        "lettera": p["lettera"],
                        "titolo": p["titolo"],
                        "testo": p["testo"],
                        "personalizzata": False,
                    }
                )
        merged.append(
            {
                "codice": code,
                "titolo": evt["titolo"],
                "procedure": procedure,
            }
        )
    return merged
