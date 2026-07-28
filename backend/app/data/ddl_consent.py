"""The datore-di-lavoro acknowledgement a direct (Model B) signup must give.

MB-5.7. Model A customers are safety professionals drafting documents for
*their* clients; Model B customers are the employer, and the employer signs the
DVR and answers for it under D.Lgs. 81/2008 art. 17 c.1 lett. a — a duty that is
non-delegable. Selling a drafting tool straight to that employer is legitimate;
letting them believe they have bought a compliant DVR rather than a draft they
must assess and sign is not.

So `POST /auth/register-direct` refuses to provision a tenant without an
explicit acknowledgement, and stores which wording was accepted
(`organizations.ddl_consent_at` / `.ddl_consent_version`).

**This module is the authority for the wording.** The signup form renders the
same text and echoes back the version it displayed; the endpoint rejects a
version it does not know, so a copy change that lands on only one side fails
loudly instead of silently stamping consent to text nobody saw.

Changing the text means **adding a new version**, never editing an old one in
place — the stored version is evidence of what a specific customer agreed to on
a specific day, and rewriting it destroys that.

> Per `docs/build/MONETIZATION-BUILD-PLAN.md` MB-5.7 this wording, the /prezzi
> disclaimer and (when it ships) the ATECO eligibility table go to legal counsel
> before the direct channel is promoted. The text below is the product team's
> draft, unreviewed as of 2026-07-28.
"""

from __future__ import annotations

# Version ids are `YYYY-MM` of the wording, not of the deploy. The frontend
# constant `DDL_CONSENT_VERSION` in `frontend/src/lib/consent.ts` must name a
# version present here.
DDL_CONSENT_VERSION = "2026-07"

DDL_CONSENT_TEXTS: dict[str, str] = {
    "2026-07": (
        "Dichiaro di essere il datore di lavoro o il soggetto responsabile "
        "della sicurezza per l'impresa che sto registrando. La piattaforma è "
        "uno strumento di redazione assistita: predispone struttura, calcoli e "
        "testi del documento, ma non sostituisce la valutazione dei rischi né "
        "la firma del datore di lavoro, che restano di mia competenza e "
        "responsabilità ai sensi del D.Lgs. 81/2008."
    ),
}

# Wordings still accepted at signup. Old versions stay readable in the table
# above (they are what existing customers agreed to) but must not be offered to
# anyone new, so acceptance is checked against this set, not the dict.
ACCEPTED_CONSENT_VERSIONS: frozenset[str] = frozenset({DDL_CONSENT_VERSION})

assert DDL_CONSENT_VERSION in DDL_CONSENT_TEXTS, (
    "DDL_CONSENT_VERSION names a wording that does not exist — a direct signup "
    "would stamp consent to text that was never written."
)
