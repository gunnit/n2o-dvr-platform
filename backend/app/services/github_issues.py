"""Mirror user feedback to GitHub Issues.

Every row inserted into `user_feedback` gets a matching issue opened in
`settings.GITHUB_REPO`. The team triages from GitHub; when an item is
ready for an autonomous fix, a maintainer manually `@claude`-mentions the
issue (we do NOT auto-add a `claude-ready` label here — the human stays
in the loop on what's safe to delegate).

Contract:
- Failures are logged and swallowed. The feedback POST must succeed even
  if GitHub is down, the token is missing, or the repo is unreachable.
- All calls are async via httpx so the FastAPI handler doesn't block.
- The caller is responsible for persisting (number, url) back to the row.
"""

from __future__ import annotations

import logging
from typing import Literal

import httpx

from app.config import settings
from app.models.user_feedback import UserFeedback

log = logging.getLogger(__name__)

_GITHUB_API = "https://api.github.com"

_TYPE_LABEL = {
    "bug": "bug",
    "idea": "enhancement",
    "observation": "observation",
}


def _is_configured() -> bool:
    return bool(settings.GITHUB_TOKEN and settings.GITHUB_REPO)


def _headers() -> dict[str, str]:
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {settings.GITHUB_TOKEN}",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _build_body(fb: UserFeedback, user_label: str | None) -> str:
    """Render the issue body. Plain markdown — no secrets, no PII."""
    route = fb.route or "—"
    page = fb.page_url or "—"
    submitter = user_label or "—"
    ua = fb.user_agent or "—"
    return (
        f"**Tipo:** {fb.type}\n"
        f"**Inviato da:** {submitter}\n"
        f"**Route:** `{route}`\n"
        f"**Pagina:** {page}\n"
        f"**User agent:** `{ua}`\n"
        f"**Feedback ID:** `{fb.id}`\n\n"
        f"---\n\n"
        f"{fb.description}\n\n"
        f"---\n"
        f"_Aperto automaticamente da DVR Sicurezza. "
        f"Menziona `@claude` quando è pronto per il fix automatico._"
    )


def _build_title(fb: UserFeedback) -> str:
    """Take the first non-empty line, cap to ~80 chars."""
    first = next(
        (line.strip() for line in fb.description.splitlines() if line.strip()),
        "(senza descrizione)",
    )
    if len(first) > 80:
        first = first[:77].rstrip() + "..."
    prefix = {"bug": "Bug", "idea": "Idea", "observation": "Osservazione"}.get(
        fb.type, "Feedback"
    )
    return f"[{prefix}] {first}"


async def create_issue_from_feedback(
    fb: UserFeedback, user_label: str | None
) -> tuple[int | None, str | None]:
    """Open a GitHub issue mirroring this feedback row.

    Returns (issue_number, html_url) on success, (None, None) otherwise.
    Never raises — caller can blindly write the result to the row.
    """
    if not _is_configured():
        log.debug("github_issues: not configured (no token), skipping mirror")
        return None, None

    labels = list(settings.GITHUB_FEEDBACK_LABELS)
    type_label = _TYPE_LABEL.get(fb.type)
    if type_label and type_label not in labels:
        labels.append(type_label)

    payload = {
        "title": _build_title(fb),
        "body": _build_body(fb, user_label),
        "labels": labels,
    }

    url = f"{_GITHUB_API}/repos/{settings.GITHUB_REPO}/issues"
    try:
        async with httpx.AsyncClient(timeout=settings.GITHUB_API_TIMEOUT_SECONDS) as client:
            resp = await client.post(url, json=payload, headers=_headers())
    except httpx.HTTPError as exc:
        log.warning("github_issues: request failed for feedback %s: %s", fb.id, exc)
        return None, None

    if resp.status_code >= 300:
        log.warning(
            "github_issues: %s returned %s for feedback %s: %s",
            url,
            resp.status_code,
            fb.id,
            resp.text[:300],
        )
        return None, None

    data = resp.json()
    number = data.get("number")
    html_url = data.get("html_url")
    if not isinstance(number, int) or not isinstance(html_url, str):
        log.warning(
            "github_issues: unexpected response shape for feedback %s: %r",
            fb.id,
            data,
        )
        return None, None
    log.info("github_issues: opened #%s for feedback %s", number, fb.id)
    return number, html_url


CloseReason = Literal["completed", "not_planned"]


async def close_issue(issue_number: int, reason: CloseReason) -> None:
    """Close a mirrored issue. Best-effort, never raises.

    `completed` for `risolto`, `not_planned` for `non_fara`.
    """
    if not _is_configured():
        return

    url = f"{_GITHUB_API}/repos/{settings.GITHUB_REPO}/issues/{issue_number}"
    payload = {"state": "closed", "state_reason": reason}
    try:
        async with httpx.AsyncClient(timeout=settings.GITHUB_API_TIMEOUT_SECONDS) as client:
            resp = await client.patch(url, json=payload, headers=_headers())
    except httpx.HTTPError as exc:
        log.warning("github_issues: close failed for #%s: %s", issue_number, exc)
        return

    if resp.status_code >= 300:
        log.warning(
            "github_issues: close #%s returned %s: %s",
            issue_number,
            resp.status_code,
            resp.text[:300],
        )
        return
    log.info("github_issues: closed #%s as %s", issue_number, reason)


async def reopen_issue(issue_number: int) -> None:
    """Reopen a previously-closed mirrored issue. Best-effort, never raises."""
    if not _is_configured():
        return

    url = f"{_GITHUB_API}/repos/{settings.GITHUB_REPO}/issues/{issue_number}"
    try:
        async with httpx.AsyncClient(timeout=settings.GITHUB_API_TIMEOUT_SECONDS) as client:
            resp = await client.patch(
                url, json={"state": "open"}, headers=_headers()
            )
    except httpx.HTTPError as exc:
        log.warning("github_issues: reopen failed for #%s: %s", issue_number, exc)
        return

    if resp.status_code >= 300:
        log.warning(
            "github_issues: reopen #%s returned %s: %s",
            issue_number,
            resp.status_code,
            resp.text[:300],
        )
