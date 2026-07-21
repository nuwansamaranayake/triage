# Roadmap: Triage

Three phases, taken directly from the MVP Build Path. Each phase mirrors a GitHub milestone and a
public project board so planning and delivery discipline are visible in the commit history.

## Phase 1 — Issue registry with a state machine

*Mirrors GitHub milestone `phase-1-registry`.*

The first honest slice: one source, real extraction, and issues as entities.

- **One source: app reviews.** Deterministic ingestion — dedup, spam filter, PII redaction — before
  any model call.
- **Aspect and quote extraction (LLM).** Span-anchored claims; every quote resolves to an exact
  source span, audited by an NLI entailment gate.
- **Seeded clustering** with stability checks and minimum-support thresholds, so issues do not
  flicker.
- **Issue Registry with the state machine** (`emerging -> growing -> peaked -> resolved ->
  regressed`), transitions gated on measured volume and velocity thresholds with hysteresis.
- **Severity formula** (`volume x velocity x emotional intensity x customer weight`).
- **Eval harness implemented** so `make eval` stops raising `NotImplementedError` and gates releases.

## Phase 2 — Causal alignment, hypothesis ledger, and the frontend

*Mirrors GitHub milestone `phase-2-causal`.*

Bring in the team's own change stream and the surfaces that render it.

- **Event timeline ingestion:** releases, deploys, pricing changes, incidents.
- **Changepoint alignment** with a deterministic detector (PELT / CUSUM) and false-discovery control
  across issues.
- **Guarded hypothesis ledger** — LLM drafts, deterministic evidence checks (temporal precedence,
  cohort specificity, magnitude) promote between `observed_signal -> plausible_hypothesis ->
  supported -> contradicted -> inconclusive`.
- **Ticket export to Jira / Linear** with quotes, timeline, and current state.
- **Next.js frontend (the shared design system).** The issue registry, hypothesis ledger, and
  outcome panel become real UI; the README demo GIF and screenshot land here.

## Phase 3 — Outcome measurement, regression watch, and scale

*Mirrors GitHub milestone `phase-3-outcomes`.*

Close the loop and widen the intake.

- **Outcome measurement** — interrupted time-series, cohort comparison where a control cohort exists,
  plain pre/post with stated limitations otherwise — grading whether a linked fix moved the signal.
- **Regression watch** that re-arms on resolve and reopens an issue as `regressed` past threshold.
- **Bias-adjusted prevalence** with uncertainty intervals where behavioral data exists.
- **Multi-source ingestion** (support tickets, NPS verbatims, social mentions).
- **Weekly grounded digest** — narrated from the ledger, never beyond it.
