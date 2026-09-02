"""Evaluator-v2 regression card (ROADMAP decision 16; EVALUATOR_SPEC §6).

Re-evaluates the stored campaign bundles under evaluator v2 against the frozen
blinded reference labels and reports detection, false positives, and exact/±1
localization before and after. Stored campaign evaluations under
results/per_run/ are never modified: every v2 artifact lives under
results/regression/.

Lanes: deterministic facts and replay results are reused from the stored run
directories (both lanes are unchanged in v2); only the judge is re-called,
under rubric-v2/prompt-v2 with the wider fixed observation window. The v2
judge pass is resumable (existing judge-v2 outputs are kept).

Usage:
    python scripts/regression_card.py --gate       # fixture gate first (live)
    python scripts/regression_card.py              # v2 judge pass + card (live)
    python scripts/regression_card.py --card-only  # rebuild card from stored v2 outputs

Requires OPENAI_API_KEY / OPENAI_BASE_URL for the live modes.
"""
from __future__ import annotations

import argparse
import json
import os
import time
import urllib.request
from pathlib import Path

from termscope.contracts import (
    AgentConfig, DeterministicFacts, JudgeResult, ReplayResult, RunBundle, TaskRef,
)
from termscope.evaluator.deterministic import evaluate_deterministic
from termscope.evaluator.judge import JudgeConfig, run_judge
from termscope.evaluator.merge import merge_lanes
from termscope.importer import import_trial

REPO = Path(__file__).resolve().parent.parent
PER_RUN = REPO / "results" / "per_run"
REVIEWS = REPO / "results" / "reviews"
OUT = REPO / "results" / "regression"
FIXTURES = REPO / "data" / "fixtures"
WORK = Path.home() / "termscope-work"
GIT_PIN = "69671fbaac6d67a7ef0dfec016cc38a64ef7a77c"

usage_log: list[dict] = []


def transport_from_env(cfg: JudgeConfig):
    base_url = os.environ["OPENAI_BASE_URL"].rstrip("/")
    api_key = os.environ["OPENAI_API_KEY"]

    def call(system: str, user: str) -> str:
        payload = json.dumps({
            "model": cfg.model, "temperature": cfg.temperature, "max_tokens": cfg.max_tokens,
            "response_format": {"type": "json_object"},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        }).encode()
        req = urllib.request.Request(base_url + "/chat/completions", data=payload,
                                     headers={"Content-Type": "application/json",
                                              "Authorization": f"Bearer {api_key}"})
        t0 = time.monotonic()
        with urllib.request.urlopen(req, timeout=cfg.timeout_sec) as resp:
            body = json.loads(resp.read().decode())
        u = body.get("usage") or {}
        choice = body["choices"][0]
        usage_log.append({"prompt_tokens": u.get("prompt_tokens"),
                          "completion_tokens": u.get("completion_tokens"),
                          "finish_reason": choice.get("finish_reason"),
                          "content_chars": len(choice["message"].get("content") or ""),
                          "seconds": round(time.monotonic() - t0, 1)})
        return choice["message"].get("content") or ""

    return call


def instruction_for(task: str) -> str:
    return (WORK / "tb2-src" / task / "instruction.md").read_text()


def reference_label(key: str) -> dict | None:
    """Blinded reference label: owner's blinded review if present, else the rater's."""
    rd = REVIEWS / key
    if not rd.exists():
        return None
    best = None
    for reviewer in ("owner", "claude-fable-5-1"):
        sub = rd / reviewer
        if not sub.exists():
            continue
        paths = [p for p in sub.glob("review-v*.json") if not p.name.endswith(".attachment.json")]
        versions = [json.loads(p.read_text())
                    for p in sorted(paths, key=lambda p: int(p.stem.rsplit("-v", 1)[1]))]
        blinded = [v for v in versions if v.get("blinded")]
        if blinded:
            best = blinded[-1]["label"]
            break
    return best


def jr_summary(r: JudgeResult) -> dict:
    return {"status": r.status, "verdict": r.verdict,
            "first_error": None if r.first_error is None else
            {"location": r.first_error.location, "step_id": r.first_error.step_id},
            "n_findings": len(r.findings),
            "n_material": sum(1 for f in r.findings if not f.recovered)}


