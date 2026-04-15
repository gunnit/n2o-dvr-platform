"""Validation harness: run every generator in-memory (no DB) against a
minimal Acme-like fixture, and verify all 17 .docx (16 documents + HACCP forms
zip) files are produced and structurally valid.

Usage:
    python -m scripts.verify_all_generators [output_dir]

Prints PASS/FAIL per generator and saves output to the given directory
(default /tmp/dlg_verify).

This bypasses the DB entirely by monkey-patching BaseDocumentGenerator.load_data
and the data loader functions to return pre-built in-memory objects.
"""

import asyncio
import os
import sys
import types
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

# Allow running from /mnt/c/Dev/dlg/backend
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from docx import Document as OpenDocx  # noqa: E402


# ---------------------------------------------------------------------------
# Lightweight in-memory stand-ins for SQLAlchemy models
# (only fields used by generators are populated)
# ---------------------------------------------------------------------------

@dataclass
class NS:
    """Generic namespace with arbitrary attrs."""
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    def __getattr__(self, k):  # permissive access
        return None


def mk(**kw):
    n = NS()
    for k, v in kw.items():
        setattr(n, k, v)
    return n


# ---------------------------------------------------------------------------
# Build the fixture data
# ---------------------------------------------------------------------------

def build_fixture() -> dict:
    azienda = mk(
        id=uuid.uuid4(),
        ragione_sociale="ACME MECCANICA COMPOSITA SRL",
        partita_iva="04567890123",
        sede_legale_via="Via dell'Industria 42",
        sede_legale_citta="Parma (PR)",
        attivita="Lavorazioni meccaniche di precisione con mensa aziendale",
        codice_ateco="25.62.00",
        descrizione_attivita="ACME Meccanica opera nel settore delle lavorazioni meccaniche di precisione.",
        organization_id=uuid.uuid4(),
        survey_status="completed",
    )

    ufficio = mk(id=uuid.uuid4(), nome="Uffici amministrativi e tecnici", tipo="Ufficio", superficie_mq=220, valutazioni_rischio=[])
    officina = mk(id=uuid.uuid4(), nome="Officina meccanica", tipo="Officina", superficie_mq=850, valutazioni_rischio=[])
    magazzino = mk(id=uuid.uuid4(), nome="Magazzino", tipo="Magazzino", superficie_mq=620, valutazioni_rischio=[])
    mensa = mk(id=uuid.uuid4(), nome="Mensa aziendale con cucina", tipo="Cucina", superficie_mq=180, valutazioni_rischio=[])
    deposito = mk(id=uuid.uuid4(), nome="Deposito chimici", tipo="Magazzino", superficie_mq=90, valutazioni_rischio=[])
    esterno = mk(id=uuid.uuid4(), nome="Area esterna", tipo="Esterno", superficie_mq=440, valutazioni_rischio=[])
    ambienti = [ufficio, officina, magazzino, mensa, deposito, esterno]

    # Mock a couple of valutazioni_rischio per ambiente
    for amb in ambienti:
        amb.valutazioni_rischio = [
            mk(categoria_rischio="Macchine", applicabile=True, pericolo="Contatto con organi meccanici", probabilita_p=2, danno_d=2, indice_i=6, livello_rischio="MODESTO", misure_prevenzione="Ripari fissi, pulsanti emergenza"),
            mk(categoria_rischio="Incendio-Esplosioni", applicabile=True, pericolo="Inneschi", probabilita_p=1, danno_d=3, indice_i=7, livello_rischio="GRAVE", misure_prevenzione="Estintori, cartellonistica"),
        ]

    persone = [
        mk(id=uuid.uuid4(), nominativo="Mario Rossi", mansione="Datore di lavoro", sesso="M", fascia_eta=">18", ruolo_datore_lavoro=True, ruolo_rspp=False, ruolo_rls=False, ruolo_primo_soccorso=False, ruolo_antincendio=False, ruolo_preposto=False),
        mk(id=uuid.uuid4(), nominativo="Luca Bianchi", mansione="RSPP", sesso="M", fascia_eta=">18", ruolo_rspp=True, ruolo_datore_lavoro=False, ruolo_rls=False, ruolo_primo_soccorso=False, ruolo_antincendio=False, ruolo_preposto=False),
        mk(id=uuid.uuid4(), nominativo="Giulia Verdi", mansione="RLS", sesso="F", fascia_eta=">18", ruolo_rls=True, ruolo_datore_lavoro=False, ruolo_rspp=False, ruolo_primo_soccorso=False, ruolo_antincendio=False, ruolo_preposto=False),
        mk(id=uuid.uuid4(), nominativo="Antonio Marrone", mansione="Operaio Tornitore", sesso="M", fascia_eta=">18", ruolo_primo_soccorso=True, ruolo_datore_lavoro=False, ruolo_rspp=False, ruolo_rls=False, ruolo_antincendio=False, ruolo_preposto=False),
        mk(id=uuid.uuid4(), nominativo="Valentina Rinaldi", mansione="Impiegata (gestante)", sesso="F", fascia_eta=">18", ruolo_datore_lavoro=False, ruolo_rspp=False, ruolo_rls=False, ruolo_primo_soccorso=False, ruolo_antincendio=False, ruolo_preposto=False),
    ]
    attrezzature = [
        mk(descrizione="Tornio parallelo CNC", marcatura_ce=True, verifiche_periodiche=True),
        mk(descrizione="Fresatrice CNC", marcatura_ce=True, verifiche_periodiche=True),
        mk(descrizione="Carrello elevatore", marcatura_ce=True, verifiche_periodiche=True),
        mk(descrizione="Postazione VDT", marcatura_ce=True, verifiche_periodiche=False),
    ]
    sostanze = [
        mk(nome_prodotto="Olio da taglio", produttore="ChemCo", pittogrammi=["GHS07"], frasi_h=["H315"], frasi_p=["P264"], stato_miscela="Liquido"),
        mk(nome_prodotto="Disinfettante mensa", produttore="FoodSafe", pittogrammi=["GHS07"], frasi_h=["H319"], frasi_p=["P305+P351+P338"], stato_miscela="Liquido"),
    ]

    # Assessment rows
    mmc_rows = [
        mk(compito="Carico/scarico pezzi dal magazzino al tornio", peso_kg=15.0, sesso="M", fascia_eta=">18",
           cp=25.0, fattore_a=0.93, fattore_b=0.93, fattore_c=0.83, fattore_d=0.85, fattore_e=1.0, fattore_f=0.88,
           plr=15.0, indice_ir=1.0, livello_rischio="GIALLO", note="Sollevamento con flessione del tronco"),
    ]
    vdt_rows = [
        mk(postazione="Ufficio 1", ore_settimanali=32.0, esposto=True,
           schermo_conforme=True, tastiera_separata=True, sedile_regolabile=True, poggiapiedi_disponibile=True,
           illuminazione_adeguata=True, riflessi_assenti=True, spazio_adeguato=True, pause_previste=True,
           idoneita_visiva="idoneo", periodicita_sorveglianza="quinquennale", note=""),
    ]
    stress_row = mk(
        gruppo_omogeneo="Azienda intera",
        area_a_eventi_sentinella={"infortuni_biennio": 1, "assenze": 5, "turnover": 2},
        area_b_contenuto_lavoro={"monotonia": False, "ritmi_elevati": True},
        area_c_contesto_lavoro={"comunicazione": True, "autonomia": True},
        punteggio_a=2, punteggio_b=3, punteggio_c=1, punteggio_totale=6, livello_rischio="BASSO",
        misure_correttive="Monitoraggio annuale.",
    )
    incendio_rows = [
        mk(ambiente_id=officina.id, inf=3, si=3, pi=2, punteggio_totale=8, livello_rischio="ALTO", misure_prevenzione="Estintori CO2 + polvere", estintori_presenti=4, idranti_presenti=2, uscite_emergenza=2),
        mk(ambiente_id=ufficio.id, inf=1, si=2, pi=2, punteggio_totale=5, livello_rischio="MEDIO", misure_prevenzione="Estintori polvere", estintori_presenti=2, idranti_presenti=1, uscite_emergenza=1),
    ]
    micro_rows = [
        mk(ambiente_id=ufficio.id, tipo_ambiente="moderato", temperatura_aria=21.0, temperatura_radiante=21.0, velocita_aria=0.1, umidita_relativa=50.0, metabolismo=1.2, isolamento_vestiario=0.7, pmv=None, ppd=None),
        mk(ambiente_id=officina.id, tipo_ambiente="moderato", temperatura_aria=19.0, temperatura_radiante=20.0, velocita_aria=0.2, umidita_relativa=55.0, metabolismo=1.6, isolamento_vestiario=0.8, pmv=None, ppd=None),
        mk(ambiente_id=mensa.id, tipo_ambiente="severo_caldo", temperatura_aria=28.0, temperatura_radiante=30.0, velocita_aria=0.1, umidita_relativa=60.0, metabolismo=1.7, isolamento_vestiario=0.5, pmv=None, ppd=None),
    ]
    gestante_persona = persone[4]
    gestanti_rows = [
        mk(persona=gestante_persona,
           stato="gestante",
           data_notifica=date(2026, 3, 20),
           data_presunto_parto=date(2026, 10, 15),
           rischi_vietati=[{"rischio": "Posizioni prolungate in piedi", "allegato": "A", "misura": "Astensione anticipata"}],
           misure_adeguamento="Mansione alternativa di supporto amministrativo seduta.",
           mansione_alternativa="Impiegata back-office",
           richiesta_astensione_anticipata=False,
           firma_lavoratrice="Valentina Rinaldi",
           firma_datore_lavoro="Mario Rossi",
           firma_rspp="Luca Bianchi",
           firma_medico_competente="Dott. Paolo Neri"),
    ]
    biologico_rows = [mk(
        settore="alimentare",
        agenti_identificati=[{"nome": "Salmonella spp.", "gruppo": "2", "via": "ingestione", "patologia": "Salmonellosi"}],
        misure_protettive=[{"descrizione": "Catena del freddo ≤ 4°C"}],
        dpi_richiesti=[{"descrizione": "Guanti monouso"}],
        protocollo_sanitario="Sorveglianza annuale.",
        formazione_specifica="Corso HACCP base.",
        livello_rischio="MEDIO",
    )]

    haccp_config = mk(
        tipologia_attivita="Mensa aziendale",
        numero_pasti_giorno=60,
        tipi_alimenti_trattati=["carne", "pesce", "verdure"],
        ccps=[
            {"codice": "CCP1", "nome": "Ricevimento", "limite_critico": "T <=4 C"},
            {"codice": "CCP3", "nome": "Cottura", "limite_critico": "T>=75 C"},
        ],
        responsabile_haccp="Maria Conti",
    )
    haccp_forms = [
        mk(form_code=f"SA-{str(i).zfill(2)}", form_title=t, data={"righe": []})
        for i, t in enumerate([
            "Elenco fornitori", "Ricevimento merci", "Temperature frigo", "Temperature congelatore",
            "Derattizzazione", "Sanificazione", "Temperature cottura", "Raffreddamento",
            "Olio friggitrice", "Acqua potabile", "Formazione", "Schede prodotti",
            "Non conformita", "Allergeni", "Pulizia attrezzature", "Piano autocontrollo",
        ], start=1)
    ]

    pee_azienda_row = mk(
        tipo="azienda",
        squadra_emergenza=[
            {"nome": "Franco Gialli", "ruolo": "Coordinatore"},
            {"nome": "Marco Esposito", "ruolo": "Antincendio"},
            {"nome": "Roberto Moretti", "ruolo": "Primo soccorso"},
        ],
        addetti_primo_soccorso=[{"nome": "Roberto Moretti", "ruolo": "Primo soccorso"}],
        addetti_antincendio=[{"nome": "Marco Esposito", "ruolo": "Antincendio"}],
        coordinatore_emergenza="Franco Gialli",
        telefoni_emergenza={"112": "Numero unico europeo", "115": "Vigili del fuoco"},
        scenari=[{"codice": "A", "titolo": "Incendio", "procedura": "Chiamare 115, evacuare."}],
        punto_raccolta="Piazzale ingresso",
        vie_fuga="Uscita nord, uscita sud officina",
        tempo_evacuazione_stimato_min=3,
        frequenza_prove="annuale",
    )
    pee_comune_row = mk(
        tipo="comune",
        squadra_emergenza=[],
        addetti_primo_soccorso=[], addetti_antincendio=[],
        coordinatore_emergenza="Franco Gialli",
        telefoni_emergenza={"112": "Numero unico europeo"},
        scenari=[],
        punto_raccolta="Piazzale condominiale",
        vie_fuga="Scale antincendio",
        tempo_evacuazione_stimato_min=5,
        frequenza_prove="annuale",
    )

    duvri_rows = [mk(
        appaltatore_ragione_sociale="Pulizie Industriali Parma SRL",
        appaltatore_partita_iva="01234567890",
        appaltatore_referente="Giovanni Pulito",
        oggetto_appalto="Servizio di pulizia giornaliera",
        data_inizio=date(2026, 5, 1),
        data_fine=date(2027, 4, 30),
        importo_appalto=42000.0,
        costi_sicurezza=850.0,
        interferenze=[{"rischio": "Scivolamento", "misure": "Segnaletica", "dpi": ["scarpe antiscivolo"]}],
    )]
    pos_rows = [mk(
        cantiere_indirizzo="Via dei Molini 15, Parma",
        cantiere_descrizione="Installazione linea meccanica",
        committente="Food&Pack SpA",
        direttore_lavori="Ing. Mazzi",
        coordinatore_sicurezza="Arch. Bruni",
        data_inizio=date(2026, 6, 1),
        data_fine=date(2026, 7, 15),
        importo_lavori=85000.0,
        numero_massimo_lavoratori=4,
        fasi_lavorative=[
            {"fase": "Allestimento", "descrizione": "Delimitazione", "rischi": ["caduta"], "dpi": ["casco"], "mezzi": ["furgone"]},
            {"fase": "Posa componenti", "descrizione": "Montaggio", "rischi": ["schiacciamento", "MMC"], "dpi": ["guanti"], "mezzi": ["transpallet"]},
        ],
        valutazione_rumore={"lex_8h_dba": 82, "fascia": "80-85", "dpi_obbligatori": True},
        valutazione_vibrazioni={"a8_mano_braccio": 2.1, "a8_corpo_intero": 0.4, "entro_limiti": True},
        mezzi_attrezzature=[{"tipo": "Transpallet"}, {"tipo": "Avvitatori"}],
        sostanze_pericolose=[{"nome": "Solvente", "uso": "Pulitura"}],
    )]

    return {
        "azienda": azienda,
        "ambienti": ambienti,
        "persone": persone,
        "attrezzature": attrezzature,
        "sostanze_chimiche": sostanze,
        "ufficio": ufficio, "officina": officina, "mensa": mensa,
        "mmc": mmc_rows,
        "vdt": vdt_rows,
        "stress": stress_row,
        "incendio": incendio_rows,
        "microclima": micro_rows,
        "gestanti": gestanti_rows,
        "biologico": biologico_rows,
        "haccp_config": haccp_config,
        "haccp_forms": haccp_forms,
        "pee_azienda": pee_azienda_row,
        "pee_comune": pee_comune_row,
        "duvri": duvri_rows,
        "pos": pos_rows,
        "generated_at": datetime.now(),
    }


