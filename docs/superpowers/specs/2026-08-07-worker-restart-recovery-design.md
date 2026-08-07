# Worker Restart Recovery Design

## Context

Production evidence on 2026-08-06 shows a 17-document batch accepted by the API at 09:54:13 UTC. Fourteen tasks completed before an abrupt worker restart at 09:54:34, and one reserved task was redelivered after the Redis visibility timeout and completed. The two tasks already executing on the worker's two concurrency slots emitted no terminal task event. Their DUVRI and PEE Comune database rows still read `in_progress`, with no file, error, or completion timestamp.

The deployed task uses Celery's default early acknowledgement (`acks_late=False`). An executing message is therefore removed before document generation finishes. A worker exit loses that message, while a merely reserved message remains unacknowledged and is eventually redelivered. This exactly matches the observed split.

## Goals

- Keep an executing document message recoverable if its worker process exits before the task returns.
- Requeue a task promptly when Celery identifies an abruptly lost child process.
- Make redelivery after a successful database commit repair the idempotent company meter without generating or uploading the document again.
- Bound automatic generator entry to the initial delivery plus one recovery, including hard-timeout redeliveries.
- Recover the two already-stranded production rows through the fixed task path and verify their terminal state.

## Non-goals

- Do not change billing rules, generation content, queue topology, Redis retention, or document fields other than the narrow attempt counter.
- Do not add unbounded automatic retries for ordinary generator or database exceptions.
- Do not create replacement document versions for the two stranded rows.
- Do not alter successful historical files.

## Approaches considered

1. **Migration-first attempt counter, late acknowledgement, worker-loss rejection, bounded hard-timeout replay, and terminal metering repair (selected).** This preserves an interrupted message, prevents a poison document from looping forever, and closes the post-document-commit/pre-metering crash window without regenerating a completed file.
2. Periodically sweep all `in_progress` rows. Rejected as broader operational machinery that cannot distinguish active long-running work without a lease protocol.
3. Reset stranded rows to `bozza` only. Rejected because it repairs today's rows but leaves the message-loss cause in place and requires manual regeneration.
4. Add a database execution lease. Rejected for this incident because the Redis visibility timeout is longer than the task hard limit, so normal execution cannot overlap its redelivery; that broader state machine would add disproportionate rollout and rollback risk.

## Design

The first release stage adds `documenti_generati.generation_attempts` as a non-null integer with a server default of `0`. The database migration must reach `live` before the API and worker map the column: Render can deploy those services in parallel. The change is additive, defaults both existing and new rows, and bounds its PostgreSQL lock wait to five seconds.

The `generate_document_task` decorator will set:

- `acks_late=True`, so Redis retains ownership of the message until the task returns;
- `reject_on_worker_lost=True`, so an abruptly lost Celery child rejects rather than acknowledges the message;
- `acks_on_failure_or_timeout=False`, so a hard timeout is not treated as successfully delivered.

Redis can still delay redelivery after a whole service restart until its visibility timeout. That is acceptable for durability and matches the already-observed one-hour redelivery. The existing 660-second hard limit is well below that timeout, preventing a normal task from being redelivered while still executing.

Before generator dispatch, `_run_generation` increments `generation_attempts` and commits it with the `in_progress` state. Values `0` and `1` therefore permit the initial entry and one recovery entry. A later delivery that reads `2` does not enter generator, snapshot, Drive, or metering code: it restores `bozza`, clears partial file fields, records a safe interruption message and completion timestamp, and commits so an operator can create a fresh version manually.

When the persisted document is already `completed` or legacy `ready`, the task calls the existing idempotent `record_activation_for_azienda` boundary and returns without mutating or regenerating the document. This covers both worker exit after the document commit but before late acknowledgement and the narrower crash window before the original metering call. The meter's composite key makes replay a no-op when the activation already exists.

The recovery operation will enqueue the two existing row IDs, not create new versions or edit their content. The IDs will be resolved through the authorized production path and kept out of reports. Completion is established only when both original rows become `completed` with non-empty files and the worker logs show terminal success on the new exact SHA.

## Failure and rollback behavior

- Expected generator failures retain the existing `bozza` rollback and friendly error behavior; the task returns normally and the late acknowledgement completes.
- A hard worker loss or hard timeout leaves the message recoverable. Celery/Redis may redeliver it later, and the existing row is reused once; a subsequent delivery restores it to `bozza` instead of looping.
- If the release causes harmful queue behavior, the code commit is independently reversible. A rollback to the previous worker is schema-compatible, but already-requeued messages must be observed before rollback because the previous code early-acknowledges them.

## Verification

- A migration/model regression verifies the integer, non-null, client default and server-default contract on both sides of the staged rollout.
- A regression asserts the registered Celery task has late acknowledgement, worker-loss rejection, and failure/timeout acknowledgement disabled.
- Async regressions prove attempts `0` and `1` are incremented and committed before generator dispatch, while attempt `2` returns to `bozza` without generator, snapshot, Drive, or meter side effects.
- Terminal-row regressions prove both `completed` and legacy `ready` preserve the file, skip generation and Drive, and replay metering exactly once.
- Run the focused task suite, billing-dispatch invariant tests, and the complete backend suite.
- After exact-SHA deployment, enqueue the two original stranded rows once, poll them to terminal state, verify files exist, and inspect worker/API/database/Redis logs for the original signature, duplicate generation, failed jobs, database failures, or new 5xx responses.
