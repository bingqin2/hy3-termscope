"""Judge gate (live Hy3): the judge must reproduce the fixture oracles before
any campaign quota is spent, plus five stability sessions on the invalid
fixture (decision 12 instrument-measurement carve-out).

Requires OPENAI_API_KEY / OPENAI_BASE_URL in the environment (source the
owner's credentials file first; nothing is printed).

Writes:
  data/environment-checks/day5-judge-gate.json
  results/judge-stability/invalid-fixture-sessions.json
"""
import json
import os
import sys
import time
import urllib.request
from collections import Counter
from pathlib import Path

from termscope.contracts import AgentConfig, ReplayResult, TaskRef
from termscope.evaluator.deterministic import evaluate_deterministic
from termscope.evaluator.judge import JudgeConfig, run_judge
from termscope.evaluator.merge import evaluate_bundle
from termscope.importer import import_trial

REPO = Path(__file__).resolve().parent.parent
FIXTURES = REPO / "data" / "fixtures"
GIT_PIN = "69671fbaac6d67a7ef0dfec016cc38a64ef7a77c"
FIXGIT = TaskRef(name="fix-git", git_commit=GIT_PIN, difficulty="easy",
                 category="software-engineering")
HY3_T2 = AgentConfig(config_id="hy3-terminus-2", agent="terminus-2", model="openai/hy3")

INSTRUCTION = (Path.home() / "termscope-work" / "tb2-src" / "fix-git" / "instruction.md").read_text()

usage_log: list[dict] = []