# ---------------------------------------------------------------------------
# Patch generators to use fixture instead of DB
# ---------------------------------------------------------------------------

def patch_generators(fixture: dict, output_dir: str):
    from app.services.document_generator import base, data_loader
    from app.services.document_generator.dvr_master import DVRMasterGenerator
    import app.services.document_generator.allegato_mmc as g_mmc
    import app.services.document_generator.allegato_vdt as g_vdt
    import app.services.document_generator.allegato_stress as g_stress
    import app.services.document_generator.allegato_gestanti as g_gest
    import app.services.document_generator.allegato_incendio as g_inc
    import app.services.document_generator.allegato_microclima as g_micro
    import app.services.document_generator.allegato_microclima_severo as g_micros
    import app.services.document_generator.pee_azienda as g_peea
    import app.services.document_generator.pee_comune as g_peec
    import app.services.document_generator.duvri as g_duvri
    import app.services.document_generator.pos as g_pos
    import app.services.document_generator.haccp_manuale as g_haccp
    import app.services.document_generator.haccp_forms as g_haccpf

    async def fake_load_data(self):
        return {
            "azienda": fixture["azienda"],
            "persone": fixture["persone"],
            "ambienti": fixture["ambienti"],
            "attrezzature": fixture["attrezzature"],
            "sostanze_chimiche": fixture["sostanze_chimiche"],
            "generated_at": fixture["generated_at"],
        }
    base.BaseDocumentGenerator.load_data = fake_load_data

    # Override output dir
    def fake_output_dir(self):
        p = os.path.join(output_dir, str(fixture["azienda"].id))
        os.makedirs(p, exist_ok=True)
        return p
    base.BaseDocumentGenerator._get_output_dir = fake_output_dir

    async def v1(self):
        return 1

    # Patch _next_version for each generator module
    for mod in [g_mmc.AllegatoMmcGenerator, g_vdt.AllegatoVdtGenerator, g_stress.AllegatoStressGenerator,
                g_gest.AllegatoGestantiGenerator, g_inc.AllegatoIncendioGenerator,
                g_micro.AllegatoMicroclimaGenerator, g_micros.AllegatoMicroclimaSeveroGenerator,
                g_peea.PeeAziendaGenerator, g_peec.PeeComuneGenerator,
                g_duvri.DuvriGenerator, g_pos.PosGenerator,
                g_haccp.HaccpManualeGenerator, g_haccpf.HaccpFormsGenerator]:
        mod._next_version = v1
    # DVR Master already uses its own _get_next_version
    DVRMasterGenerator._get_next_version = v1
    # Biologico uses _next_version helper from _biologico_common
    from app.services.document_generator import _biologico_common
    async def bio_v1(gen, tipo_doc, aliases):
        return 1
    _biologico_common._next_version = bio_v1

    # Patch data loaders
    async def lm(db, aid): return fixture["mmc"]
    async def lv(db, aid): return fixture["vdt"]
    async def ls(db, aid): return fixture["stress"]
    async def li(db, aid): return fixture["incendio"]
    async def lmc(db, aid): return fixture["microclima"]
    async def lg(db, aid): return fixture["gestanti"]
    async def lb(db, aid, settore=None):
        if settore is None or settore == "alimentare":
            return fixture["biologico"]
        return []
    async def lh(db, aid): return fixture["haccp_config"], fixture["haccp_forms"]
    async def lpee(db, aid, tipo="azienda"):
        return fixture["pee_azienda"] if tipo == "azienda" else fixture["pee_comune"]
    async def ld(db, aid): return fixture["duvri"]
    async def lp(db, aid): return fixture["pos"]

    data_loader.load_mmc = lm
    data_loader.load_vdt = lv
    data_loader.load_stress = ls
    data_loader.load_incendio = li
    data_loader.load_microclima = lmc
    data_loader.load_gestanti = lg
    data_loader.load_biologico = lb
    data_loader.load_haccp = lh
    data_loader.load_pee = lpee
    data_loader.load_duvri = ld
    data_loader.load_pos = lp
    # Also patch the module-level imports in each generator that did `from ... import load_X`
    for mod, (attr, fn) in [
        (g_mmc, ("load_mmc", lm)), (g_vdt, ("load_vdt", lv)),
        (g_stress, ("load_stress", ls)), (g_inc, ("load_incendio", li)),
        (g_micro, ("load_microclima", lmc)), (g_micros, ("load_microclima", lmc)),
        (g_gest, ("load_gestanti", lg)), (g_duvri, ("load_duvri", ld)),
        (g_pos, ("load_pos", lp)), (g_haccp, ("load_haccp", lh)),
        (g_haccpf, ("load_haccp", lh)), (g_peea, ("load_pee", lpee)),
        (g_peec, ("load_pee", lpee)),
    ]:
        setattr(mod, attr, fn)
    # For biologico common
    from app.services.document_generator import _biologico_common as bc
    bc.load_biologico = lb


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_docx(path: str) -> tuple[bool, str]:
    """Try opening as .docx; for .zip (HACCP_FORMS), validate zip + contents."""
    if path.endswith(".zip"):
        import zipfile
        if not zipfile.is_zipfile(path):
            return False, "not a valid zip"
        with zipfile.ZipFile(path) as z:
            names = z.namelist()
            if not any(n.endswith(".docx") for n in names):
                return False, "zip contains no .docx"
            return True, f"zip with {len(names)} entries"
    try:
        d = OpenDocx(path)
        n_p = len(d.paragraphs)
        n_t = len(d.tables)
        return True, f"{n_p} paragraphs, {n_t} tables"
    except Exception as e:
        return False, f"open failed: {e}"


