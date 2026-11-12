from pathlib import Path

from app.domain.catalog import load_catalog
from app.domain.planning import build_plan
from app.domain.sanitize import redact_text
from app.domain.state import assert_transition, readiness_from_results

CATALOG = load_catalog(str(Path(__file__).resolve().parents[3] / "catalog" / "tools.json"))
PYTHON = {
    "tool": "python",
    "version_constraint": "==3.12.10",
    "mandatory": True,
    "install_strategy": "winget",
}


def test_reuses_a_compliant_interpreter():
    plan = build_plan(
        [PYTHON],
        {"tools": [{"tool": "python", "installed": True, "version": "3.12.10", "functional": True}]},
        CATALOG,
    )
    assert plan["actions"][0]["operation"] == "reuse"
    assert plan["approval_required"] is False


def test_plans_catalog_install_without_substituting_a_version():
    plan = build_plan(
        [PYTHON],
        {"tools": [{"tool": "python", "installed": True, "version": "3.14.6", "functional": True}]},
        CATALOG,
    )
    action = plan["actions"][0]
    assert action["operation"] == "install"
    assert action["version"] == "3.12.10"
    assert action["package_id"] == "Python.Python.3.12"
    assert "command" not in action
    assert plan["required_acknowledgements"] == ["elevation"]


def test_docker_engine_is_not_ready_from_the_cli_version_alone():
    plan = build_plan(
        [{"tool": "docker_engine", "version_constraint": "present", "mandatory": True, "install_strategy": "verify_only"}],
        {"tools": [{"tool": "docker_engine", "installed": True, "version": "28.0.0", "functional": True, "engine_running": False}]},
        CATALOG,
    )
    assert plan["actions"][0]["operation"] == "verify_only"
    assert plan["actions"][0]["operation"] != "install"


def test_optional_failure_does_not_block_readiness():
    requirements = [
        {"tool": "python", "mandatory": True},
        {"tool": "git", "mandatory": False},
    ]
    results = [
        {"tool": "python", "outcome": "pass"},
        {"tool": "git", "outcome": "fail"},
    ]
    assert readiness_from_results(requirements, results, True) == "ready"
    assert readiness_from_results(requirements, [{"tool": "python", "outcome": "fail"}], True) == "not_ready"
    assert readiness_from_results(requirements, results, False) == "needs_update"


def test_invalid_job_transition_is_rejected():
    try:
        assert_transition("pending", "completed")
    except ValueError:
        return
    raise AssertionError("pending jobs must not jump to completed")


def test_secrets_are_redacted():
    text = redact_text("Authorization: Bearer abc.def.ghi and token=dvc_secretvalue")
    assert "abc.def.ghi" not in text
    assert "dvc_secretvalue" not in text
    assert "[redacted]" in text
