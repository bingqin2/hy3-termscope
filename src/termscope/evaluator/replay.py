"""Replay lane — prefix-replay causal localization (ROADMAP decision 7, flagship).

For a failed or flagged run: rebuild the task environment fresh from its pinned
image, execute the trajectory's commands 1..k in one non-interactive shell
session, and probe the outcome at that prefix. Two probes exist:

- ``direct``      — run the task's checks: do they already pass at k?
- ``reachability``— run the oracle solution from the prefix state, then the
                    checks: is the task still completable? (the spec's
                    "reachable outcome")

The causal first error of a failed run is the first k at which reachability
flips False **permanently** (verified at the flip and its predecessor, with a
repeat probe at the flip to catch non-determinism). When no prefix flips —
or probes disagree on repetition — replay reports ``none`` / ``unlocatable``
honestly instead of forcing a step.

Known, recorded limitation: the oracle solution assumes a pristine initial
state, so a prefix ending inside an unfinished operation (e.g. an unresolved
merge) can flip reachability without being a material error. The flip step's
command is therefore always included in the notes, and the judge/human lanes
weigh materiality (merge precedence, EVALUATOR_SPEC §5).

Everything here is local Docker; zero model calls, zero API quota.
"""
from __future__ import annotations

import subprocess
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Literal

from termscope.contracts import PrefixCheck, ReplayResult, RunBundle

Probe = Literal["direct", "reachability"]

_SESSION_PRELUDE = (
    "set +e\n"
    "export PAGER=cat GIT_PAGER=cat TERM=dumb DEBIAN_FRONTEND=noninteractive\n"
)


@dataclass
class DockerReplayEnv:
    """Runs prefix probes for one task in throwaway containers."""

    image: str
    workdir: str
    tests_dir: Path
    solution_dir: Path
    platform: str = "linux/amd64"
    check_timeout_sec: float = 900.0
    prefix_timeout_sec: float = 300.0
    log: Callable[[str], None] = lambda s: None

    def _run(self, args: list[str], *, timeout: float, input_text: str | None = None):
        return subprocess.run(
            args, input=input_text, capture_output=True, text=True, timeout=timeout
        )

    def probe(self, commands: list[str], probe: Probe) -> tuple[bool | None, float]:
        """Fresh container -> prefix 1..k -> (oracle) -> checks. Returns (passed, seconds)."""
        name = f"termscope-replay-{uuid.uuid4().hex[:12]}"
        started = time.monotonic()
        try:
            run = self._run(
                ["docker", "run", "-d", "--platform", self.platform, "--name", name,
                 "--entrypoint", "sleep", self.image, "infinity"],
                timeout=120,
            )
            if run.returncode != 0:
                self.log(f"container start failed: {run.stderr.strip()[:200]}")
                return None, time.monotonic() - started
            self._run(["docker", "exec", name, "mkdir", "-p", "/logs/verifier"], timeout=30)

            if commands:
                script = _SESSION_PRELUDE + f"cd {self.workdir}\n" + "\n".join(commands) + "\n"
                self._run(
                    ["docker", "exec", "-i", name, "bash", "-s"],
                    timeout=self.prefix_timeout_sec, input_text=script,
                )

            if probe == "reachability":
                self._run(
                    ["docker", "cp", str(self.solution_dir), f"{name}:/solution"],
                    timeout=60,
                )
                self._run(
                    ["docker", "exec", name, "bash", "-c",
                     f"cd {self.workdir} && bash /solution/solve.sh"],
                    timeout=self.prefix_timeout_sec,
                )

            self._run(["docker", "cp", str(self.tests_dir), f"{name}:/tests"], timeout=60)
            self._run(
                ["docker", "exec", name, "bash", "-c",
                 f"cd {self.workdir} && bash /tests/test.sh"],
                timeout=self.check_timeout_sec,
            )
            reward = self._run(
                ["docker", "exec", name, "cat", "/logs/verifier/reward.txt"], timeout=30
            )
            text = reward.stdout.strip() if reward.returncode == 0 else ""
            passed = {"1": True, "0": False}.get(text)
            elapsed = time.monotonic() - started
            self.log(f"probe k={len(commands)} {probe}: passed={passed} ({elapsed:.0f}s)")
            return passed, elapsed
        except subprocess.TimeoutExpired:
            self.log(f"probe k={len(commands)} {probe}: timeout")
            return None, time.monotonic() - started
        finally:
            subprocess.run(["docker", "rm", "-f", name], capture_output=True, timeout=60)


