# Triage golden feedback eval report

cluster billing_charge: 6 members (5 seeded, 1 embedding), majority golden label share 6/6
cluster crash_login: 12 members (9 seeded, 3 embedding), majority golden label share 12/12
cluster dark_mode: 5 members (4 seeded, 1 embedding), majority golden label share 5/5
cluster slow_sync: 7 members (6 seeded, 1 embedding), majority golden label share 7/7
severity crash_login: frequency=12 recency=0.9390 impact=0.8500 score=9.5773
severity slow_sync: frequency=7 recency=0.7187 impact=0.9143 score=4.5999
severity billing_charge: frequency=6 recency=0.5490 impact=0.9000 score=2.9644
severity dark_mode: frequency=5 recency=0.3211 impact=0.4000 score=0.6422

| metric | value | bound | pass |
|---|---|---|---|
| cluster_purity | 1.0 | >= 0.85 | PASS |
| assignment_coverage | 1.0 | >= 0.9 | PASS |
| state_machine_legality | 1.0 | >= 1.0 | PASS |
| severity_monotonicity | 1.0 | >= 1.0 | PASS |

key-gated extraction section: run scripts/eval_llm.py (not part of this deterministic report)
