# Changelog

All notable changes to Triage are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Removed
- Unused `sentence-transformers` dependency (and the CUDA torch stack it pulled). No Phase 1
  code imports it; production images drop from ~5.7 GB toward the ~0.5 GB baseline
  (FAILURES FAIL-0010).

### Security
- Business read endpoints (GET /api/v1/issues and /issues/{id}) now require the same bearer token as writes. They
  previously served real production data to unauthenticated callers (FAILURES FAIL-0009).

## [0.2.0] - 2026-07-23

### Fixed
- Adversarial review wave (10 findings, see FAILURES.md FAIL-0007): LLM aspect extraction
  no longer runs its network call inside an open DB transaction (read session closes
  before the gateway call; results land in a second, short write transaction), and a
  retried extract now replaces the item's previous `llm_extracted` claims instead of
  appending duplicates that skewed the sentiment majority and severity.
- Issue transitions use a state-guarded UPDATE: a concurrent transition that lands first
  turns the second request into a typed 409 (`concurrent_transition`) instead of a
  duplicate/self-loop transition row.
- Import dedup identity now includes `external_id` when present, so distinct records with
  identical text from the same source count as distinct observations.
- Cluster label majority tie-breaks are lexicographic (total order) instead of set
  iteration order, which varied with `PYTHONHASHSEED` across processes.
- `scripts/gate.py` injects one `SMOKE_TEST_TOKEN` into both the uvicorn server and the
  smoke client, so bearer auth is exercised for real on every gate run regardless of the
  local `.env`; README smoke exports aligned with `.env.example` (`dev-smoke-token`).
- `scripts/check_migrations.py` exits nonzero when `EXPECTED_TABLE_COUNT` is unset or not
  a positive integer — the Standard 4 gate can no longer pass vacuously.
- CI test job install fallbacks removed: a dependency-resolution failure now fails the
  install step with its real error instead of limping into pytest with an incomplete set.
- contracts.md's CI claim is now backed by `tests/test_contracts.py`, which asserts every
  `implemented` row against the app's OpenAPI spec.

### Security
- Added `.dockerignore` excluding `.env`, `.git`, caches, and local state: `COPY . .` was
  baking the local `.env` (live `OPENROUTER_API_KEY`) and full git history into image
  layers. The key must be rotated if any image was ever built and shared from this tree.

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
