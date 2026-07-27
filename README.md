# Triage

> **Status: Phase 1 core loop released (v0.3.0).** Bulk import, aspect claims,
> seeded clustering, an issue registry with a real state machine, and a documented severity
> formula are implemented, tested, and gated: the golden eval suite is a required CI check
> and every number below was observed, not promised. Changepoint alignment, hypothesis
> ledger, and outcome measurement are Phase 2/3. [ROADMAP.md](ROADMAP.md) shows what exists
> today versus what is next.

**Your feedback stream is a bug tracker, not a mood ring.** Triage turns raw feedback into issue
tickets with lifecycles, links every spike to the release or event that plausibly caused it, measures
whether the fix worked, and reopens the issue if it regresses.

## What it is

Triage converts high-volume, multi-channel customer feedback, reviews, support tickets, NPS
verbatims, social mentions, into a small number of tracked, evidenced, causally-annotated issues,
each with a state, an owner, an outcome measurement, and a regression watch. It rejects the sentiment
dashboard nobody acts on: "sentiment down 3 points" carries no action.

The people who move products, PMs and support leads, especially at companies priced out of
enterprise CX platforms, need what a bug tracker gives: what broke, when, what plausibly caused it,
how bad weighted by who is hurting, and whether last month's fix held. As open source, it also serves
the long tail vendors ignore: small products, non-profits, and OSS maintainers triaging their own
streams.

## How it works (the design)

1. **Ingest deterministically.** Dedup, spam filter, and PII redaction run before any model call.
2. **Sense with the LLM.** Aspect and quote extraction produce span-anchored claims: every quote
   points back to an exact source span.
3. **Cluster and register.** Seeded, stability-checked clustering feeds an Issue Registry where each
   issue is an entity on a state machine (`emerging -> growing -> peaked -> resolved -> regressed`),
   transitions gated on measured volume and velocity thresholds plus hysteresis, never on LLM vibes.
4. **Score honestly.** Severity is a formula (`volume x velocity x emotional intensity x customer
   weight`). Prevalence is selection-bias-adjusted with uncertainty where behavioral data exists,
   and says so where it does not.
5. **Align causally.** A changepoint detector (PELT / CUSUM, with false-discovery control) finds when
   a trajectory shifted and aligns it to the team's event timeline. The LLM drafts a hypothesis into
   a guarded ledger: `observed_signal -> plausible_hypothesis -> supported -> contradicted ->
   inconclusive`, where promotion requires deterministic evidence checks, not narrative confidence.
6. **Close the loop.** When a fix is linked, Triage runs the measurement it can honestly support
   (interrupted time-series, cohort comparison, or pre/post with stated limits) and grades it. The
   regression watch stays armed and reopens the issue if the pattern returns.

## What exists today (verified)

The Phase 1 core loop is enforced by gates, not promised. Checks you can run in five minutes:

1. `python scripts/smoke_test.py` against a running instance drives the real keyless loop:
   bulk import with pre-labeled aspects, a deterministic triage run, an issue listed with
   its severity, a legal state transition accepted, and an illegal one rejected with a
   typed 409. Observed: `SMOKE OK`.
2. `python scripts/eval.py`: the golden 30-item feedback suite against pre-written bounds.
   Observed: cluster purity 1.0, assignment coverage 1.0, state-machine legality 1.0,
   severity monotonicity 1.0, byte-reproducible report. Required in CI; exits nonzero on
   any miss.
3. `alembic upgrade head` then `python scripts/check_migrations.py`: observed
   `MIGRATION OK: 9 tables` (8 app tables plus alembic_version, asserted, not assumed).
4. Set `APP_ENV=production` and call `/api/v1/demo`: returns 503, because fixture data
   outside development is forbidden by code, not by convention.
5. The LLM stage is measured, key-gated, and never silently skipped: observed
   planted-aspect recall 1.00 and paraphrase jaccard 0.86 on canonical anchors
   (`eval_report_llm.md`), with a Seismograph stability contract in `contracts/`. Without
   a key the extraction endpoint refuses with a typed 503 and the keyless pre-labeled
   import path remains a full product path.

## The unique bet

Incumbents ship taxonomy dashboards: sentiment trends, theme clouds, drill-downs (the tools we reviewed as of July 2026). No open feedback tool we reviewed (July 2026) is built as an issue tracker with causal timeline alignment, guarded hypothesis states, bias-corrected prevalence, post-fix outcome grading, and regression watches. That is the bet.

The full scoped novelty statement, with the field surveyed, is in [PRD.md](PRD.md).

The bet: statistical honesty is a product feature. A tool that can be wrong, it files tickets and reopens them, changes engineering behavior in a way a mood dashboard, which can never be wrong, never does.

## Quickstart (local, zero external keys)

### Standalone clone

```bash
python -m venv .venv
source .venv/bin/activate         # POSIX     (.venv\Scripts\activate on Windows)
pip install -e .[dev]             # groundwork resolves from GitHub automatically
cp .env.example .env              # POSIX     (copy .env.example .env on Windows)
uvicorn app.main:app --reload
```

### Developing the whole portfolio (sibling checkout, editable)

```bash
git clone https://github.com/nuwansamaranayake/groundwork ../groundwork
pip install -e ../groundwork
pip install -e .[dev]
```

Then, in another shell:

```bash
export API_PORT=8000 SMOKE_TEST_TOKEN=dev-smoke-token && python scripts/smoke_test.py   # POSIX -> SMOKE OK
set API_PORT=8000 && set SMOKE_TEST_TOKEN=dev-smoke-token && python scripts/smoke_test.py  # Windows
```

The token must match `SMOKE_TEST_TOKEN` in your `.env` (the server side); `.env.example` sets
`dev-smoke-token`, so the export above works against an unmodified `cp .env.example .env`.

Zero-key paths that work out of the box: `python -m app.cli triage --data
data/synthetic/golden/golden.json` runs the full deterministic loop in memory (no database,
no network), and `/api/v1/demo` serves the synthetic dataset in development. Postgres is
needed for the persisted loop (import, triage run, issue registry); an OpenRouter key only
for LLM aspect extraction.

## Demo

A screenshot and GIF of the issue registry, hypothesis ledger, and outcome panel land in Phase 2
with the Next.js frontend. Until then, `GET /api/v1/demo` returns the synthetic issue records behind
those views.

## Doctrine

The LLM senses; deterministic code decides; humans approve action; every claim carries provenance.
The operational rules that enforce this, fail loud, smoke-test real endpoints, no silent fallbacks,
live in [DOCTRINE.md](DOCTRINE.md).
