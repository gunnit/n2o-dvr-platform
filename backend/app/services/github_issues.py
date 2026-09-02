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


def _log_http_failure(operation: str, resp: httpx.Response, context: str) -> None:
    """Report a non-2xx mirror response at a severity that matches the cause.

    A 401/403 is not a transient hiccup: the token is expired, revoked or
    lacks `issues:write`, and it will keep failing for every subsequent
    segnalazione until a human rotates it. Between 2026-06-10 and 2026-08-25
    that happened and nothing surfaced it — the mirror logged at WARNING,
    the POST still returned 201, and 38 segnalazioni were accepted while
    never reaching the board the team triages from. ERROR puts credential
    failures in Render's error feed, where a dead token is noticed in days
    rather than months.

    Everything else (422, 5xx, rate limits) stays a warning: those are
    per-request and the next submission may well succeed.
    """
    detail = resp.text[:300]
    if resp.status_code in (401, 403):
        log.error(
            "github_issues: %s DENIED %s for %s — GITHUB_TOKEN is invalid, expired "
            "or missing issues:write on %s. Feedback is still being saved but is "
            "NOT reaching GitHub; rotate the token and backfill with "
            "scripts/backfill_feedback_issues.py. Response: %s",
            operation,
            resp.status_code,
            context,
            settings.GITHUB_REPO,
            detail,
        )
    else:
        log.warning(
            "github_issues: %s returned %s for %s: %s",
            operation,
            resp.status_code,
            context,
            detail,
        )


def _headers() -> dict[str, str]:
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {settings.GITHUB_TOKEN}",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _feedback_type_label(feedback_type: str) -> str:
    return {"bug": "Bug", "idea": "Idea", "observation": "Osservazione"}.get(
        feedback_type, "Feedback"
    )


def _build_title(feedback_type: str) -> str:
    return f"[{_feedback_type_label(feedback_type)}] Nuova segnalazione DVR"


def _build_body(feedback_type: str) -> str:
    """Render a generic notification without feedback content or identity."""
    label = _feedback_type_label(feedback_type)
    return (
        f"**Tipo:** {label}\n\n"
        "È disponibile una nuova segnalazione nell'area amministrativa Feedback. "
        "Il contenuto non viene copiato su GitHub per tutelare i dati personali e aziendali."
    )


async def create_issue_from_feedback(fb: UserFeedback) -> tuple[int | None, str | None]:
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
        "title": _build_title(fb.type),
        "body": _build_body(fb.type),
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
        _log_http_failure("create", resp, f"feedback {fb.id}")
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
        _log_http_failure("close", resp, f"issue #{issue_number}")
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
        _log_http_failure("reopen", resp, f"issue #{issue_number}")
