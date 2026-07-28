"""Role-based capabilities — who may do what inside one organization.

Two orthogonal axes decide what a person sees in this product, and conflating
them is the mistake this module exists to prevent:

* **What the organization bought** — plan, limits, credits, allowed document
  types. That is ``app.billing`` and it answers with ``402 Payment Required``.
* **What this person is allowed to do inside that organization** — the three
  personas in ``docs/context/USER_STORIES.md``. That is this module, and it
  answers with ``403 Forbidden``.

A field operator on an Enterprise plan still cannot manage users; an admin on a
lapsed plan still cannot generate a document. Neither check substitutes for the
other, so they never share a code path.

The personas, verbatim from USER_STORIES:

``operatore_campo``
    "Visits client sites to conduct surveys and collect data. Uses
    tablet/smartphone, often offline or on weak connections." Collects — does
    not finalize. Generating a DVR is a signed, billable, legally-operative act
    performed after review, so it is deliberately not theirs.

``operatore_ufficio``
    "Reviews AI-generated documents, adjusts risk scores, and finalizes
    documentation." The full production role, minus anything that spends money
    or changes who works here.

``admin``
    "Manages client portfolio, oversees document generation, handles billing and
    delivery. Has access to all clients and audit trails." Everything.

**This module is the single source of truth.** The frontend renders navigation
from the capability set returned by ``GET /auth/me``, so a new capability shows
up in the UI without a second, hand-copied table drifting out of step.
"""

from __future__ import annotations

# --- The vocabulary --------------------------------------------------------
# Named after the action, not the screen: screens get renamed and merged, the
# underlying permission ("may this person commit the organization to a recurring
# charge") does not.

#: Read the client/site register.
AZIENDE_READ = "aziende:read"
#: Create a new client company (Model A) or sede (Model B).
AZIENDE_CREATE = "aziende:create"
#: Remove one, with everything hanging off it.
AZIENDE_DELETE = "aziende:delete"

#: Fill in and edit a sopralluogo — the field job.
SURVEY_WRITE = "survey:write"
#: Score risks and complete the specialist assessments (MMC, VDT, stress, …).
ASSESSMENTS_WRITE = "assessments:write"

#: List and download generated documents. Never gated on plan (D.Lgs. 81/2008
#: retention), and never withheld from anyone who can see the company.
DOCUMENTS_READ = "documents:read"
#: Start a generation run. The finalization act.
DOCUMENTS_GENERATE = "documents:generate"
#: Delete a generated document / revision.
DOCUMENTS_DELETE = "documents:delete"

#: Invoke the AI suggesters and extractors. Spends the organization's credits,
#: which is why it is a capability and not a free-for-all.
AI_USE = "ai:use"

#: See the plan, the limits and the credit tracker.
BILLING_READ = "billing:read"
#: Subscribe, change plan, cancel, buy credit packs. Commits the organization
#: to a charge.
BILLING_MANAGE = "billing:manage"

#: Invite, edit and re-role colleagues.
USERS_MANAGE = "users:manage"
#: Letterhead, logo, organization anagrafica.
ORG_MANAGE = "org:manage"
#: Feedback inbox, AI-feedback analytics, backup status — the oversight screens.
ADMIN_TOOLS = "admin:tools"

ALL_CAPABILITIES: frozenset[str] = frozenset(
    {
        AZIENDE_READ,
        AZIENDE_CREATE,
        AZIENDE_DELETE,
        SURVEY_WRITE,
        ASSESSMENTS_WRITE,
        DOCUMENTS_READ,
        DOCUMENTS_GENERATE,
        DOCUMENTS_DELETE,
        AI_USE,
        BILLING_READ,
        BILLING_MANAGE,
        USERS_MANAGE,
        ORG_MANAGE,
        ADMIN_TOOLS,
    }
)


# --- The roles -------------------------------------------------------------

ROLE_ADMIN = "admin"
ROLE_OPERATORE_UFFICIO = "operatore_ufficio"
ROLE_OPERATORE_CAMPO = "operatore_campo"

#: Italian labels for the UI. The role string itself is an internal identifier
#: and used to leak straight into the sidebar as "operatore_ufficio".
ROLE_LABELS: dict[str, str] = {
    ROLE_ADMIN: "Amministratore",
    ROLE_OPERATORE_UFFICIO: "Operatore in ufficio",
    ROLE_OPERATORE_CAMPO: "Operatore sul campo",
}

