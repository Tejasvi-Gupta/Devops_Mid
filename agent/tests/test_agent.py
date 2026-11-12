import os

from epp_agent.commands import (
    RejectedAction,
    build_winget_command,
    load_catalog,
    manifest_matches,
)
from epp_agent.detect import detect_with

CATALOG = load_catalog()


def test_install_command_is_allowlisted():
    command = build_winget_command(
        {
            "operation": "install",
            "tool": "git",
            "version": "2.56.0.3",
            "package_id": "Git.Git",
            "reason": "missing",
            "impact": "installs git",
            "requires_elevation": True,
            "requires_reboot": False,
            "approval_required": True,
            "risks": [],
            "acknowledgements": ["elevation"],
        },
        CATALOG,
    )
    assert command[:4] == ["winget", "install", "--id", "Git.Git"]
    assert "--version" in command
    assert "2.56.0.3" in command
    assert all(not item.startswith("cmd") for item in command)


def test_server_supplied_shell_is_rejected():
    try:
        build_winget_command(
            {"operation": "install", "tool": "git", "version": "2.56.0.3", "package_id": "Git.Git", "command": "calc.exe"},
            CATALOG,
        )
    except RejectedAction:
        return
    raise AssertionError("shell commands must be rejected")


def test_manifest_pin_must_match():
    entry = next(item for item in CATALOG["tools"] if item["id"] == "git")["versions"][0]
    sample = f"Installer Url: {entry['url']}\nInstaller SHA256: {entry['sha256']}\n"
    assert manifest_matches(sample, entry)
    assert not manifest_matches(sample.replace(entry["sha256"], "0" * 64), entry)


def test_detection_parses_command_output(monkeypatch):
    monkeypatch.setattr("epp_agent.detect._desktop_installed", lambda: False)

    def run(args):
        joined = " ".join(args)
        if joined == "python --version":
            return 0, "Python 3.12.10"
        if joined == "docker info":
            return 1, "Cannot connect"
        return 1, "not found"

    report = detect_with(run)
    python = next(item for item in report["tools"] if item["tool"] == "python")
    engine = next(item for item in report["tools"] if item["tool"] == "docker_engine")
    assert python["version"] == "3.12.10"
    assert python["functional"] is True
    assert engine["engine_running"] is False


def test_real_installer_is_disabled_during_tests():
    os.environ["EPP_AGENT_MODE"] = "test"
    from epp_agent.execute import WindowsInstaller

    try:
        WindowsInstaller().execute({"operation": "install", "tool": "git", "version": "2.56.0.3", "package_id": "Git.Git"})
    except RuntimeError as exc:
        assert "EPP_AGENT_MODE=test" in str(exc)
        return
    raise AssertionError("the test guard did not stop the installer")
