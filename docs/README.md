# Documentation

This directory is the source of truth for scope, design, planning, and progress.

## Documents

| Document | Purpose | Update when |
| --- | --- | --- |
| [PROJECT_REQUIREMENTS.md](PROJECT_REQUIREMENTS.md) | Extracted Task 2 requirements, submission rules, acceptance checklist | The instruction PDF's interpretation changes |
| [ROADMAP.md](ROADMAP.md) | Decisions, 10-day outcome sequence, cut order, no-go list, risks | A day starts, finishes, or changes scope |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Components, repository layout, stack, data flow, schema overview | Implementation evidence changes a technical decision |
| [EVALUATOR_SPEC.md](EVALUATOR_SPEC.md) | Evaluation set, error taxonomy, deterministic / replay / LLM lanes, merge policy, metrics, validation protocol | Validation evidence changes evaluator behavior |
| [FRONTEND_SPEC.md](FRONTEND_SPEC.md) | Site sections, design language, data contract, isolated-page publish workflow | The site's scope or data contract changes |
| [DEVELOPMENT_SETUP.md](DEVELOPMENT_SETUP.md) | Prerequisites, environment configuration, commands, working policies | Tooling or policy changes |
| [NEXT_STEPS.md](NEXT_STEPS.md) | The single next approved action | The current action completes or changes |

## Practice

- Requirements stay separate from implementation choices.
- The roadmap is updated at milestone boundaries only; day-to-day detail lives in NEXT_STEPS.md.
- A fixed decision changes only with recorded implementation evidence.
- Nothing is staged, committed, or pushed except on the owner's explicit instruction.
