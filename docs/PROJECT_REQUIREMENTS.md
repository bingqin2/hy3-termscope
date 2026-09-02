# Project requirements

Source: `犀牛鸟开源-实战任务-混元大语言模型项目.pdf` (repo root) — 2026 Tencent Rhino-Bird
open-source practical task, Hunyuan LLM track, **Task 2: 可验证场景：过程评估与错误定位**
(verifiable scenario: process evaluation and error localization). This is an individual entry.

## Submission rules (apply to the whole repo)

1. Self-created public repository; no PR to the official Hy3 repo. ✔ github.com/bingqin2/hy3
2. README states project intro, how to run, environment requirements.
3. No hardcoded API keys — environment variables / config files only.
4. Project name and README marked as personal / activity work.
5. All model capability is called through Hy3 (https://github.com/Tencent-Hunyuan/Hy3); no training or fine-tuning.

## Task 2 requirements → where this project satisfies them

| PDF requirement | Solution |
| --- | --- |
| 基于 Hy3 构建可运行应用，产出完整解答过程 | Hy3 drives existing terminal agents (`terminus-2` primary; `mini-swe-agent` optional) through Harbor on Terminal-Bench 2.0 tasks; every step recorded in the pinned trajectory format ([ARCHITECTURE.md](ARCHITECTURE.md)) |
| 场景需存在标准答案（自拟方向允许） | Terminal-operations tasks from Terminal-Bench 2.0: every task ships an executable verifier and an oracle solution ([EVALUATOR_SPEC.md](EVALUATOR_SPEC.md) §1) |
| 评测题集：标准答案 + 可自动校验 + 难度分层 + 来源/构造/分层依据 | Pre-registered slice of 16–20 TB2 tasks (floor 12), seeded-stratified over the 3 official difficulty tiers × ≥ 6 categories; source/construction = the cited public benchmark (pinned revision); the selection protocol and per-task provenance live in the committed slice file |
| 过程正确性判定（跳步、循环、误用、遗漏、幻觉） | Hybrid evaluator: deterministic facts + prefix-replay causality + evidence-anchored Hy3 judge ([EVALUATOR_SPEC.md](EVALUATOR_SPEC.md) §3–4) |
| 错误步骤定位 | Prefix-replay causal localizer + validated judge citations; merge precedence replay > judge; honest `unlocatable` ([EVALUATOR_SPEC.md](EVALUATOR_SPEC.md) §3, §5) |
| 错误类型归类体系 | 7-category process taxonomy with terminal-domain decision rules and severity weights ([EVALUATOR_SPEC.md](EVALUATOR_SPEC.md) §2) |
| 结果正确但过程不成立的样本识别 | Derived `resolved ∧ process-invalid` status (conclusive lanes only) + mandatory human audit of every flagged-resolved run ([EVALUATOR_SPEC.md](EVALUATOR_SPEC.md) §3, §6) |
| 有效性验证 ≥ 2 项：定位准确率、误报率 | Blinded human labels on failed runs; human audit of flagged-resolved runs; discriminative fixture-tier test; ten judge-stability sessions plus one consistency session per campaign run; evaluator v1→v2 regression card against frozen labels ([EVALUATOR_SPEC.md](EVALUATOR_SPEC.md) §6) |
| 完整评测 + 结果表格 + 典型 case 归因 + 难度分层分析 | Single-pass campaign, aggregated tables, capability-cliff analysis, case studies in the report |

## Acceptance checklist (final deliverables, PDF 【产出】)

- [ ] Public repo: app source, process-evaluation module, README (intro / run / environment), `env.example`
- [ ] Eval materials: pre-registered stratified TB2 slice (16–20 tasks) + the benchmark's shipped verifiers, answer-checking via Harbor, process-evaluation scripts
- [ ] Full results: answer accuracy, process correctness rate, error-type distribution, difficulty-stratified tables
- [ ] Validation records: localization accuracy, false-positive rate, human spot-check logs (explicit denominators), judge-stability records, v1→v2 regression card
- [ ] Analysis report: design rationale, taxonomy explanation, typical cases, capability boundary / cliff analysis
- [ ] Demo GIF ≤ 2 minutes: one task solved + process-evaluated + shown in the run explorer
- [ ] Live GitHub Pages site (sections 01–06, [FRONTEND_SPEC.md](FRONTEND_SPEC.md))

## Scope notes accepted by the owner

- **Single-attempt evaluation by design.** Each task × config runs exactly once (ROADMAP decision 12) — an integrity choice, not a quota limit (quota is not binding; owner-confirmed). No repeated-run statistics; the report states this scope honestly.
- **Paper-level statistical rigor is not a goal.** Mean±SEM / Pass@k protocols are deliberately not reproduced; rates on small n are reported as raw fractions.
- **Published benchmark.** Task construction belongs to the Terminal-Bench 2.0 authors (cited, pinned revision). This project's documented contributions are the selection protocol, the process-evaluation layer (replay localization included), and its quantitative validation.
