"""Fire risk prevention/protection measures per level.

Source: D.M. 03/09/2021 (criteri di progettazione, gestione dell'emergenza
incendio) and D.Lgs. 81/2008 art. 46. See LEGISLATION_REFERENCE.md.

The list replaces the single paragraph previously inlined in
`frontend/src/app/(dashboard)/assessments/incendio/[aziendaId]/page.tsx`
(`AZIONE_PER_LIVELLO`). Each entry is a standalone, user-selectable
measure rendered as a checklist item in the operator UI (US-3.12).
"""

from typing import Literal

Livello = Literal["Basso", "Medio", "Alto"]

_MEASURES: dict[str, list[str]] = {
    "Basso": [
        "Mantenere in efficienza gli estintori portatili esistenti con verifica semestrale.",
        "Verificare periodicamente vie di esodo, segnaletica e illuminazione di sicurezza.",
        "Aggiornare annualmente la formazione antincendio del personale (livello 1 - rischio basso).",
        "Redigere o aggiornare il piano di emergenza ed evacuazione aziendale.",
    ],
    "Medio": [
        "Installare impianto di rilevazione automatica incendi nelle aree a maggior carico di incendio.",
        "Adottare misure di compartimentazione per separare aree di lavoro con elevato carico di incendio.",
        "Controllare le sorgenti di innesco (apparecchi elettrici, sostanze infiammabili, lavorazioni a caldo).",
        "Designare e formare gli addetti alla gestione dell'emergenza (formazione livello 2).",
        "Aggiornare il piano di emergenza ed evacuazione con prove semestrali documentate.",
    ],
    "Alto": [
        "Attivare immediatamente misure straordinarie di prevenzione e protezione antincendio.",
        "Coinvolgere un professionista antincendio iscritto negli elenchi del Ministero dell'Interno (ex L. 818/1984).",
        "Presentare SCIA ai Vigili del Fuoco ove prevista dall'attività ai sensi del DPR 151/2011.",
        "Installare impianti di rilevazione e spegnimento automatici (sprinkler, rilevatori lineari, sistemi gas).",
        "Garantire formazione antincendio di livello 3 a tutti gli addetti alla gestione dell'emergenza.",
        "Prevedere valutazione approfondita del rischio incendio con metodo FSE (Fire Safety Engineering) ove applicabile.",
    ],
}


def get_measures_for_level(livello: Livello) -> list[str]:
    """Return the canonical list of prevention/protection measures for the level.

    Args:
        livello: One of "Basso", "Medio", "Alto".

    Returns:
        A fresh list of Italian measure strings (caller-safe to mutate).

    Raises:
        ValueError: if ``livello`` is not a recognised band.
    """
    if livello not in _MEASURES:
        raise ValueError(f"Livello non valido: {livello!r}")
    return list(_MEASURES[livello])
