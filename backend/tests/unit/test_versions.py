import pytest
from app.domain.versions import VersionError, extract_version, validate_constraint, version_satisfies


def test_exact_and_range_constraints():
    assert version_satisfies("3.12.10", "==3.12.10")
    assert not version_satisfies("3.12.11", "==3.12.10")
    assert version_satisfies("3.12.10", ">=3.12,<3.13")
    assert not version_satisfies("3.13.0", ">=3.12,<3.13")
    assert version_satisfies("2.56.0.3", "==2.56.0.3")
    assert version_satisfies("24.22.1", "present")
    assert not version_satisfies(None, "present")


def test_rejects_unconstrained_words():
    with pytest.raises(VersionError):
        validate_constraint("latest")
    with pytest.raises(VersionError):
        validate_constraint("")


def test_extracts_tool_versions():
    assert extract_version("git", "git version 2.56.0.windows.3") == "2.56.0.3"
    assert extract_version("node", "v24.22.1") == "24.22.1"
    assert extract_version("python", "Python 3.12.10") == "3.12.10"
    assert extract_version("python", "not a version") is None
