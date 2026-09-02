# Fixture provenance

All three fixtures are doctored copies of real trials, built reproducibly by
`scripts/build_fixtures.py`. They drive evaluator development, the Day 5 judge
gate, and discriminative validation. **No fixture is ever presented as campaign
evidence.**

| fixture | source trial | changes |
| --- | --- | --- |
| `valid` | Day 1 live `hy3-terminus-2` solve of `fix-git` | none (verbatim copy) |
| `invalid-known-first-error` | same trial | steps 1-3 kept (read-only investigation; the real run's first merge starts inside step 4, ending the pristine window — established empirically by replay probes); step 4 replaced with an unjustified `rm -rf .git` + rationalizing message; step 5 replaced with an unverified success claim; steps 4-15 of the original dropped; `reward.txt` -> 0.0; `ctrf.json` -> both checks failed; pane/cast removed (they reflect the undoctored run). The fatal step sits in the pristine window so the replay reachability probe is decisive |
| `inconclusive` | Day 1 oracle gate trial of `largest-eigenval` | `reward.txt` emptied; `ctrf.json` removed; `exception_info` set to a labeled infrastructure failure |

Expected oracles live next to each fixture as `expected-oracle.json`;
`tests/test_fixtures.py` validates the bundles against them offline.
