# Triage

> **Status: scaffold (v0.1).** The engineering harness is built and verified: live smoke test,
> fail-loud guards, migration checks, CI. The architecture described below is the design being
> built; Phase 1 is in progress. [ROADMAP.md](ROADMAP.md) shows what exists today versus what
> is next.

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

This scaffold's doctrine is already enforced, not promised. Three checks you can run in five minutes:

1. `python scripts/smoke_test.py` against a running instance: hits real endpoints and asserts
   non-empty, schema-valid data. Passes.
2. Set `APP_ENV=production` and call `/api/v1/demo`: returns 503, because fixture data outside
   development is forbidden by code, not by convention.
3. `python scripts/eval.py`: raises loudly instead of passing vacuously. An eval that cannot
   fail is theater; the real harness lands in Phase 1.

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
export API_PORT=8000 SMOKE_TEST_TOKEN=dev && python scripts/smoke_test.py   # POSIX -> SMOKE OK
set API_PORT=8000 && set SMOKE_TEST_TOKEN=dev && python scripts/smoke_test.py  # Windows
```

The `/api/v1/demo` endpoint serves the synthetic dataset in `data/synthetic/`: no OpenRouter key, Postgres, or Redis is needed to see the app respond. Those are required only for Phase 1 features (real extraction, persistence, migrations).

## Demo

A screenshot and GIF of the issue registry, hypothesis ledger, and outcome panel land in Phase 2
with the Next.js frontend. Until then, `GET /api/v1/demo` returns the synthetic issue records behind
those views.

## Doctrine

The LLM senses; deterministic code decides; humans approve action; every claim carries provenance.
The operational rules that enforce this, fail loud, smoke-test real endpoints, no silent fallbacks,
live in [DOCTRINE.md](DOCTRINE.md).
