"""Judge consistency sessions (EVALUATOR_SPEC §6.4; decision 12 carve-out).

One additional judge session per campaign run (plus, with --stability RUN,
five sessions on one real flagged run). Sessions are instrument-variance
measurements: the first campaign judgement stays the official evaluation and
these repeats live under results/judge-stability/, never in per_run/.

Writes:
  results/judge-stability/consistency/<key>.json      (one repeat per run)
  results/judge-stability/real-run-sessions.json      (--stability)
  results/judge-stability/consistency-summary.json    (agreement table)

Requires OPENAI_API_KEY / OPENAI_BASE_URL in the environment.
Verdicts are never printed (agreement flags only).
"""
from __future__ import annotations

import argparse
import json
import os
import time
import urllib.request
from pathlib import Path

from termscope.contracts import DeterministicFacts, JudgeResult, RunBundle
from termscope.evaluator.judge import JudgeConfig, run_judge

REPO = Path(__file__).resolve().parent.parent
PER_RUN = REPO / "results" / "per_run"
OUT = REPO / "results" / "judge-stability"
WORK = Path.home() / "termscope-work"


def transport(cfg: JudgeConfig):
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
        with urllib.request.urlopen(req, timeout=cfg.timeout_sec) as resp:
            body = json.loads(resp.read().decode())
        return body["choices"][0]["message"].get("content") or ""

    return call


def agreement(a: JudgeResult, b: JudgeResult) -> dict:
    def step(r):
        return None if r.first_error is None else r.first_error.step_id

    def primary(r):
        s = step(r)
        for f in r.findings:
            if f.step_id == s and not f.recovered:
                return f.error_type
        return None

    both_ok = a.status == "ok" and b.status == "ok"
    return {
        "both_ok": both_ok,
        "verdict_agree": both_ok and a.verdict == b.verdict,
        "first_error_step_agree": both_ok and step(a) == step(b),
        "first_error_pm1": both_ok and step(a) is not None and step(b) is not None
                           and abs(step(a) - step(b)) <= 1,
        "primary_category_agree": both_ok and primary(a) == primary(b),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stability", metavar="RUN_ID",
                    help="also run five sessions on this real flagged run")
    args = ap.parse_args()
    cfg = JudgeConfig(raw_dir=REPO / ".local" / "judge-raw-consistency")
    call = transport(cfg)
    (OUT / "consistency").mkdir(parents=True, exist_ok=True)

    rows = []
    for d in sorted(PER_RUN.iterdir()):
        if not (d / "judge.json").exists():
            continue
        official = JudgeResult.model_validate_json((d / "judge.json").read_text())
        out = OUT / "consistency" / f"{d.name}.json"
        if out.exists():
            repeat = JudgeResult.model_validate_json(out.read_text())
        else:
            bundle = RunBundle.model_validate_json((d / "bundle.json").read_text())
            facts = DeterministicFacts.model_validate_json((d / "deterministic.json").read_text())
            instr = (WORK / "tb2-src" / bundle.task.name / "instruction.md").read_text()
            repeat = run_judge(bundle, facts, instr, call, cfg)
            out.write_text(repeat.model_dump_json(indent=1))
            time.sleep(1)
        ag = agreement(official, repeat)
        rows.append({"run_id": d.name, **ag})
        print(f"{d.name:46s} ok={ag['both_ok']} verdict={ag['verdict_agree']} "
              f"step={ag['first_error_step_agree']} cat={ag['primary_category_agree']}", flush=True)

    summary = {
        "record": "judge-consistency-one-session-per-campaign-run",
        "n_runs": len(rows),
        "both_ok": sum(r["both_ok"] for r in rows),
        "verdict_agreement": f"{sum(r['verdict_agree'] for r in rows)}/{len(rows)}",
        "first_error_step_agreement": f"{sum(r['first_error_step_agree'] for r in rows)}/{len(rows)}",
        "first_error_pm1_agreement": f"{sum(r['first_error_pm1'] for r in rows)}/{len(rows)}",
        "primary_category_agreement": f"{sum(r['primary_category_agree'] for r in rows)}/{len(rows)}",
        "rows": rows,
    }

    if args.stability:
        d = PER_RUN / args.stability
        bundle = RunBundle.model_validate_json((d / "bundle.json").read_text())
        facts = DeterministicFacts.model_validate_json((d / "deterministic.json").read_text())
        instr = (WORK / "tb2-src" / bundle.task.name / "instruction.md").read_text()
        official = JudgeResult.model_validate_json((d / "judge.json").read_text())
        sessions = []
        for i in range(5):
            s = run_judge(bundle, facts, instr, call, cfg)
            sessions.append(s)
            time.sleep(1)
        ags = [agreement(official, s) for s in sessions]
        (OUT / "real-run-sessions.json").write_text(json.dumps({
            "record": "judge-stability-real-flagged-run",
            "run_id": args.stability, "n_sessions": 5,
            "verdict_agreement_with_official": f"{sum(a['verdict_agree'] for a in ags)}/5",
            "first_error_step_agreement_with_official": f"{sum(a['first_error_step_agree'] for a in ags)}/5",
            "primary_category_agreement_with_official": f"{sum(a['primary_category_agree'] for a in ags)}/5",
            "sessions": [json.loads(s.model_dump_json()) for s in sessions],
        }, indent=1))
        summary["real_run_stability"] = {
            "run_id": args.stability,
            "verdict": f"{sum(a['verdict_agree'] for a in ags)}/5",
            "step": f"{sum(a['first_error_step_agree'] for a in ags)}/5",
        }

    (OUT / "consistency-summary.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps({k: v for k, v in summary.items() if k != "rows"}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