def run_gate(cfg: JudgeConfig) -> int:
    """v2 must reproduce the fixture oracles before any campaign re-call."""
    task = TaskRef(name="fix-git", git_commit=GIT_PIN, difficulty="easy",
                   category="software-engineering")
    config = AgentConfig(config_id="hy3-terminus-2", agent="terminus-2", model="openai/hy3")
    instruction = instruction_for("fix-git")
    transport = transport_from_env(cfg)

    valid = import_trial(FIXTURES / "valid" / "trial", task=task, config=config)
    invalid = import_trial(FIXTURES / "invalid-known-first-error" / "trial",
                           task=task, config=config)
    oracle = json.loads((FIXTURES / "invalid-known-first-error" / "expected-oracle.json").read_text())
    k, cat = oracle["first_error"]["step_id"], oracle["primary_error_type"]

    print("v2 gate 1/2: valid fixture ...", flush=True)
    rv = run_judge(valid, evaluate_deterministic(valid), instruction, transport, cfg)
    material_v = [f for f in rv.findings if not f.recovered]
    pass_valid = (rv.status == "ok" and rv.verdict == "valid" and not material_v
                  and rv.first_error is not None and rv.first_error.location == "none")
    print(f"  -> {jr_summary(rv)}", flush=True)

    print("v2 gate 2/2: invalid fixture ...", flush=True)
    ri = run_judge(invalid, evaluate_deterministic(invalid), instruction, transport, cfg)
    hit = [f for f in ri.findings if f.step_id == k and not f.recovered]
    pass_invalid = (ri.status == "ok" and ri.verdict == "invalid"
                    and ri.first_error is not None
                    and ri.first_error.location == "located" and ri.first_error.step_id == k
                    and any(f.error_type == cat for f in hit))
    print(f"  -> {jr_summary(ri)} step-{k} categories {[f.error_type for f in hit]}", flush=True)

    OUT.mkdir(parents=True, exist_ok=True)
    record = {
        "record": "evaluator-v2-fixture-gate",
        "rubric_version": "rubric-v2", "prompt_version": "prompt-v2",
        "valid_fixture": {"pass": pass_valid, "result": jr_summary(rv)},
        "invalid_fixture": {"pass": pass_invalid, "expected_step": k,
                            "expected_category": cat, "result": jr_summary(ri)},
        "usage": usage_log,
        "passed": pass_valid and pass_invalid,
    }
    (OUT / "v2-gate.json").write_text(json.dumps(record, indent=1))
    print(json.dumps({"gate_passed": record["passed"]}), flush=True)
    return 0 if record["passed"] else 1


def load_stored(d: Path):
    bundle = RunBundle.model_validate_json((d / "bundle.json").read_text())
    facts = DeterministicFacts.model_validate_json((d / "deterministic.json").read_text())
    replay = ReplayResult.model_validate_json((d / "replay.json").read_text()) \
        if (d / "replay.json").exists() else None
    v1 = json.loads((d / "evaluation.json").read_text())["merged"]
    return bundle, facts, replay, v1


def judge_pass(cfg: JudgeConfig) -> None:
    transport = transport_from_env(cfg)
    jdir = OUT / "judge-v2"
    udir = OUT / "judge-v2-usage"
    jdir.mkdir(parents=True, exist_ok=True)
    udir.mkdir(parents=True, exist_ok=True)
    keys = [d.name for d in sorted(PER_RUN.iterdir()) if (d / "evaluation.json").exists()]
    for i, key in enumerate(keys, 1):
        out = jdir / f"{key}.json"
        if out.exists():
            continue
        bundle, facts, _, _ = load_stored(PER_RUN / key)
        n_before = len(usage_log)
        result = run_judge(bundle, facts, instruction_for(bundle.task.name), transport, cfg)
        out.write_text(result.model_dump_json(indent=1))
        (udir / f"{key}.json").write_text(json.dumps(usage_log[n_before:], indent=1))
        print(f"[{i}/{len(keys)}] {key}: {result.status}", flush=True)
        time.sleep(1)


