# PRD: Triage

## Users

- **Product manager (primary).** Owns a product with a feedback stream too large to read by hand.
  Needs to know what broke, how bad it is weighted by who is hurting, and whether shipped fixes held.
- **Support lead (primary).** Sees the raw pain first, needs it deduplicated into tracked issues with
  evidence, not a rising ticket count.
- **Engineer / on-call (secondary).** Consumes issue tickets exported to Jira / Linear, complete with
  span-anchored quotes, causal timeline, and current state.
- **Open-source maintainer, non-profit, or small-product team (long tail).** The audience enterprise
  CX vendors never courted; runs Triage on their own issue stream with zero private-data dependence.

## Jobs to be done

- Turn multi-channel feedback (reviews, tickets, NPS, social) into a small set of tracked issues with
  states, owners, and evidence.
- Detect that an issue is emerging or growing *before* it shows up in aggregate sentiment.
- Align each spike to the release, deploy, pricing change, or incident that plausibly caused it — and
  keep the causal claim inside its evidence, as a guarded state.
- Measure whether a linked fix actually moved the signal, and grade it.
- Keep a regression watch armed so a resolved issue reopens if it returns.

## Non-goals

- **Not a sentiment dashboard.** Sentiment is a prioritization input, never the headline metric.
- **No individual scoring.** Emotion signals prioritize issues; they never score customers or agents,
  and there is no sentiment-based individual profiling.
- **No LLM-made decisions.** The model senses (extracts claims, drafts hypotheses). Every state
  transition, severity number, changepoint, promotion, and outcome grade is computed deterministically.
- **No causal claims beyond the evidence.** A hypothesis is never rendered as proof; promotion
  requires deterministic checks.
- **No fabricated statistical power.** Below the detector's power threshold, Triage degrades honestly
  to evidence collection and says so, rather than manufacturing a trend.
- **Phase-boundaried scope.** No changepoint alignment or outcome measurement in Phase 1; no frontend
  before Phase 2 (see ROADMAP.md).

## Success metrics (targets, enforced by the eval harness)

These are goals the Phase-1 eval harness will measure against a planted-defect synthetic stream, not
achieved results. The harness currently raises `NotImplementedError` on purpose (see EVAL.md).

- **Issue detection precision and recall** against known injected issues.
- **Detection lag** — time from an issue's true onset to Triage flagging it.
- **State-transition accuracy** — transitions fire on the correct measured thresholds.
- **Hypothesis hit rate** — drafted hypotheses matched against planted causal events, scored by
  guarded-state correctness rather than confident-sounding prose.
- **Outcome-measurement correctness** on simulated fixes (did the grade match the injected effect?).
- **Span fidelity** of extracted quotes, audited with an NLI entailment gate.

Each metric is published per release once the harness is implemented.
