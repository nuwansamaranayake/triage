# Triage

**Your feedback stream is a bug tracker, not a mood ring.** Triage turns raw feedback into issue
tickets with lifecycles, links every spike to the release or event that plausibly caused it, measures
whether the fix worked, and reopens the issue if it regresses.

## What it is

Triage converts high-volume, multi-channel customer feedback — reviews, support tickets, NPS
verbatims, social mentions — into a small number of tracked, evidenced, causally-annotated issues,
each with a state, an owner, an outcome measurement, and a regression watch. It rejects the sentiment
dashboard nobody acts on: "sentiment down 3 points" carries no action.

The buyers who move products — PMs and support leads, especially at companies priced out of
enterprise CX platforms — need what a bug tracker gives: what broke, when, what plausibly caused it,
how bad weighted by who is hurting, and whether last month's fix held. As open source, it also serves
the long tail vendors ignore: small products, non-profits, and OSS maintainers triaging their own
streams.

## How it works

1. **Ingest deterministically.** Dedup, spam filter, and PII redaction run before any model call.
2. **Sense with the LLM.** Aspect and quote extraction produce span-anchored claims — every quote
   points back to an exact source span.
3. **Cluster and register.** Seeded, stability-checked clustering feeds an Issue Registry where each
   issue is an entity on a state machine (`emerging -> growing -> peaked -> resolved -> regressed`),
   transitions gated on measured volume and velocity thresholds plus hysteresis, never on LLM vibes.
4. **Score honestly.** Severity is a formula (`volume x velocity x emotional intensity x customer
   weight`). Prevalence is selection-bias-adjusted with uncertainty where behavioral data exists —
   and says so where it does not.
5. **Align causally.** A changepoint detector (PELT / CUSUM, with false-discovery control) finds when
   a trajectory shifted and aligns it to the team's event timeline. The LLM drafts a hypothesis into
   a guarded ledger — `observed_signal -> plausible_hypothesis -> supported -> contradicted ->
   inconclusive` — where promotion requires deterministic evidence checks, not narrative confidence.
6. **Close the loop.** When a fix is linked, Triage runs the measurement it can honestly support
   (interrupted time-series, cohort comparison, or pre/post with stated limits) and grades it. The
   regression watch stays armed and reopens the issue if the pattern returns.

## The unique bet

Incumbents ship taxonomy dashboards: sentiment trends, theme clouds, drill-downs. Triage is the only
open feedback tool built as an issue tracker with causal timeline alignment, guarded hypothesis
states, selection-bias-corrected prevalence, post-fix outcome grading, and regression watches — where
sentiment is a prioritization input, not the headline. The bet: statistical honesty is a product
feature. A tool that can be wrong — it files tickets and reopens them — changes engineering behavior
in a way a mood dashboard, which can never be wrong, never does.

## Quickstart (local, zero external keys)

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows  (source .venv/bin/activate on POSIX)
pip install -e ../groundwork      # sibling shared library (uv users: uv sync)
pip install -e .[dev]
copy .env.example .env            # leave keys blank; the demo runs on synthetic data
uvicorn app.main:app --reload
```

In another shell:

```bash
set API_PORT=8000 && set SMOKE_TEST_TOKEN=dev && python scripts/smoke_test.py   # -> SMOKE OK
```

The `/api/v1/demo` endpoint serves the synthetic dataset in `data/synthetic/` — no OpenRouter
key, Postgres, or Redis needed to see the app respond. Those are required only for Phase 1
features (real extraction, persistence, migrations).

## Demo

A screenshot and GIF of the issue registry, hypothesis ledger, and outcome panel land in Phase 2
with the Next.js frontend. Until then, `GET /api/v1/demo` returns the synthetic issue records behind
those views.

## Doctrine

The LLM senses; deterministic code decides; humans approve action; every claim carries provenance.
The operational rules that enforce this — fail loud, smoke-test real endpoints, no silent fallbacks —
live in [DOCTRINE.md](DOCTRINE.md).