@dataclass
class FlipSearch:
    """Pure first-permanent-flip search over ordered prefix indices.

    ``probe_fn(k)`` returns True (good), False (bad), or None (probe failure).
    Assumes monotonicity, then verifies the flip boundary and repeats the probe
    at the flip once; disagreement or probe failure -> unlocatable.
    """

    probe_fn: Callable[[int], bool | None]
    checked: dict[int, bool | None] = field(default_factory=dict)

    def at(self, k: int) -> bool | None:
        if k not in self.checked:
            self.checked[k] = self.probe_fn(k)
        return self.checked[k]

    def search(self, ks: list[int]) -> tuple[str, int | None, list[str]]:
        notes: list[str] = []
        lo_ok = self.at(0)
        if lo_ok is None:
            return "unlocatable", None, ["baseline probe (k=0) failed to produce an outcome"]
        if lo_ok is False:
            return "unlocatable", None, [
                "baseline (k=0) is already bad — environment drift vs. the gate record"
            ]
        hi = ks[-1]
        hi_ok = self.at(hi)
        if hi_ok is None:
            return "unlocatable", None, [f"final probe (k={hi}) failed to produce an outcome"]
        if hi_ok is True:
            return "none", None, [
                "no prefix flips the reachable outcome — the failure is one of "
                "omission, not a destroyed state"
            ]
        lo_i, hi_i = -1, len(ks) - 1  # ks[lo_i] good (virtual k=0), ks[hi_i] bad
        while hi_i - lo_i > 1:
            mid_i = (lo_i + hi_i) // 2
            mid_ok = self.at(ks[mid_i])
            if mid_ok is None:
                return "unlocatable", None, [f"probe at k={ks[mid_i]} failed to produce an outcome"]
            if mid_ok:
                lo_i = mid_i
            else:
                hi_i = mid_i
        flip = ks[hi_i]
        repeat = self.probe_fn(flip)  # fresh repeat, bypassing the cache
        if repeat is not False:
            notes.append(
                f"repeat probe at flip k={flip} disagreed (non-determinism recorded)"
            )
            return "unlocatable", None, notes
        prev = ks[lo_i] if lo_i >= 0 else 0
        notes.append(f"reachable through k={prev}, permanently unreachable from k={flip}")
        return "located", flip, notes


def localize(
    bundle: RunBundle,
    env: DockerReplayEnv,
    *,
    probe: Probe = "reachability",
) -> ReplayResult:
    """Causally localize a run's first error by prefix replay."""
    if bundle.trajectory is None:
        return ReplayResult(feasible=False, localization="unlocatable",
                            notes=("no trajectory to replay",))

    command_steps = [s.step_id for s in bundle.trajectory if s.command]
    if not command_steps:
        return ReplayResult(feasible=False, localization="unlocatable",
                            notes=("trajectory has no commands",))
    commands_by_step = {s.step_id: s.command for s in bundle.trajectory if s.command}

    matrix: list[PrefixCheck] = []

    def probe_fn(k: int) -> bool | None:
        cmds = [commands_by_step[s] for s in command_steps if s <= k]
        passed, seconds = env.probe(cmds, probe)
        matrix.append(PrefixCheck(prefix_k=k, reward=None, passed=passed,
                                  probe=probe, seconds=round(seconds, 1)))
        return passed

    search = FlipSearch(probe_fn)
    localization, flip_step, notes = search.search(command_steps)

    if localization == "located" and flip_step is not None:
        cmd = commands_by_step[flip_step].split("\n")[0]
        notes.append(f"flip step command: {cmd[:120]}")

    feasible = not (
        localization == "unlocatable"
        and any("baseline" in n or "failed to produce" in n for n in notes)
    )
    return ReplayResult(
        feasible=feasible,
        localization=localization,  # type: ignore[arg-type]
        first_error_step=flip_step,
        matrix=tuple(sorted(matrix, key=lambda p: p.prefix_k)),
        notes=tuple(notes),
    )
