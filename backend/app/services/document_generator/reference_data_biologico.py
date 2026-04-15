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
