# Failure Gallery — Triage

An honest record of things that broke, why, and what changed. A curated gallery beats a buried
changelog: it is where the doctrine earns its keep. Every entry names the *reported* symptom and
the *diagnosed* root cause separately (Standard 5).

> The entry below is a seeded template. Replace it with the first real failure you diagnose.

## FAIL-0001 (template) — Demo showed no data

- **Date**: 2026-07-21
- **Surface**: `GET /api/v1/demo`
- **Reported symptom**: The demo view rendered "no data".
- **Diagnosed cause**: `data/synthetic/demo.json` existed but was an empty array. The endpoint
  correctly raised HTTP 500 (`"synthetic fixture is empty"`) instead of silently returning `[]`.
- **Root cause**: Fixture authored empty during scaffold.
- **Fix**: Populated the fixture with a non-empty synthetic dataset. The smoke test asserts
  `items` is non-empty, so this cannot regress silently.
- **Doctrine link**: Standard 3 (no silent mock/fallback) and Standard 2 (smoke asserts non-empty).

## FAIL-0002 — `make migrate` failed on a clean machine (check_migrations driver)

- **Date**: 2026-07-21
- **Surface**: `scripts/check_migrations.py` (`make migrate`)
- **Reported symptom**: The migration-count check errored immediately after a successful
  `alembic upgrade`.
- **Diagnosed cause**: The script did `DATABASE_URL.replace("+psycopg", "")`, turning
  `postgresql+psycopg://...` into a bare `postgresql://...`. SQLAlchemy routes the bare URL to the
  **psycopg2** driver, which is not a declared dependency (the apps pin `psycopg` v3). `alembic`
  itself succeeded because it kept the `+psycopg` URL, so the failure surfaced only at the check step.
- **Root cause**: Driver mismatch between the migration step (psycopg v3) and the check step (psycopg2).
- **Fix**: Use `DATABASE_URL` unmodified so the check reuses the declared psycopg v3 driver. Proven
  against a real Postgres: `MIGRATION OK: 1 tables` at `EXPECTED_TABLE_COUNT=1`, and
  `MIGRATION CHECK FAILED: expected 2 tables, found 1` (rc=1) at `EXPECTED_TABLE_COUNT=2`.
- **Doctrine link**: Standard 4 (assert the table count) and Standard 1 (fix the root cause — the
  driver — not the symptom).

## FAIL-0003 — First public CI run: smoke job died before the stack started

- **Date**: 2026-07-23
- **Surface**: GitHub Actions `smoke` job (`docker compose up -d --build`)
- **Reported symptom**: CI run red on the first push; compose exited immediately.
- **Diagnosed cause (from the run log)**: `env file ... .env not found`. `docker-compose.yml`
  declares `env_file: .env`, and `.env` is gitignored by design, so it does not exist in a CI
  checkout. A second, deterministic failure sat behind it: the Dockerfile's `pip install .` now
  resolves `aignite-groundwork` from a `git+https` URL, and `python:3.12-slim` ships no git.
- **Root cause**: The CI environment was never given the dev-shaped inputs the compose file
  assumes (env file present, git available in the build image).
- **Fix**: CI smoke job copies the committed `.env.example` to `.env` before compose (the same
  step the README gives a stranger); Dockerfile installs git before `pip install`.
- **Doctrine link**: Standard 1 (root cause from the real log, not a retry) and Standard 2 (the
  smoke gate exists to catch exactly this before anyone calls the estate "green").

## FAIL-0004 — Phase 1 venv build died in a pip build subprocess (truststore recursion)

- **Date**: 2026-07-27
- **Surface**: local Phase 1 toolchain (`pip install -e ../groundwork` into a fresh venv)
- **Reported symptom**: `RecursionError: maximum recursion depth exceeded` deep inside
  `ssl.py` while pip built the groundwork editable install.
- **Diagnosed cause**: `sitecustomize.py` (truststore `inject_into_ssl()`, required on this
  machine because the AV MITMs TLS) was written into the venv **before** the installs ran.
  pip's build-isolation subprocess imports sitecustomize and pip itself already integrates
  truststore, so SSL context attribute access recursed until the interpreter died.
- **Root cause**: injection ordering — runtime TLS shimming applied to build-time
  subprocesses that already carry their own truststore integration.
- **Fix**: install every dependency first, write `sitecustomize.py` last. The shim is needed
  for runtime LLM calls (httpx/OpenAI client), not for pip.
- **Doctrine link**: Standard 1 (the fix is the ordering, not a pip retry).

## FAIL-0005 — Second triage run crashed on datetime math (sqlite test engine)

- **Date**: 2026-07-27
- **Surface**: `POST /api/v1/triage/run` under pytest (injected sqlite engine)
- **Reported symptom**: `TypeError: can't subtract offset-naive and offset-aware datetimes`
  in the severity formula.
