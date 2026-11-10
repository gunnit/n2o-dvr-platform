"""Backend CI runs the interpreter production runs.

Render pins ``PYTHON_VERSION`` for the API and the worker; CI used to test on
3.12, and a 3.14-only import failure (a schema field shadowing the builtin
``list`` under lazy annotations) reached review instead of CI.
"""

from pathlib import Path

import pytest
import yaml

BACKEND_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = BACKEND_ROOT.parent / ".github" / "workflows" / "backend-ci.yml"


def _production_versions() -> set[str]:
    blueprint = yaml.safe_load((BACKEND_ROOT / "render.yaml").read_text(encoding="utf-8"))
    return {
        str(env["value"])
        for service in blueprint["services"]
        for env in service.get("envVars", [])
        if env.get("key") == "PYTHON_VERSION"
    }


@pytest.mark.skipif(not WORKFLOW.exists(), reason="the CI workflow is not in this checkout")
def test_backend_ci_python_matches_render_python_version():
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    setup = next(
        step
        for step in workflow["jobs"]["test"]["steps"]
        if str(step.get("uses", "")).startswith("actions/setup-python")
    )
    assert _production_versions() == {str(setup["with"]["python-version"])}
