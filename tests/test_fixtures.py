"""Offline validation: fixture bundles must match their expected oracles (Day 2 exit)."""
import json
from pathlib import Path

import pytest

from termscope.contracts import AgentConfig, TaskRef
from termscope.importer import import_trial, verify_bundle

FIXTURES = Path(__file__).resolve().parent.parent / "data" / "fixtures"
GIT_PIN = "69671fbaac6d67a7ef0dfec016cc38a64ef7a77c"

FIXGIT = TaskRef(name="fix-git", git_commit=GIT_PIN, difficulty="easy", category="software-engineering")
EIGEN = TaskRef(name="largest-eigenval", git_commit=GIT_PIN, difficulty="medium", category="mathematics")
HY3_T2 = AgentConfig(config_id="hy3-terminus-2", agent="terminus-2", model="openai/hy3")
ORACLE = AgentConfig(config_id="oracle", agent="oracle")


def oracle_for(name: str) -> dict:
    return json.loads((FIXTURES / name / "expected-oracle.json").read_text())


@pytest.fixture(scope="module")
def bundles():
    return {
        "valid": import_trial(FIXTURES / "valid" / "trial", task=FIXGIT, config=HY3_T2),
        "invalid-known-first-error": import_trial(
            FIXTURES / "invalid-known-first-error" / "trial", task=FIXGIT, config=HY3_T2
        ),
        "inconclusive": import_trial(FIXTURES / "inconclusive" / "trial", task=EIGEN, config=ORACLE),
    }


def test_all_bundles_hash_verify(bundles):
    for name, b in bundles.items():
        assert verify_bundle(b), name


def test_outcomes_match_expected_oracles(bundles):
    for name, b in bundles.items():
        assert b.outcome == oracle_for(name)["outcome"], name


def test_valid_fixture_is_verbatim_clean_solve(bundles):
    b = bundles["valid"]
    assert b.reward == 1.0
    assert b.trajectory is not None and len(b.trajectory) == 15
    assert all(c.status == "passed" for c in b.verifier.checks)
    assert b.token_usage is not None and b.token_usage.total_tokens == 69401


def test_invalid_fixture_known_first_error_step(bundles):
    b = bundles["invalid-known-first-error"]
    oracle = oracle_for("invalid-known-first-error")
    k = oracle["first_error"]["step_id"]
    assert b.reward == 0.0
    assert b.trajectory is not None and len(b.trajectory) == 5
    fatal = b.trajectory[k - 1]
    assert fatal.step_id == k
    assert fatal.command is not None and "rm -rf" in fatal.command
    claim = b.trajectory[k]
    assert claim.command is None  # success claimed with no confirming command
    assert all(c.status == "failed" for c in b.verifier.checks)
    # steps 1..3 are the real, undoctored pristine-repo prefix (read-only)
    valid_prefix = bundles["valid"].trajectory[:3]
    assert tuple(s.command for s in b.trajectory[:3]) == tuple(s.command for s in valid_prefix)


def test_inconclusive_fixture_has_infrastructure_exception(bundles):
    b = bundles["inconclusive"]
    assert b.exception is not None and "EnvironmentTeardownError" in b.exception
    assert b.verifier.checks == ()
    assert oracle_for("inconclusive")["process_verdict"] is None
