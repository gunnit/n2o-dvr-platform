"""The feature map stays true, and the properties it reveals stay pinned.

``docs/qa/feature-map.yaml`` is generated from the app: every route the server
serves, the guards that actually apply to it, and the pages that call it. A
generated inventory is only worth having if something fails when it stops
matching, so:

* :func:`test_manifest_matches_the_code` diffs a fresh render against the
  committed file. Adding, renaming or removing an endpoint fails here until the
  manifest is regenerated and the diff read.
* the rest pin the properties the map *reveals*. The realistic failure mode of
  the first test is someone running ``--write`` to make the build green without
  reading what changed — so the facts that matter (an endpoint with no auth
  dependency, a UI call to a route that does not exist) get their own
  assertions with their own error messages, and regenerating does not silence
  them.

Same spirit as ``test_billing_enforcement.py`` and ``test_permissions.py``:
these read the shape of the codebase, because a missing guard is silent at
runtime and no behavioural test covers an endpoint nobody remembered to write
one for.
"""

from __future__ import annotations

import difflib
import importlib.util
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
GENERATOR = BACKEND / "scripts" / "build_feature_map.py"
MANIFEST = REPO / "docs" / "qa" / "feature-map.yaml"
REGENERATE = "python backend/scripts/build_feature_map.py --write"


def _load_generator():
    """``scripts/`` is not a package, so load the module by path."""
    spec = importlib.util.spec_from_file_location("build_feature_map", GENERATOR)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def generator():
    return _load_generator()


@pytest.fixture(scope="module")
def manifest(generator):
    return generator.build_manifest()


def test_route_collector_descends_modern_fastapi_included_routers(generator):
    from fastapi import APIRouter, FastAPI

    child = APIRouter(prefix="/child")

    @child.get("/ping")
    async def nested_ping():
        return {"ok": True}

    parent = APIRouter(prefix="/api")
    parent.include_router(child)
    probe = FastAPI()
    probe.include_router(parent)

    routes = list(generator._iter_api_routes(probe.routes))

    assert [
        (method, route.path, route.endpoint)
        for route in routes
        for method in sorted(route.methods or set())
        if method not in {"HEAD", "OPTIONS"}
    ] == [("GET", "/api/child/ping", nested_ping)]


# --- the map is current ----------------------------------------------------


def test_manifest_matches_the_code(generator, manifest):
    """A fresh render equals the committed file, byte for byte.

    The failure message is a diff rather than "not equal": the diff *is* the
    review. A new row with an empty ``capabilities`` or ``billing_gates`` is the
    question this file exists to ask, and it is only asked if someone reads it.
    """
    if not (REPO / "frontend" / "src").exists():  # pragma: no cover — backend-only checkout
        pytest.skip("frontend not present; the manifest covers both halves")

    assert MANIFEST.exists(), f"{MANIFEST} is missing — generate it with: {REGENERATE}"

    expected = generator.render(manifest)
    actual = MANIFEST.read_text(encoding="utf-8")
    if actual == expected:
        return

    diff = list(
        difflib.unified_diff(
            actual.splitlines(),
            expected.splitlines(),
            fromfile="docs/qa/feature-map.yaml (committed)",
            tofile="the code as it is now",
            lineterm="",
            n=2,
        )
    )
    shown = "\n".join(diff[:60])
    more = f"\n... and {len(diff) - 60} more diff lines" if len(diff) > 60 else ""
    pytest.fail(
        "the feature map no longer describes the app.\n\n"
        f"{shown}{more}\n\n"
        f"Regenerate with:  {REGENERATE}\n"
        "Then read the diff before committing it — that review is the point."
    )


# --- what the map reveals, pinned ------------------------------------------

#: Endpoints that resolve no auth dependency at all. Every one is deliberate:
#: the two signup paths and login (you cannot hold a token yet), the PayPal
#: webhook (PayPal has no account here — it authenticates by signature inside
#: the handler), and the pure calculators, which take numbers and return
#: numbers without touching a tenant's data.
#:
#: This list is pinned rather than derived so that an endpoint *accidentally*
#: missing its auth dependency fails here. That mistake produces a working
#: endpoint, so nothing else would notice.
EXPECTED_PUBLIC = {
    "POST /api/v1/auth/login",
    "POST /api/v1/auth/register",
    "POST /api/v1/auth/register-direct",
    "POST /api/v1/billing/webhook",
    "GET /api/v1/calculate/biologico-checklist",
    "GET /api/v1/calculate/fire-measures",
    "POST /api/v1/calculate/fire-risk",
    "POST /api/v1/calculate/microclima/phs",
    "POST /api/v1/calculate/microclima/pmv",
    "POST /api/v1/calculate/niosh",
    "GET /api/v1/calculate/niosh-cp",
    "POST /api/v1/calculate/risk-index",
    "POST /api/v1/calculate/stress",
    "GET /api/v1/calculate/stress/indicators",
    "POST /api/v1/calculate/vdt",
    "GET /api/v1/haccp/_meta/activity-types",
}


def test_no_endpoint_becomes_unauthenticated_by_accident(manifest):
    public = set(manifest["review"]["public_endpoints"])
    newly_public = public - EXPECTED_PUBLIC
    assert not newly_public, (
        "endpoint(s) resolve no auth dependency and are reachable without a "
        f"token: {sorted(newly_public)}. If that is intended, add them to "
        "EXPECTED_PUBLIC with the reason; otherwise they are missing a "
        "get_current_user / get_current_org dependency."
    )

    # The other direction is not a security problem, but a stale allowlist
    # hides the next real one.
    no_longer_public = EXPECTED_PUBLIC - public
    assert not no_longer_public, (
        f"EXPECTED_PUBLIC lists endpoint(s) that are no longer public or no "
        f"longer exist: {sorted(no_longer_public)} — prune the list"
    )