ROLE_DESCRIPTIONS: dict[str, str] = {
    ROLE_ADMIN: (
        "Accesso completo: clienti, documenti, utenti, personalizzazione e abbonamento."
    ),
    ROLE_OPERATORE_UFFICIO: (
        "Rivede i sopralluoghi, completa le valutazioni e genera i documenti. "
        "Non gestisce utenti né abbonamento."
    ),
    ROLE_OPERATORE_CAMPO: (
        "Compila i sopralluoghi in cantiere o in azienda e consulta i documenti. "
        "Non genera documenti finali."
    ),
}

_FIELD_CAPABILITIES: frozenset[str] = frozenset(
    {
        AZIENDE_READ,
        SURVEY_WRITE,
        ASSESSMENTS_WRITE,
        DOCUMENTS_READ,
        # The camera-based attrezzature recogniser and the SDS scanner are field
        # tools — withholding AI from the person holding the phone would defeat
        # the point of the survey app.
        AI_USE,
        # Everyone can *see* the plan and the credit balance. Spending someone
        # else's credits without being able to check what is left is how an
        # operator discovers the ceiling as a 402 halfway through a sopralluogo;
        # buying more stays admin-only (BILLING_MANAGE).
        BILLING_READ,
    }
)

_OFFICE_CAPABILITIES: frozenset[str] = _FIELD_CAPABILITIES | {
    # Generating, editing and versioning the finished document — the office
    # operator's whole job description.
    DOCUMENTS_GENERATE,
    DOCUMENTS_DELETE,
    # Deliberately NOT granted: AZIENDE_CREATE / AZIENDE_DELETE. Taking a client
    # on (or dropping one) is a commercial decision the portfolio owner makes —
    # it is also what starts the "active company" meter billing. US-5.1 states
    # this as an acceptance criterion and the endpoints have always enforced it;
    # this matrix keeps that promise rather than quietly widening it.
}

ROLE_CAPABILITIES: dict[str, frozenset[str]] = {
    ROLE_ADMIN: ALL_CAPABILITIES,
    ROLE_OPERATORE_UFFICIO: frozenset(_OFFICE_CAPABILITIES),
    ROLE_OPERATORE_CAMPO: _FIELD_CAPABILITIES,
}

ALLOWED_ROLES: frozenset[str] = frozenset(ROLE_CAPABILITIES)

#: What an unrecognised role gets. Roles only ever enter the database through
#: ``users.py``, which validates against :data:`ALLOWED_ROLES` — but a row
#: written by a migration, a fixture or a hand-run UPDATE could still carry
#: something else, and the safe reading of "I don't know what you are" is the
#: least-privileged persona, not a crash and not admin.
_UNKNOWN_ROLE_CAPABILITIES: frozenset[str] = _FIELD_CAPABILITIES


def capabilities_for(role: str | None) -> frozenset[str]:
    """Every capability granted to ``role``."""
    return ROLE_CAPABILITIES.get(role or "", _UNKNOWN_ROLE_CAPABILITIES)


def has_capability(role: str | None, capability: str) -> bool:
    return capability in capabilities_for(role)


def role_label(role: str | None) -> str:
    return ROLE_LABELS.get(role or "", "Operatore")


def validate_matrix() -> None:
    """Fail loudly on a matrix that would misbehave. Called by the tests.

    Two properties matter and neither is obvious from reading the literals:
    every role's grants must be real capabilities (a typo would silently grant
    nothing), and the personas must nest — an office operator can do everything
    a field operator can, an admin everything an office operator can. A
    non-nesting matrix means "promoting" someone takes something away, which no
    admin expects from a dropdown labelled with three ascending roles.
    """
    for role, caps in ROLE_CAPABILITIES.items():
        unknown = caps - ALL_CAPABILITIES
        if unknown:
            raise ValueError(f"{role} grants unknown capabilities: {sorted(unknown)}")
        if role not in ROLE_LABELS:
            raise ValueError(f"{role} has no Italian label")

    if not ROLE_CAPABILITIES[ROLE_OPERATORE_CAMPO] <= ROLE_CAPABILITIES[ROLE_OPERATORE_UFFICIO]:
        raise ValueError("operatore_ufficio must be a superset of operatore_campo")
    if not ROLE_CAPABILITIES[ROLE_OPERATORE_UFFICIO] <= ROLE_CAPABILITIES[ROLE_ADMIN]:
        raise ValueError("admin must be a superset of operatore_ufficio")
