"""Seed demo operator users for the ACME Meccanica demo org.

The /api/v1/auth/register endpoint only creates admin users. This script
adds the two operator roles used by the user stories so the demo can
exercise role-gated flows.

Run after the ACME fixture:
    python -m app.db.fixtures.acme_meccanica
    python -m scripts.seed_demo_users

Idempotent — re-running skips users that already exist.
"""

import asyncio
import logging
import sys

from passlib.context import CryptContext
from sqlalchemy import select

from app.db.session import async_session_factory
from app.models.organization import Organization
from app.models.user import User

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ORG_NAME = "N2O SRL (demo)"

DEMO_USERS = [
    (
        "ufficio@acme-meccanica.test",
        "Ufficio2026!",
        "Maria Ufficio (demo)",
        "operatore_ufficio",
    ),
    (
        "campo@acme-meccanica.test",
        "Campo2026!",
        "Paolo Campo (demo)",
        "operatore_campo",
    ),
]


async def main() -> int:
    async with async_session_factory() as session:
        org = (
            await session.execute(
                select(Organization).where(Organization.name == ORG_NAME)
            )
        ).scalar_one_or_none()
        if org is None:
            log.error(
                "Organization %r not found. Run the ACME fixture first: "
                "python -m app.db.fixtures.acme_meccanica",
                ORG_NAME,
            )
            return 1

        for email, password, full_name, role in DEMO_USERS:
            exists = (
                await session.execute(select(User).where(User.email == email))
            ).scalar_one_or_none()
            if exists:
                log.info("skip  %s (already present, role=%s)", email, exists.role)
                continue
            session.add(
                User(
                    organization_id=org.id,
                    email=email,
                    hashed_password=pwd_context.hash(password),
                    full_name=full_name,
                    role=role,
                )
            )
            log.info("create %-35s  role=%s  password=%s", email, role, password)

        await session.commit()

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