def build_card() -> dict:
    rows = []
    for d in sorted(PER_RUN.iterdir()):
        if not (d / "evaluation.json").exists():
            continue
        key = d.name
        bundle, facts, replay, v1 = load_stored(d)
        j2path = OUT / "judge-v2" / f"{key}.json"
        judge2 = JudgeResult.model_validate_json(j2path.read_text()) if j2path.exists() else None
        v2 = json.loads(merge_lanes(bundle, facts, replay, judge2, version="v2").model_dump_json())
        ref = reference_label(key)
        rows.append({
            "run_id": key, "outcome": bundle.outcome,
            "reference": None if ref is None else {
                "process": ref.get("process"),
                "step": (ref.get("first_error") or {}).get("step_id"),
                "location": (ref.get("first_error") or {}).get("location"),
                "error_type": ref.get("error_type")},
            "v1": {"process": v1["process"], "step": v1["first_error"]["step_id"],
                   "location": v1["first_error"]["location"],
                   "primary_error_type": v1["primary_error_type"],
                   "resolved_but_invalid": v1["correct_result_invalid_process"]},
            "v2": {"process": v2["process"], "step": v2["first_error"]["step_id"],
                   "location": v2["first_error"]["location"],
                   "primary_error_type": v2["primary_error_type"],
                   "resolved_but_invalid": v2["correct_result_invalid_process"],
                   "judge_status": None if judge2 is None else judge2.status},
        })

    failed = [r for r in rows if r["outcome"] == "unresolved" and r["reference"]]
    ref_nonvalid = [r for r in failed if r["reference"]["process"] in ("partial", "invalid")]
    ref_located = [r for r in failed if r["reference"]["location"] == "located"]

    def nonvalid(side):
        return [r for r in ref_nonvalid if r[side]["process"] in ("partial", "invalid")]

    def verdict_agree(side):
        return [r for r in failed if r[side]["process"] == r["reference"]["process"]]

    def loc(side, tol):
        n = 0
        for r in failed:
            hs, ms = r["reference"]["step"], r[side]["step"]
            if hs is not None and ms is not None and abs(hs - ms) <= tol:
                n += 1
            elif hs is None and ms is None and r["reference"]["location"] == r[side]["location"] == "none":
                n += 1  # none-none agreement counts under both tolerances
        return n

    def cat_agree(side):
        n = 0
        for r in ref_located:
            if r[side]["step"] == r["reference"]["step"] and \
               r[side]["primary_error_type"] == r["reference"]["error_type"]:
                n += 1
        return n

    resolved = [r for r in rows if r["outcome"] == "resolved"]
    flagged = {s: [r["run_id"] for r in resolved if r[s]["resolved_but_invalid"]] for s in ("v1", "v2")}

    spend = {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0}
    udir = OUT / "judge-v2-usage"
    if udir.exists():
        for p in udir.glob("*.json"):
            for u in json.loads(p.read_text()):
                spend["calls"] += 1
                spend["prompt_tokens"] += u.get("prompt_tokens") or 0
                spend["completion_tokens"] += u.get("completion_tokens") or 0

    gate = json.loads((OUT / "v2-gate.json").read_text()) if (OUT / "v2-gate.json").exists() else None
    card = {
        "record": "evaluator-v2-regression-card",
        "v2_changes": [
            "rubric-v2/prompt-v2: mandatory four-part audit (commitments, contradictions, final claim, scope/safety) enforced by the validator; valid-as-earned verdict semantics; quoted-evidence rationales; externally-terminated-run principle",
            "wider fixed observation window (6000+3000 chars vs 1600+800)",
            "merge-v2: a causal replay flip caps a contradicting semantic valid at partial; category fallback when localization comes from replay alone",
        ],
        "labels": "frozen blinded reference labels (results/reviews/, provenance second_rater; owner-blinded would take precedence where present)",
        "fixture_gate": None if gate is None else {"passed": gate["passed"],
                                                   "valid": gate["valid_fixture"]["pass"],
                                                   "invalid": gate["invalid_fixture"]["pass"]},
        "metrics": {
            "denominators": {"failed_labeled": len(failed), "reference_nonvalid": len(ref_nonvalid),
                             "reference_located": len(ref_located), "resolved": len(resolved)},
            "detection_nonvalid": {"v1": f"{len(nonvalid('v1'))}/{len(ref_nonvalid)}",
                                   "v2": f"{len(nonvalid('v2'))}/{len(ref_nonvalid)}"},
            "verdict_agreement_3way": {"v1": f"{len(verdict_agree('v1'))}/{len(failed)}",
                                       "v2": f"{len(verdict_agree('v2'))}/{len(failed)}"},
            "localization_exact": {"v1": f"{loc('v1', 0)}/{len(failed)}",
                                   "v2": f"{loc('v2', 0)}/{len(failed)}"},
            "localization_pm1": {"v1": f"{loc('v1', 1)}/{len(failed)}",
                                 "v2": f"{loc('v2', 1)}/{len(failed)}"},
            "localization_located_only": {
                "v1": f"{sum(1 for r in ref_located if r['v1']['step'] == r['reference']['step'])}/{len(ref_located)}",
                "v2": f"{sum(1 for r in ref_located if r['v2']['step'] == r['reference']['step'])}/{len(ref_located)}"},
            "category_agreement_at_exact_step": {"v1": f"{cat_agree('v1')}/{len(ref_located)}",
                                                 "v2": f"{cat_agree('v2')}/{len(ref_located)}"},
            "resolved_flagged_invalid": {"v1": flagged["v1"], "v2": flagged["v2"],
                                         "note": "v2 flags are the owner's false-positive audit set; none are auto-accepted"},
        },
        "metric_definitions": {
            "localization_exact/pm1": "reference vs merged first error over all labeled failed runs; agreement = same step (within tolerance), or both sides 'none'",
            "localization_located_only": "exact step match restricted to runs whose reference label locates a step",
            "detection_nonvalid": "merged process in {partial, invalid} on runs the reference labels non-valid"},
        "residual_failure_mode": {
            "id": "audit-then-absolve",
            "evidence": "all completed v2 calls filled the mandatory audits (zero validation retries), yet 13/14 failed runs still came back 'valid' with 8 findings total across 39 calls; e.g. on one spectroscopy run the audit names the decisive peak-assignment commitment, records that amplitude/offset 'swing wildly', and itself classifies the final check as 'a structural check, not a fit-correctness check' — then renders valid with zero findings",
            "diagnosis": "the judge executes the audits but resolves them charitably inside the agent's own frame; it does not independently re-derive domain conclusions, and it shares the generating model's priors (measured self-evaluation bias, anticipated in EVALUATOR_SPEC §4.8). The one detection gain in v2 comes from the merge change (causal replay flip capping 'valid'), not from the semantic lane",
            "disposition": "decision 16 permits exactly one revision; v2 is it, measured and recorded. Stored campaign evaluations remain official v1; localization credibility rests on the replay lane and the blinded reference labels, and the semantic lane's limits are reported as a finding, not patched further"},
        "spend": spend,
        "provenance": {"labels": "second_rater (blinded)", "outcomes": "official",
                       "v1": "stored campaign evaluations (untouched)",
                       "v2": "results/regression/judge-v2 + merge-v2 over stored facts/replay"},
        "rows": rows,
    }
    return card


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gate", action="store_true", help="run the v2 fixture gate only")
    ap.add_argument("--card-only", action="store_true", help="rebuild the card from stored v2 outputs")
    args = ap.parse_args()
    cfg = JudgeConfig(version="v2", raw_dir=REPO / ".local" / "judge-raw-v2")
    if args.gate:
        return run_gate(cfg)
    if not args.card_only:
        judge_pass(cfg)
    OUT.mkdir(parents=True, exist_ok=True)
    card = build_card()
    (OUT / "regression-card.json").write_text(json.dumps(card, indent=1))
    print(json.dumps({k: card[k] for k in ("fixture_gate", "metrics", "spend")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
