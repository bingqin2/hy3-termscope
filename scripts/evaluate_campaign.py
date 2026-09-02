"""Import campaign trials and run the quota-free and semantic lanes.

Per finished run in ~/termscope-work/campaign-manifest.json:
  results/per_run/<config>__<task>/bundle.json         immutable RunBundle
  results/per_run/<config>__<task>/deterministic.json  DeterministicFacts
  results/per_run/<config>__<task>/judge.json          JudgeResult (skipped when inconclusive)

Lane outputs are written once and never overwritten (single evaluation per
stored trajectory, decision 12). The merged EvaluationResult is assembled
separately once the replay lane has run on failed/flagged runs.

Blinding (decision 17): verdicts and first-error steps are never printed
unless --show-verdict is passed explicitly.

Requires OPENAI_API_KEY / OPENAI_BASE_URL in the environment for the judge.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

from termscope.contracts import AgentConfig, TaskRef
from termscope.evaluator.deterministic import evaluate_deterministic
from termscope.evaluator.judge import JudgeConfig, run_judge
from termscope.importer import import_trial

REPO = Path(__file__).resolve().parent.parent
WORK = Path.home() / "termscope-work"
MANIFEST = WORK / "campaign-manifest.json"
PER_RUN = REPO / "results" / "per_run"
GIT_PIN = "69671fbaac6d67a7ef0dfec016cc38a64ef7a77c"

prereg = json.loads((REPO / "data" / "slices" / "preregistration.json").read_text())
CONFIGS = {c["config_id"]: c for c in prereg["configs"]}
slice_tasks = {t["name"]: t for t in json.loads((REPO / "data" / "slices" / "slice-v1.json").read_text())["tasks"]}
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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--show-verdict", action="store_true",
                    help="print judge verdicts (breaks blinding; explicit opt-in)")
    ap.add_argument("--no-judge", action="store_true", help="import + deterministic only")
    ap.add_argument("--retry-unavailable", action="store_true",
                    help="re-measure runs whose judge lane returned 'unavailable' "
                         "(apparatus failure, decision-12 exception); the earlier "
                         "result is archived as judge.attemptN.json, never deleted")
    args = ap.parse_args()

    manifest = json.loads(MANIFEST.read_text())
    cfg = JudgeConfig(raw_dir=REPO / ".local" / "judge-raw")
    transport = None if args.no_judge else transport_from_env(cfg)

    counts = {"imported": 0, "deterministic": 0, "judged": 0, "judge_skipped_inconclusive": 0,
              "judge_existing": 0, "no_trial": 0}
    for key, run in sorted(manifest["runs"].items()):
        if run.get("status") != "finished" or not run.get("trial_dir"):
            counts["no_trial"] += 1
            continue
        task, config_id = run["task"], run["config_id"]
        t = slice_tasks[task]
        c = CONFIGS[config_id]
        out = PER_RUN / key
        out.mkdir(parents=True, exist_ok=True)

        bundle_path = out / "bundle.json"
        if bundle_path.exists():
            from termscope.contracts import RunBundle
            bundle = RunBundle.model_validate_json(bundle_path.read_text())
        else:
            bundle = import_trial(
                Path(run["trial_dir"]),
                task=TaskRef(name=task, git_commit=GIT_PIN, difficulty=t["difficulty"],
                             category=t["category"]),
                config=AgentConfig(config_id=config_id, agent=c["agent"], model=c["model"]),
            )
            bundle_path.write_text(bundle.model_dump_json(indent=1))
            counts["imported"] += 1

        det_path = out / "deterministic.json"
        facts = evaluate_deterministic(bundle)
        if not det_path.exists():
            det_path.write_text(facts.model_dump_json(indent=1))
            counts["deterministic"] += 1

        judge_path = out / "judge.json"
        if args.no_judge:
            continue
        if judge_path.exists():
            prior = json.loads(judge_path.read_text())
            if not (args.retry_unavailable and prior.get("status") in ("unavailable", "context_limit")):
                counts["judge_existing"] += 1
                continue
            n = 1 + len(list(out.glob("judge.attempt*.json")))
            judge_path.rename(out / f"judge.attempt{n}.json")
            counts["judge_remeasured"] = counts.get("judge_remeasured", 0) + 1
            print(f"re-measuring {key}: prior judge result archived as judge.attempt{n}.json",
                  flush=True)
        if bundle.outcome == "inconclusive":
            counts["judge_skipped_inconclusive"] += 1
            continue
        n_before = len(usage_log)
        result = run_judge(bundle, facts, instruction_for(task), transport, cfg)
        judge_path.write_text(result.model_dump_json(indent=1))
        (out / "judge-usage.json").write_text(json.dumps(usage_log[n_before:], indent=1))
        counts["judged"] += 1
        line = f"judged {key}: status={result.status}"
        if args.show_verdict:
            line += f" verdict={result.verdict} first_error={result.first_error}"
        print(line, flush=True)

    spend = {
        "judge_calls": len(usage_log),
        "judge_prompt_tokens": sum(u["prompt_tokens"] or 0 for u in usage_log),
        "judge_completion_tokens": sum(u["completion_tokens"] or 0 for u in usage_log),
    }
    print(json.dumps({"counts": counts, "judge_spend_this_invocation": spend}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
