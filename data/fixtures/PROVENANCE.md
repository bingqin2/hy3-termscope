# Fixture provenance

All three fixtures are doctored copies of real trials, built reproducibly by
`scripts/build_fixtures.py`. They drive evaluator development, the Day 5 judge
gate, and discriminative validation. **No fixture is ever presented as campaign
evidence.**

| fixture | source trial | changes |
| --- | --- | --- |
| `valid` | Day 1 live `hy3-terminus-2` solve of `fix-git` | none (verbatim copy) |
| `invalid-known-first-error` | same trial | steps 1-9 kept; step 10 replaced with an unjustified `rm -rf .git` + rationalizing message; step 11 replaced with an unverified success claim; steps 12-15 dropped; `reward.txt` -> 0.0; `ctrf.json` -> both checks failed; pane/cast removed (they reflect the undoctored run) |
| `inconclusive` | Day 1 oracle gate trial of `largest-eigenval` | `reward.txt` emptied; `ctrf.json` removed; `exception_info` set to a labeled infrastructure failure |

Expected oracles live next to each fixture as `expected-oracle.json`;
`tests/test_fixtures.py` validates the bundles against them offline.
