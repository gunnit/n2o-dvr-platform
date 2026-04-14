"""
Database seeding script for reference data.

Seeds the database with:
- Risk categories and their standard hazard items
- Environment types with default risk applicability
- Document type metadata

Run with: python -m app.db.seed

Note: This script seeds reference data that is used by the survey form
and document generation engine. It does NOT create sample company data.
The risk categories and hazard items are extracted from N2O's real
template documents (see docs/context/REFERENCE_DATA.md).
"""

import asyncio
import logging
import uuid

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_factory, engine
from app.db.base import Base
from app.services.reference_data import (
    DOCUMENT_TYPES,
    ENVIRONMENT_TYPES,
    HAZARD_LIBRARY,
    RISK_CATEGORIES,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def seed_reference_tables(session: AsyncSession) -> None:
    """Seed all reference data tables.

    This function is idempotent — it checks for existing data before
    inserting and can be safely re-run.
    """
    logger.info("Starting reference data seeding...")

    await _seed_risk_categories(session)
    await _seed_environment_types(session)
    await _seed_document_types(session)

    await session.commit()
    logger.info("Reference data seeding complete.")


async def _seed_risk_categories(session: AsyncSession) -> None:
    """Seed risk categories and their standard hazard items.

    Inserts into: categorie_rischio, pericoli_standard (if tables exist).
    Falls back to logging the data if tables don't exist yet.
    """
    logger.info("Seeding risk categories...")

    # Check if the reference tables exist
    try:
        result = await session.execute(
            text(
                "SELECT EXISTS ("
                "  SELECT FROM information_schema.tables "
                "  WHERE table_name = 'categorie_rischio'"
                ")"
            )
        )
        table_exists = result.scalar()
    except Exception:
        table_exists = False

    if table_exists:
        # Check if data already exists
        result = await session.execute(
            text("SELECT COUNT(*) FROM categorie_rischio")
        )
        count = result.scalar()
        if count > 0:
            logger.info(
                f"  Risk categories already seeded ({count} rows). Skipping."
            )
            return

        for rc in RISK_CATEGORIES:
            await session.execute(
                text(
                    "INSERT INTO categorie_rischio "
                    "(id, numero, macro_categoria, categoria, field_key) "
                    "VALUES (:id, :numero, :macro, :cat, :fk)"
                ),
                {
                    "id": str(uuid.uuid4()),
                    "numero": rc["numero"],
                    "macro": rc["macro_categoria"],
                    "cat": rc["categoria"],
                    "fk": rc["field_key"],
                },
            )

        logger.info(f"  Inserted {len(RISK_CATEGORIES)} risk categories.")

        # Seed standard hazards
        hazard_count = 0
        for cat_name, hazards in HAZARD_LIBRARY.items():
            for idx, hazard in enumerate(hazards, 1):
                await session.execute(
                    text(
                        "INSERT INTO pericoli_standard "
                        "(id, categoria, ordine, descrizione) "
                        "VALUES (:id, :cat, :ordine, :desc)"
                    ),
                    {
                        "id": str(uuid.uuid4()),
                        "cat": cat_name,
                        "ordine": idx,
                        "desc": hazard,
                    },
                )
                hazard_count += 1

        logger.info(f"  Inserted {hazard_count} standard hazard items.")
    else:
        logger.info(
            "  Table 'categorie_rischio' not found. "
            "Run migrations first, then re-run seeding."
        )
        logger.info(f"  Would seed {len(RISK_CATEGORIES)} risk categories:")
        for rc in RISK_CATEGORIES:
            hazard_count = len(HAZARD_LIBRARY.get(rc["categoria"], []))
            logger.info(
                f"    {rc['numero']}. {rc['categoria']} "
                f"({rc['macro_categoria']}) — {hazard_count} hazards"
            )


async def _seed_environment_types(session: AsyncSession) -> None:
    """Seed environment type reference data."""
    logger.info("Seeding environment types...")

    try:
        result = await session.execute(
            text(
                "SELECT EXISTS ("
                "  SELECT FROM information_schema.tables "
                "  WHERE table_name = 'tipi_ambiente'"
                ")"
            )
        )
        table_exists = result.scalar()
    except Exception:
        table_exists = False

    if table_exists:
        result = await session.execute(
            text("SELECT COUNT(*) FROM tipi_ambiente")
        )
        count = result.scalar()
        if count > 0:
            logger.info(
                f"  Environment types already seeded ({count} rows). Skipping."
            )
            return

        for env_type in ENVIRONMENT_TYPES:
            await session.execute(
                text(
                    "INSERT INTO tipi_ambiente (id, nome) "
                    "VALUES (:id, :nome)"
                ),
                {"id": str(uuid.uuid4()), "nome": env_type},
            )

        logger.info(f"  Inserted {len(ENVIRONMENT_TYPES)} environment types.")
    else:
        logger.info(
            "  Table 'tipi_ambiente' not found. "
            "Run migrations first, then re-run seeding."
        )
        logger.info(f"  Would seed {len(ENVIRONMENT_TYPES)} environment types:")
        for env_type in ENVIRONMENT_TYPES:
            logger.info(f"    - {env_type}")


async def _seed_document_types(session: AsyncSession) -> None:
    """Seed document type metadata."""
    logger.info("Seeding document types...")

    try:
        result = await session.execute(
            text(
                "SELECT EXISTS ("
                "  SELECT FROM information_schema.tables "
                "  WHERE table_name = 'tipi_documento'"
                ")"
            )
        )
        table_exists = result.scalar()
    except Exception:
        table_exists = False

    if table_exists:
        result = await session.execute(
            text("SELECT COUNT(*) FROM tipi_documento")
        )
        count = result.scalar()
        if count > 0:
            logger.info(
                f"  Document types already seeded ({count} rows). Skipping."
            )
            return

        for key, meta in DOCUMENT_TYPES.items():
            await session.execute(
                text(
                    "INSERT INTO tipi_documento "
                    "(id, chiave, nome, abbreviazione, fase, complessita, template_disponibile) "
                    "VALUES (:id, :chiave, :nome, :abbr, :fase, :compl, :tmpl)"
                ),
                {
                    "id": str(uuid.uuid4()),
                    "chiave": key,
                    "nome": meta["nome"],
                    "abbr": meta["abbreviazione"],
                    "fase": meta["fase"],
                    "compl": meta["complessita"],
                    "tmpl": meta["template_disponibile"],
                },
            )

        logger.info(f"  Inserted {len(DOCUMENT_TYPES)} document types.")
    else:
        logger.info(
            "  Table 'tipi_documento' not found. "
            "Run migrations first, then re-run seeding."
        )
        logger.info(f"  Would seed {len(DOCUMENT_TYPES)} document types:")
        for key, meta in DOCUMENT_TYPES.items():
            logger.info(f"    - {key}: {meta['nome']}")


async def main() -> None:
    """Run the seeding script."""
    logger.info("=" * 60)
    logger.info("N2O DVR — Database Seeding Script")
    logger.info("=" * 60)

    async with async_session_factory() as session:
        await seed_reference_tables(session)

    logger.info("Done.")


if __name__ == "__main__":
    asyncio.run(main())