- **Diagnosed cause**: `feedback_items.submitted_at` is `DateTime(timezone=True)`. Postgres
  returns tz-aware values; sqlite (the test engine) returns naive ones. The severity clock
  is always tz-aware, so the subtraction blew up only on DB read-back paths.
- **Root cause**: dialect difference in datetime round-tripping, unhandled at the read
  boundary.
- **Fix**: normalize datetimes to tz-aware UTC at the DB read boundary in the triage loop
  (`_aware()` in app/routes.py). Caught by `tests/test_api.py` before the code ever ran
  against Postgres.
- **Doctrine link**: Standard 1 (fix the boundary, not the formula) and the test gate.

## FAIL-0006 — First real LLM eval: paraphrase jaccard 0.29 against a 0.60 contract

- **Date**: 2026-07-27
- **Surface**: `scripts/eval_llm.py` (key-gated, google/gemini-2.5-flash via the gateway)
- **Reported symptom**: planted-aspect recall 1.00 PASS, paraphrase jaccard 0.29 FAIL —
  the aspect-extraction stability contract missed by half.
- **Diagnosed cause (from a labeled debug run)**: on one paraphrase the model named aspects
  by the user's action ("coupon code application", "syncing with laptop") instead of the
  component+problem ("checkout crash", "slow sync"), and `canonicalize()` could not unify
  morphological variants — "syncing" did not reduce to "sync" — so anchor sets diverged.
- **Root cause**: two, both in our layer: an underspecified labeling instruction in the
  extraction prompt, and a stemmer with no gerund rule in the canonical identity function.
- **Fix**: prompt now requires component+problem noun-phrase labels; `_stem()` gained an
  `-ing` rule ("syncing"/"sync", "billing"/"bill" — golden keys updated to the new
  canonical forms). Observed after the fix: recall 1.00, paraphrase jaccard min 0.86.
- **Doctrine link**: the flywheel duty — the Seismograph contract exists precisely to catch
  label instability before it reaches clustering; bounds were not lowered to pass.

## FAIL-0007 — Adversarial review wave: 10 confirmed findings before release

- **Date**: 2026-07-27
- **Surface**: whole repo (Dockerfile, `app/routes.py`, `scripts/gate.py`,
  `scripts/check_migrations.py`, CI, contracts.md)
- **Reported symptom**: none — every gate was observed green. An adversarial code review
  against the phase-1 tree confirmed 10 defects the gates never exercised (1 critical,
  3 major, 6 minor; 1 further claim refuted on inspection).
- **Worst findings**: (1) no `.dockerignore`, so `COPY . .` baked the local `.env` — a live
  `OPENROUTER_API_KEY` — and full git history into image layers; (2) the LLM extraction
  endpoint ran its network call inside an open DB transaction, so a hung provider could pin
  pooled connections and stall every other endpoint; (3) the same endpoint was not
  idempotent — a retry appended duplicate claims, flipping sentiment majorities and
  silently deflating severity ~2.5x; (4) the gate's smoke client and the server it started
  could disagree on `SMOKE_TEST_TOKEN`, meaning the observed-green gate had never actually
  exercised bearer auth.
- **Root cause**: the gates asserted the happy path they were written for; nothing
  adversarial probed retry behavior, concurrency, container build context, or whether the
  gate's own auth leg was live. Green gates measure what they measure — nothing else.
- **Fix**: all 10 findings fixed in this wave (`.dockerignore`; read-LLM-write restructure;
  delete-and-replace idempotency; state-guarded transition UPDATE with typed 409;
  external_id in dedup identity; lexicographic label tie-break; token injected into both
  gate sides; `check_migrations.py` fails loud when `EXPECTED_TABLE_COUNT` is unset; CI
  install fallbacks removed; contracts.md claim backed by a real test). Each
  behavior-changing fix carries a regression test. The OpenRouter key is treated as
  exposed-if-ever-built and must be rotated.
- **Doctrine link**: Standard 2 (the smoke that "passed" was not exercising auth) and the
  review discipline — an adversarial pass caught before release what observed-green gates
  structurally could not.

## FAIL-0008 — Eval report embedded an environment-dependent line, breaking byte-reproducibility across environments

- **Date**: 2026-07-23
- **Surface**: `scripts/eval.py` report writer (central post-fix verification sweep)
- **Reported symptom**: the committed eval_report.md differed by one trailer line when the
  gate ran in a shell with a different OPENROUTER_API_KEY state.
- **Diagnosed cause**: the key-gated-section status note (present/absent by ambient env) was
  written into the report file, so "byte-reproducible" only held within one environment.
- **Fix**: the note now goes to stdout only; the report file is purely deterministic. Verified
  by running the eval with and without a key and comparing byte-for-byte.
- **Doctrine link**: reproducibility bounds must be environment-independent, or they are
  theater in every environment except the author's.
