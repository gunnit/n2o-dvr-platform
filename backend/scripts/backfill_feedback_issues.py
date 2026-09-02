"""Open GitHub issues for segnalazioni whose mirror never landed.

`POST /feedback` mirrors each row to a GitHub issue best-effort: the
submission succeeds whether or not GitHub answers. That is the right call
for the operator — nobody should lose a bug report because a token
expired — but it means a dead token drains straight into a gap that
nothing else reports.

That is exactly what happened. `GITHUB_TOKEN` started answering 401 after
2026-06-10, and every segnalazione from then on was stored with
`github_issue_number IS NULL`. The team triages from the repo, so those
rows were invisible: 38 of them arrived in August alone and none reached
the board.

This script closes that gap after the token is rotated. It walks the rows
with no `github_issue_number` oldest-first, opens one issue each through
the *same* `github_issues.create_issue_from_feedback` the API uses, and
writes the number and URL back.

    python -m scripts.backfill_feedback_issues              # dry run (default)
    python -m scripts.backfill_feedback_issues --apply      # really open issues
    python -m scripts.backfill_feedback_issues --apply --since 2026-07-01
    python -m scripts.backfill_feedback_issues --apply --limit 10

**Creates public GitHub issues — a dry run is the default on purpose.**
Check the count first, and rotate the token before `--apply`: with a bad
token every call 401s, the script reports the failures and writes nothing,
so a premature run is loud but harmless.

The issue body carries no feedback text and no identity — the mirror is a
generic "nuova segnalazione" notification (see `github_issues._build_body`)
and this script inherits that, so backfilling cannot leak content that the
live path keeps private.

Idempotent: a row that gets a number is skipped on the next run. Failures
are left NULL and retried next time. Rate-limit friendly — GitHub's issue
creation is throttled, so calls are spaced by `--delay` (default 1.0s) and
the script stops early on a credential failure rather than burning through
the whole backlog against a bad token.
"""

import argparse
import asyncio
import logging
import sys
from datetime import date, datetime

from sqlalchemy import select

from app.db.session import async_session_factory
from app.models.user_feedback import UserFeedback
from app.services import github_issues

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)


async def backfill(
    apply: bool = False,
    since: date | None = None,
    limit: int | None = None,
    delay: float = 1.0,
) -> int:
    if not github_issues._is_configured():
        log.error(
            "GITHUB_TOKEN / GITHUB_REPO not configured — nothing to back fill into."
        )
        return 1

    async with async_session_factory() as db:
        stmt = (
            select(UserFeedback)
            .where(UserFeedback.github_issue_number.is_(None))
            .order_by(UserFeedback.created_at)
        )
        if since is not None:
            stmt = stmt.where(
                UserFeedback.created_at >= datetime.combine(since, datetime.min.time())
            )
        if limit is not None:
            stmt = stmt.limit(limit)

        rows = list((await db.execute(stmt)).scalars().all())

        if not rows:
            log.info("Nothing to back fill — every segnalazione has an issue.")
            return 0

        log.info(
            "%d segnalazioni without a GitHub issue (%s .. %s)",
            len(rows),
            rows[0].created_at.date(),
            rows[-1].created_at.date(),
        )

        if not apply:
            for fb in rows:
                log.info(
                    "  WOULD MIRROR %s  %s  %s  status=%s",
                    fb.created_at.strftime("%Y-%m-%d %H:%M"),
                    fb.type.ljust(11),
                    fb.id,
                    fb.status,
                )
            log.info("Dry run — re-run with --apply to open these issues.")
            return 0

        created = 0
        failed = 0
        for i, fb in enumerate(rows):
            number, html_url = await github_issues.create_issue_from_feedback(fb)
            if number is None:
                failed += 1
                log.warning("  FAILED  %s (left for the next run)", fb.id)
                # A credential failure fails identically for every remaining
                # row. Stop rather than emit hundreds of identical errors.
                if failed >= 3 and created == 0:
                    log.error(
                        "3 consecutive failures with nothing created — aborting. "
                        "Check GITHUB_TOKEN, then re-run."
                    )
                    break
                continue

            fb.github_issue_number = number
            fb.github_issue_url = html_url
            await db.commit()
            created += 1
            log.info("  #%-5s %s  %s", number, fb.created_at.date(), fb.id)

            if delay and i < len(rows) - 1:
                await asyncio.sleep(delay)

        log.info("Backfill complete: %d created, %d failed.", created, failed)
        return 0 if failed == 0 else 1


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="actually open the issues (default is a dry run)",
    )
    parser.add_argument(
        "--since",
        type=_parse_date,
        metavar="YYYY-MM-DD",
        help="only back fill segnalazioni created on or after this date",
    )
    parser.add_argument(
        "--limit", type=int, help="stop after this many rows (useful for a smoke test)"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="seconds between issue creations (default 1.0)",
    )
    args = parser.parse_args()
    return asyncio.run(
        backfill(
            apply=args.apply, since=args.since, limit=args.limit, delay=args.delay
        )
    )


if __name__ == "__main__":
    sys.exit(main())
