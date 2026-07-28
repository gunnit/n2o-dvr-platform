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


class ProfileUpdateRequest(BaseModel):
    full_name: str = Field(min_length=1)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)
