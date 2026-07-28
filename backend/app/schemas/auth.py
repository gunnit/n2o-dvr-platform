import uuid

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    # Optional: the register form allows an empty "organization" input and
    # sends null. The endpoint falls back to "{full_name}'s Organization".
    organization_name: str | None = None


class RegisterDirectRequest(RegisterRequest):
    """A company registering to document *itself* (Model B).

    Deliberately a separate schema and endpoint rather than an `account_type`
    field on `RegisterRequest`: the channel a tenant belongs to decides which
    price list it can buy from, so it must never be settable by an optional
    parameter on the consultant signup path.
    """

    # MB-5.7 — refused unless true. Not a checkbox we can default: the whole
    # point is that the employer actively acknowledged it.
    consenso_datore_lavoro: bool
    # Which wording the form displayed. Validated against
    # `app.data.ddl_consent.ACCEPTED_CONSENT_VERSIONS` so a copy change on one
    # side alone fails loudly instead of stamping consent to unseen text.
    consenso_versione: str = Field(min_length=1, max_length=16)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: str
    organization_id: uuid.UUID

    model_config = {"from_attributes": True}


class MeResponse(UserResponse):
    """`/auth/me`, extended with everything the shell needs to render itself.

    The frontend builds its navigation from `capabilities` rather than from a
    second copy of the role matrix: two tables of the same rules drift, and the
    one that drifts is always the one the customer sees. `role_label` is here
    for the same reason — `operatore_ufficio` is an internal identifier and used
    to be printed verbatim under the user's name in the sidebar.

    Cosmetic only. Every capability is re-checked server-side on the endpoint
    that needs it, so a stale session can hide a button but never grant one.
    """

    role_label: str
    capabilities: list[str]
    #: 'consultant' | 'direct' — decides the tenant's vocabulary and which
    #: sections of the product are meaningful for it.
    account_type: str


class ProfileUpdateRequest(BaseModel):
    full_name: str = Field(min_length=1)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)
