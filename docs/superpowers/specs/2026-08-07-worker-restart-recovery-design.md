# Worker Restart Recovery Design

## Context

Production evidence on 2026-08-06 shows a 17-document batch accepted by the API at 09:54:13 UTC. Fourteen tasks completed before an abrupt worker restart at 09:54:34, and one reserved task was redelivered after the Redis visibility timeout and completed. The two tasks already executing on the worker's two concurrency slots emitted no terminal task event. Their DUVRI and PEE Comune database rows still read `in_progress`, with no file, error, or completion timestamp.

The deployed task uses Celery's default early acknowledgement (`acks_late=False`). An executing message is therefore removed before document generation finishes. A worker exit loses that message, while a merely reserved message remains unacknowledged and is eventually redelivered. This exactly matches the observed split.

## Goals

- Keep an executing document message recoverable if its worker process exits before the task returns.
- Requeue a task promptly when Celery identifies an abruptly lost child process.
- Make redelivery after a successful database commit a safe no-op instead of generating and uploading the same document again.
- Recover the two already-stranded production rows through the fixed task path and verify their terminal state.

## Non-goals

- Do not change document schemas, billing rules, generation content, queue topology, or Redis retention.
- Do not add unbounded automatic retries for ordinary generator or database exceptions.
- Do not create replacement document versions for the two stranded rows.
- Do not alter successful historical files.

## Approaches considered

1. **Late acknowledgement plus worker-loss rejection and a completed-row guard (selected).** This addresses the observed message-loss boundary with task-local configuration and makes the principal post-commit redelivery case idempotent.
2. Periodically sweep all `in_progress` rows. Rejected as broader operational machinery that cannot distinguish active long-running work without a lease protocol.
3. Reset stranded rows to `bozza` only. Rejected because it repairs today's rows but leaves the message-loss cause in place and requires manual regeneration.
4. Add a database execution-lease migration. Rejected for this incident because the Redis visibility timeout is longer than the task hard limit, so normal execution cannot overlap its redelivery; a schema change would add disproportionate rollout and rollback risk.

## Design

The `generate_document_task` decorator will set:

- `acks_late=True`, so Redis retains ownership of the message until the task returns;
- `reject_on_worker_lost=True`, so an abruptly lost Celery child rejects rather than acknowledges the message.

Redis can still delay redelivery after a whole service restart until its visibility timeout. That is acceptable for durability and matches the already-observed one-hour redelivery. The existing 660-second hard limit is well below that timeout, preventing a normal task from being redelivered while still executing.

`_run_generation` will return immediately when the persisted document is already `completed` or legacy `ready`. This covers a worker exit after the completion commit but before the late acknowledgement. Pending, `in_progress`, and `bozza` rows still run, allowing a genuinely interrupted row to recover on redelivery.

The recovery operation will enqueue the two existing row IDs, not create new versions or edit their content. The IDs will be resolved through the authorized production path and kept out of reports. Completion is established only when both original rows become `completed` with non-empty files and the worker logs show terminal success on the new exact SHA.

## Failure and rollback behavior

- Expected generator failures retain the existing `bozza` rollback and friendly error behavior; the task returns normally and the late acknowledgement completes.
- A hard worker loss leaves the message recoverable. Celery/Redis may redeliver it later, and the existing row is reused.
- If the release causes harmful queue behavior, the code commit is independently reversible. A rollback to the previous worker is schema-compatible, but already-requeued messages must be observed before rollback because the previous code early-acknowledges them.

## Verification

- A regression asserts the registered Celery task has both late acknowledgement and worker-loss rejection enabled; it fails on the deployed defaults.
- An async regression supplies a persisted completed document and proves `_run_generation` does not call a generator, commit, meter, upload, or mutate the row.
- Run the focused task suite, billing-dispatch invariant tests, and the complete backend suite.
- After exact-SHA deployment, enqueue the two original stranded rows once, poll them to terminal state, verify files exist, and inspect worker/API/database/Redis logs for the original signature, duplicate generation, failed jobs, database failures, or new 5xx responses.