async def run_one(tipo: str, azienda_id: uuid.UUID) -> tuple[bool, str, str]:
    from app.services.document_generator.dispatcher import get_generator_for
    try:
        gen = get_generator_for(tipo, azienda_id, db=None)
        path = await gen.generate()
        ok, msg = validate_docx(path)
        return ok, path, msg
    except Exception as e:
        import traceback
        return False, "", f"{type(e).__name__}: {e}\n{traceback.format_exc()[-400:]}"


async def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "/tmp/dlg_verify"
    os.makedirs(out, exist_ok=True)

    fixture = build_fixture()
    patch_generators(fixture, out)

    from app.services.document_generator.dispatcher import ALL_DOCUMENT_TYPES
    results = []
    for tipo in ALL_DOCUMENT_TYPES:
        ok, path, msg = await run_one(tipo, fixture["azienda"].id)
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {tipo:40s} -> {os.path.basename(path) if path else '(none)'}  {msg}")
        results.append((tipo, ok, path, msg))

    n_pass = sum(1 for r in results if r[1])
    n_total = len(results)
    print("\n" + "=" * 60)
    print(f"RESULT: {n_pass}/{n_total} generators produced valid output")
    print(f"Output directory: {out}/<azienda_uuid>/")
    print("=" * 60)

    if n_pass != n_total:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
