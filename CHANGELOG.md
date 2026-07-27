# Changelog

All notable changes to Triage are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Phase 1 core loop (branch `phase-1`): keyless bulk JSON/CSV import with deterministic
  content-hash dedup and pre-labeled span-anchored aspect claims; key-gated LLM aspect
  extraction via the groundwork gateway (typed 503 without a key); deterministic
  aspect-key-seeded clustering with hashing-embedding assignment; issue registry with the
  `new -> triaged -> in_progress -> fixed -> verified` state machine (illegal transitions
  rejected with a typed 409); documented severity formula
  (frequency x recency_weight x impact_weight, monotone in frequency); severity history;
  CLI `python -m app.cli triage`.
- Schema: 8 app tables applied from `app.db.metadata` by alembic `0002_real_schema`;
  observed `MIGRATION OK: 9 tables` (`EXPECTED_TABLE_COUNT=9`).
- Eval harness (`scripts/eval.py`), bounds written before the code: observed cluster
  purity 1.0, assignment coverage 1.0, state-machine legality 1.0, severity
  monotonicity 1.0; byte-reproducible report; CI eval job flipped to
  "eval (required)".
- Key-gated LLM eval (`scripts/eval_llm.py`) observed for real on
  google/gemini-2.5-flash: planted-aspect recall 1.00, paraphrase jaccard (min) 0.86 on
  canonical anchors; Seismograph stability contract
  `contracts/aspect-extraction-stability.yaml` validated against the Seismograph DSL
  loader.
- Failure gallery entries FAIL-0004..0006 (truststore/pip recursion, sqlite naive
  datetimes, paraphrase label instability) with root-cause fixes.

### Changed
- Dependency on `aignite-groundwork` switched from an editable path source to a pinned git
  dependency (`git+https://github.com/nuwansamaranayake/groundwork@v0.1.0`) so standalone clones and CI resolve
  it without a sibling checkout. PyPI publication planned at first release.
- `scripts/check_migrations.py` now uses `DATABASE_URL` with the declared psycopg v3 driver
  unmodified, fixing a clean-machine `make migrate` failure (see FAILURES.md FAIL-0002).
- README truth pass: scaffold status block, `(the design)` heading, "What exists today (verified)"
  section, scoped/dated novelty, dual-path Quickstart, em-dash sweep.
- CI: Python matrix (3.12, 3.13); eval job labeled "eval (Phase 1 pending)".

### Added
- `CODE_OF_CONDUCT.md` (Contributor Covenant 2.1) and a SECURITY.md vulnerability-reporting policy.

## [0.1.0] - 2026-07-21
### Added
- Engineering harness scaffold: governed doc set, config guard, verification gates,
  smoke test against a real business endpoint, migration-count check, CI pipeline,
  and a synthetic dataset so the demo runs with zero external keys.