#: Write endpoints that deliberately declare no capability. Submitting feedback
#: and editing your own account are things every signed-in person may do, so
#: there is no capability to name — the gate is simply "you are logged in".
#:
#: Everything else that writes must name one. This list was 90 entries until
#: `survey:write` and `assessments:write` were wired onto the sopralluogo and
#: assessment endpoints; keeping it pinned at four is what stops it drifting
#: back to a state where "no guard" and "deliberately open" are indistinguishable.
EXPECTED_UNGUARDED_WRITES = {
    "POST /api/v1/ai-feedback",
    "PATCH /api/v1/auth/me",
    "POST /api/v1/auth/me/change-password",
    "POST /api/v1/feedback",
}


def test_new_write_endpoints_declare_a_capability(manifest):
    unguarded = set(manifest["review"]["unguarded_writes"])
    undeclared = unguarded - EXPECTED_UNGUARDED_WRITES
    assert not undeclared, (
        "write endpoint(s) name no capability, so every role may call them "
        f"regardless of what the matrix says: {sorted(undeclared)}. Add "
        "`dependencies=[Depends(require_capability(...))]`, or add them to "
        "EXPECTED_UNGUARDED_WRITES with the reason they are open to everyone."
    )

    stale = EXPECTED_UNGUARDED_WRITES - unguarded
    assert not stale, (
        f"EXPECTED_UNGUARDED_WRITES lists endpoint(s) that are now gated or "
        f"gone: {sorted(stale)} — prune the list"
    )


def test_survey_and_assessment_capabilities_are_actually_enforced(manifest):
    """The two capabilities the persona split is built on must be load-bearing.

    ``app/core/permissions.py`` describes ``operatore_campo`` as the role that
    collects but does not finalise. That story is only true if the collection
    endpoints actually ask for these capabilities — until they did, narrowing a
    role would have changed precisely nothing, silently.
    """
    from app.core import permissions as perms

    enforced = {cap for e in manifest["endpoints"] for cap in e["capabilities"]}
    for capability in (perms.SURVEY_WRITE, perms.ASSESSMENTS_WRITE):
        assert capability in enforced, (
            f"{capability} is granted by the matrix but no endpoint requires it"
        )


def test_wiring_the_capabilities_did_not_narrow_anyone(manifest):
    """Every survey/assessment endpoint stays reachable by all three roles.

    All three personas hold both capabilities, so adding the guards was meant to
    be behaviour-preserving. If a future edit removes one of these capabilities
    from a role, this test is where that decision surfaces — deliberately, as a
    failure to read rather than a silent change in who can run a sopralluogo.
    """
    from app.core import permissions as perms

    for endpoint in manifest["endpoints"]:
        caps = set(endpoint["capabilities"])
        if not caps <= {perms.SURVEY_WRITE, perms.ASSESSMENTS_WRITE} or not caps:
            continue
        assert set(endpoint["roles_allowed"]) == set(perms.ALLOWED_ROLES), (
            f"{endpoint['id']} is now closed to "
            f"{sorted(set(perms.ALLOWED_ROLES) - set(endpoint['roles_allowed']))}"
        )


@pytest.mark.parametrize(
    "role",
    ["admin", "operatore_ufficio", "operatore_campo", "a role nobody defined"],
)
@pytest.mark.parametrize("capability", ["survey:write", "assessments:write"])
def test_the_guard_itself_admits_every_role(role, capability):
    """Run the dependency, rather than reasoning about the matrix that feeds it.

    The rest of this file reads structure. This one executes the actual guard
    the 86 wired endpoints now carry, for every role including an unrecognised
    one, and asserts it raises nothing — which is the whole safety claim behind
    that migration.
    """
    import asyncio
    from types import SimpleNamespace

    from app.dependencies import require_capability

    check = require_capability(capability)
    user = SimpleNamespace(role=role)
    assert asyncio.run(check(user=user)) is user


def test_the_ui_never_calls_a_route_that_does_not_exist(manifest):
    """A mistyped path in the frontend is a 404 at runtime and nothing earlier.

    TypeScript cannot check a string against the server's route table, and no
    backend test sees the frontend, so this crossing is the only place the two
    halves are compared.
    """
    orphans = manifest["review"]["ui_calls_without_a_matching_route"]
    assert not orphans, (
        "frontend/src calls /api/v1 path(s) the backend does not serve: "
        f"{orphans}"
    )


def test_every_endpoint_names_the_area_and_source_it_lives_in(manifest):
    """Cheap integrity check on the map itself.

    If the AST pass and the route table ever stop agreeing — a module renamed,
    an endpoint registered from somewhere unexpected — rows go blank rather than
    loud, and a map full of empty guards reads as "nothing is gated".
    """
    for endpoint in manifest["endpoints"]:
        assert endpoint["area"], f"{endpoint['id']} has no area"
        assert (REPO / endpoint["source"]).exists(), (
            f"{endpoint['id']} points at {endpoint['source']}, which does not exist"
        )
        assert endpoint["auth"] in {"required", "public"}
        assert endpoint["roles_allowed"], f"{endpoint['id']} is reachable by nobody"


def test_generated_manifest_is_deterministic(generator):
    """Two renders of the same code are identical.

    A timestamp, a set iteration order or an unsorted list would make the diff
    test fail at random, and a flaky guard gets deleted rather than fixed.
    """
    assert generator.render(generator.build_manifest()) == generator.render(
        generator.build_manifest()
    )
