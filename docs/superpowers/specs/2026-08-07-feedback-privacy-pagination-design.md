# Feedback Privacy and Complete Admin Queue Design

## Context

Production evidence on 2026-08-07 identified two independent defects in the feedback subsystem.

1. Automatic GitHub mirrors publish user-controlled feedback text plus submitter, route, page URL, user-agent, and feedback identifiers into the public `gunnit/n2o-dvr-platform` repository.
2. The admin feedback page requests the API default of 100 rows, while the accessible production tenant currently has 148 rows. The rendered counters therefore omit older rows, including two `in_revisione` reports.

The product database remains the feedback source of truth. GitHub is only a best-effort notification and state-sync channel.

## Goals

- Preserve GitHub notification creation, type labels, returned issue number/URL, and later close/reopen synchronization.
- Guarantee that no feedback description, person label, email, user agent, resource route, page URL, query string, fragment, or feedback identifier enters a new GitHub issue payload.
- Load every row available to the tenant-scoped admin endpoint and render accurate status counts.
- Keep the API schema, database schema, authorization model, and feedback status semantics unchanged.

## Non-goals

- Do not rewrite or delete historical GitHub issue bodies in this change.
- Do not repair the currently failing GitHub credential or infer missing production feedback from GitHub.
- Do not add a cross-tenant product API or weaken organization scoping.
- Do not implement product-domain requests contained in feedback.

## Approaches considered

### GitHub mirror

1. **Generic notification payload (selected).** Publish only a type-derived title/body and configured labels. This retains workflow and status synchronization while creating a structural privacy boundary.
2. Disable mirroring. Safest for disclosure, but removes the existing notification workflow even after credentials are repaired.
3. Regex-redact the current payload. Rejected because arbitrary Italian text can contain identity, health, employment, and company data that pattern matching cannot reliably identify.

### Admin pagination

1. **Client-side complete pagination (selected).** Reuse the existing endpoint in 500-row batches, deduplicate by ID, and stop on a short page. It is the smallest compatible change and needs no backend migration.
2. Add a new aggregate backend endpoint. Rejected as unnecessary API surface for the current volume.
3. Fetch each status separately. Rejected because it multiplies requests and complicates the page while still relying on offset pagination.

## Design

`backend/app/services/github_issues.py` will derive public issue text from `fb.type` only. `_build_title(feedback_type)` and `_build_body(feedback_type)` will never accept a `UserFeedback` object or a user label. `create_issue_from_feedback(fb)` will continue using the full object privately for type-label selection, request correlation in private logs, and persistence of the returned issue number and URL. The API caller will stop passing `user.full_name or user.email`.

`frontend/src/app/(dashboard)/admin/feedback/feedback-pagination.ts` will export `fetchAllFeedback(apiFetch)`. It will call `/api/v1/feedback?limit=500&offset=N`, preserve newest-first order, retain the first occurrence of each ID, and terminate only when a page contains fewer than 500 rows. The page's existing load function will call this helper. API failures continue to flow to the existing visible error state.

## Privacy and error behavior

- Public GitHub content contains fixed Italian notification copy plus a validated type label only.
- Configured GitHub labels remain unchanged; network and 4xx failures remain best-effort and cannot roll back the committed database row.
- Pagination propagates a failed page request instead of showing a partial queue as complete.
- Deduplication protects the rendered table from overlap if rows are inserted while offset pagination is in progress.

## Verification

- A backend regression test sends unique private markers through every previously mirrored field and proves none occur in the outbound JSON payload.
- Existing GitHub transport, no-token, 4xx, network-error, close, and reopen behavior remains covered.
- A frontend unit test returns one full 500-row page plus a short overlapping page, proves both offsets are requested, proves the newest duplicate wins, and proves 501 unique rows are returned.
- Run focused tests first, then the complete backend suite, frontend unit suite, TypeScript check, lint, and production build.
- After deployment, verify exact SHA on API, worker, and frontend; confirm the admin page renders all 148 accessible rows with 29 `nuovo` and 3 `in_revisione`; inspect post-deploy logs for new errors or 5xx responses.
