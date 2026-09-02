"""Replay lane logic tests (search behavior; Docker integration lives in
scripts/day4_replay_measurement.py and its committed measurement record)."""
from datetime import datetime, timezone

from termscope.contracts import AgentConfig, RunBundle, TaskRef, TrajectoryStep, VerifierRecord
from termscope.evaluator.replay import localize

GIT_PIN = "69671fbaac6d67a7ef0dfec016cc38a64ef7a77c"
FIXGIT = TaskRef(name="fix-git", git_commit=GIT_PIN, difficulty="easy", category="software-engineering")
HY3_T2 = AgentConfig(config_id="hy3-terminus-2", agent="terminus-2", model="openai/hy3")


def step(i, command=None, source="agent"):
    return TrajectoryStep(step_id=i, source=source, content=f"step {i}", command=command)


def bundle(steps):
    return RunBundle(
        bundle_id="0" * 64,
        created_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
        task=FIXGIT, config=HY3_T2, outcome="unresolved", reward=0.0,
        verifier=VerifierRecord(reward=0.0), trajectory=tuple(steps),
        files=(), trial_name="synthetic",
    )


class FakeEnv:
    """passed = fn(n_commands); records probe count."""

    def __init__(self, fn):
        self.fn, self.calls = fn, 0

    def probe(self, commands, probe):
        self.calls += 1
        return self.fn(len(commands)), 0.1


# steps 1 (user, no cmd), 2..8 commands, 9 claim (no cmd) — fixture-shaped
STEPS = [step(1, source="user")] + [step(i, f"cmd{i}") for i in range(2, 9)] + [step(9)]


def test_locates_permanent_flip():
    env = FakeEnv(lambda n: n < 7)  # bad once the 7th command (step 8) is included
    r = localize(bundle(STEPS), env)
    assert r.localization == "located"
    assert r.first_error_step == 8
    assert r.feasible is True
    assert any("permanently unreachable from k=8" in n for n in r.notes)
    assert env.calls <= 6  # bisection, not a linear sweep of 7 prefixes


def test_no_flip_reports_none():
    env = FakeEnv(lambda n: True)
    r = localize(bundle(STEPS), env)
    assert r.localization == "none"
    assert r.first_error_step is None
    assert any("omission" in n for n in r.notes)


def test_bad_baseline_is_unlocatable_and_infeasible():
    env = FakeEnv(lambda n: False)
    r = localize(bundle(STEPS), env)
    assert r.localization == "unlocatable"
    assert r.feasible is False
    assert any("baseline" in n for n in r.notes)


def test_nondeterministic_flip_is_unlocatable():
    seen = {}

    def flaky(n):
        if n < 7:
            return True
        seen[n] = seen.get(n, 0) + 1
        return seen[n] > 1  # False first, True on the repeat probe

    r = localize(bundle(STEPS), FakeEnv(flaky))
    assert r.localization == "unlocatable"
    assert any("non-determinism" in n for n in r.notes)


def test_probe_failure_is_unlocatable():
    env = FakeEnv(lambda n: None)
    r = localize(bundle(STEPS), env)
    assert r.localization == "unlocatable"


def test_no_commands_is_unlocatable():
    r = localize(bundle([step(1, source="user"), step(2)]), FakeEnv(lambda n: True))
    assert r.localization == "unlocatable"
    assert r.feasible is False


def test_matrix_records_every_probe():
    env = FakeEnv(lambda n: n < 7)
    r = localize(bundle(STEPS), env)
    assert len(r.matrix) == env.calls
    assert all(p.probe == "reachability" for p in r.matrix)