def make_transport(cfg: JudgeConfig):
    base_url = os.environ["OPENAI_BASE_URL"].rstrip("/")
    api_key = os.environ["OPENAI_API_KEY"]

    def call(system: str, user: str) -> str:
        payload = json.dumps({
            "model": cfg.model,
            "temperature": cfg.temperature,
            "max_tokens": cfg.max_tokens,
            "response_format": {"type": "json_object"},
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": user}],
        }).encode()
        req = urllib.request.Request(
            base_url + "/chat/completions", data=payload,
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {api_key}"})
        started = time.monotonic()
        with urllib.request.urlopen(req, timeout=cfg.timeout_sec) as resp:
            body = json.loads(resp.read().decode())
        usage = body.get("usage") or {}
        usage_log.append({
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
            "seconds": round(time.monotonic() - started, 1),
        })
        return body["choices"][0]["message"]["content"]

    return call


def jr_summary(r):
    return {
        "status": r.status,
        "verdict": r.verdict,
        "first_error": None if r.first_error is None else
            {"location": r.first_error.location, "step_id": r.first_error.step_id},
        "findings": [
            {"step_id": f.step_id, "error_type": f.error_type, "severity": f.severity,
             "recovered": f.recovered, "rationale": f.rationale}
            for f in r.findings
        ],
        "retried": r.retried,
    }


def main() -> int:
    cfg = JudgeConfig(raw_dir=REPO / ".local" / "judge-raw")
    transport = make_transport(cfg)

    valid = import_trial(FIXTURES / "valid" / "trial", task=FIXGIT, config=HY3_T2)
    invalid = import_trial(FIXTURES / "invalid-known-first-error" / "trial",
                           task=FIXGIT, config=HY3_T2)
    oracle_invalid = json.loads(
        (FIXTURES / "invalid-known-first-error" / "expected-oracle.json").read_text())
    k = oracle_invalid["first_error"]["step_id"]
    cat = oracle_invalid["primary_error_type"]

    print("gate 1/2: valid fixture ...", flush=True)
    fv = evaluate_deterministic(valid)
    rv = run_judge(valid, fv, INSTRUCTION, transport, cfg)
    material_v = [f for f in rv.findings if not f.recovered]
    pass_valid = (rv.status == "ok" and rv.verdict == "valid" and not material_v
                  and rv.first_error is not None and rv.first_error.location == "none")
    print(f"  -> {rv.status}/{rv.verdict}, material findings {len(material_v)}, "
          f"first_error {jr_summary(rv)['first_error']}", flush=True)

    print("gate 2/2: invalid fixture ...", flush=True)
    fi = evaluate_deterministic(invalid)
    ri = run_judge(invalid, fi, INSTRUCTION, transport, cfg)
    hit_step = [f for f in ri.findings if f.step_id == k and not f.recovered]
    pass_invalid = (
        ri.status == "ok" and ri.verdict == "invalid"
        and ri.first_error is not None and ri.first_error.location == "located"
        and ri.first_error.step_id == k
        and any(f.error_type == cat for f in hit_step)
    )
    print(f"  -> {ri.status}/{ri.verdict}, first_error {jr_summary(ri)['first_error']}, "
          f"step-{k} categories {[f.error_type for f in hit_step]}", flush=True)

    print("stability: 5 sessions on the invalid fixture ...", flush=True)
    sessions = []
    for i in range(5):
        s = run_judge(invalid, fi, INSTRUCTION, transport, cfg)
        sessions.append(s)
        fe = jr_summary(s)["first_error"]
        print(f"  session {i+1}: {s.status}/{s.verdict} first_error {fe}", flush=True)

    verdicts = Counter(s.verdict for s in sessions)
    steps = Counter(None if s.first_error is None else s.first_error.step_id for s in sessions)
    cats = Counter(
        next((f.error_type for f in s.findings
              if s.first_error and f.step_id == s.first_error.step_id and not f.recovered), None)
        for s in sessions
    )
    stability = {
        "record": "judge-stability-invalid-fixture",
        "n_sessions": 5,
        "judge": {"model": cfg.model, "temperature": cfg.temperature,
                  "rubric": "rubric-v1", "prompt": "prompt-v1"},
        "verdict_agreement": f"{max(verdicts.values())}/5",
        "first_error_step_agreement": f"{max(steps.values())}/5",
        "primary_category_agreement": f"{max(cats.values())}/5",
        "sessions": [jr_summary(s) for s in sessions],
    }
    outdir = REPO / "results" / "judge-stability"
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "invalid-fixture-sessions.json").write_text(json.dumps(stability, indent=1))

    # full-pipeline demonstration on the invalid fixture: replay (measured on
    # this machine) + judge + merge
    day4 = json.loads((REPO / "data" / "environment-checks" / "day4-replay-measurement.json").read_text())
    replay = ReplayResult(
        feasible=True,
        localization=day4["invalid_fixture"]["localization"],
        first_error_step=day4["invalid_fixture"]["first_error_step"],
        notes=tuple(day4["invalid_fixture"]["notes"]),
    )
    ev = evaluate_bundle(invalid, judge=ri, replay=replay)
    merged = {
        "process": ev.merged.process,
        "first_error": {"location": ev.merged.first_error.location,
                        "step_id": ev.merged.first_error.step_id},
        "judge_earlier_step": ev.merged.judge_earlier_step,
        "primary_error_type": ev.merged.primary_error_type,
        "correct_result_invalid_process": ev.merged.correct_result_invalid_process,
        "flagged_for_human_review": ev.merged.flagged_for_human_review,
    }

    tokens_in = sum(u["prompt_tokens"] or 0 for u in usage_log)
    tokens_out = sum(u["completion_tokens"] or 0 for u in usage_log)
    record = {
        "record": "day5-judge-gate",
        "judge": {"model": cfg.model, "temperature": cfg.temperature,
                  "rubric_version": "rubric-v1", "prompt_version": "prompt-v1"},
        "gate": {
            "valid_fixture": {"pass": pass_valid, "result": jr_summary(rv)},
            "invalid_fixture": {"pass": pass_invalid, "expected_step": k,
                                "expected_category": cat, "result": jr_summary(ri)},
        },
        "stability_summary": {key: stability[key] for key in
                              ("verdict_agreement", "first_error_step_agreement",
                               "primary_category_agreement")},
        "merged_invalid_fixture": merged,
        "cost": {"calls": len(usage_log), "prompt_tokens": tokens_in,
                 "completion_tokens": tokens_out, "total_tokens": tokens_in + tokens_out,
                 "per_call": usage_log},
        "gate_passed": bool(pass_valid and pass_invalid),
    }
    (REPO / "data" / "environment-checks" / "day5-judge-gate.json").write_text(
        json.dumps(record, indent=1))
    print(f"gate_passed={record['gate_passed']} "
          f"tokens={record['cost']['total_tokens']} over {len(usage_log)} calls", flush=True)
    return 0 if record["gate_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
