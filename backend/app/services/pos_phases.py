"""POS phase graph + ordering helpers (US-4.7).

The phase list lives in the ``pos.fasi_lavorative`` JSONB column. This
module owns the rules that must hold for the column:

* every phase ``id`` is unique
* every ``dipende_da`` entry resolves to a known phase id
* no phase depends on itself
* no cycle exists in the dependency graph (otherwise the Gantt-like
  overview and the "this phase starts after ..." narrative in the .docx
  would be nonsense)
* after ordering by ``ordine``, a phase's dependencies all precede it
  (so the drag-drop is kept consistent with the declared dependencies).

The validator raises ``PosPhaseError`` with an Italian operator-facing
message — the API layer surfaces this verbatim as HTTP 400.
"""

from __future__ import annotations

from collections import deque

from app.schemas.pos_phase import PosPhase


class PosPhaseError(ValueError):
    """Raised when the phase list violates the structural rules."""


def _topological_cycle(phases: list[PosPhase]) -> str | None:
    """Return the name of a phase that participates in a cycle, else None.

    Classic Kahn's algorithm: seed the queue with phases that have no
    incoming edges, peel them off, and check whether any phase remains
    unvisited at the end. Names rather than ids are returned because
    the error message goes to a safety consultant, not a developer.
    """
    indegree: dict[str, int] = {p.id: 0 for p in phases}
    edges: dict[str, list[str]] = {p.id: [] for p in phases}
    name_by_id: dict[str, str] = {p.id: p.nome for p in phases}

    for p in phases:
        for dep in p.dipende_da:
            # Skip unknown deps — they're caught by ``validate_phases`` earlier.
            if dep not in indegree:
                continue
            # Edge: dep -> p (dep must come first).
            edges[dep].append(p.id)
            indegree[p.id] += 1

    q: deque[str] = deque([pid for pid, deg in indegree.items() if deg == 0])
    visited = 0
    while q:
        cur = q.popleft()
        visited += 1
        for nxt in edges[cur]:
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                q.append(nxt)

    if visited == len(phases):
        return None
    # Pick any unvisited phase to name in the error.
    for pid, deg in indegree.items():
        if deg > 0:
            return name_by_id[pid]
    return None  # unreachable


def validate_phases(phases: list[PosPhase]) -> None:
    """Raise ``PosPhaseError`` if the phase list is inconsistent.

    Pure function — callers persist only after this returns. Runs in
    ``O(n + edges)`` time so it's cheap even for deep phase graphs.
    """
    ids = [p.id for p in phases]
    if len(set(ids)) != len(ids):
        raise PosPhaseError("Identificativo di fase duplicato nella lista")

    id_set = set(ids)
    for p in phases:
        for dep in p.dipende_da:
            if dep == p.id:
                raise PosPhaseError(
                    f"La fase '{p.nome}' non può dipendere da se stessa"
                )
            if dep not in id_set:
                raise PosPhaseError(
                    f"La fase '{p.nome}' dipende da una fase inesistente ({dep})"
                )

    cycle_name = _topological_cycle(phases)
    if cycle_name is not None:
        raise PosPhaseError(
            f"Dipendenze cicliche rilevate attorno alla fase '{cycle_name}'. "
            "Rivedi le precedenze."
        )


def normalize_ordering(phases: list[PosPhase]) -> list[PosPhase]:
    """Return the phases sorted by ``ordine`` with the field renumbered 0..n-1.

    The frontend is free to leave gaps in ``ordine`` (e.g. after
    deleting a middle phase). We renumber server-side so the persisted
    JSONB stays dense and predictable. Stable sort preserves insertion
    order when ``ordine`` values collide.
    """
    sorted_phases = sorted(phases, key=lambda p: p.ordine)
    # Rebuild each object with the canonical ordine so the stored JSON
    # and any subsequent .model_dump() match the printed document.
    return [
        p.model_copy(update={"ordine": i})
        for i, p in enumerate(sorted_phases)
    ]


def dependency_violations_after_ordering(
    phases: list[PosPhase],
) -> list[tuple[str, str]]:
    """After ordering, list ``(dependent_name, missing_predecessor_name)`` pairs.

    Called by the generator to decorate the Gantt-like overview table
    with a "precedenza non rispettata" footnote when an operator drags
    a phase before one of its declared dependencies. We do not refuse
    the save — the operator may have a reason — but the docx output
    makes the inconsistency visible.
    """
    ordered = sorted(phases, key=lambda p: p.ordine)
    position: dict[str, int] = {p.id: i for i, p in enumerate(ordered)}
    name_by_id: dict[str, str] = {p.id: p.nome for p in ordered}

    violations: list[tuple[str, str]] = []
    for p in ordered:
        for dep in p.dipende_da:
            if dep not in position:
                continue
            if position[dep] >= position[p.id]:
                violations.append((p.nome, name_by_id[dep]))
    return violations
