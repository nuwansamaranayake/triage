# EVAL: Triage

## What "good" means

Triage is good when it behaves like an honest issue tracker under statistical uncertainty, not a
confident-sounding dashboard. Concretely: it detects real issues early, without inventing phantom
ones; its lifecycle states change for the right measured reasons; its causal hypotheses stay inside
their evidence; and its post-fix grades match what actually happened. A tool that files tickets and
reopens them can be wrong — so "good" is defined by measured behavior against a known-truth stream,
not by prose.

## Published limits

This sentence is what the root page publishes, verbatim. The gate fails if the page and this block drift apart.

<!-- LIMITS -->
On a golden set of 30 synthetic feedback items with 4 planted clusters, clustering is pure (1.0), every item is assigned (coverage 1.0), every legal state transition is accepted and every planted illegal one rejected (1.0), and severity ordering is monotone in frequency and recency (1.0); the set is synthetic, so it does not measure clustering quality on real customer feedback.
<!-- /LIMITS -->


## Phase 1 acceptance thresholds (written before the harness, 2026-07-27)

Phase 1 ships the deterministic core of the issue tracker (bulk import, aspect claims,
seeded clustering, issue registry state machine, severity formula), so its bounds measure
that core. The suite is deterministic and keyless: a golden feedback set of 30 synthetic
items with labeled aspects, known cluster assignments, planted illegal state transitions,
and a planted severity ordering; the deterministic HashingEmbedder and a fixed reference
clock (read from the golden file, never wall time) keep it byte-reproducible as a required
CI check. `scripts/eval.py` exits nonzero on any miss.

| Metric | Definition | Bound |
|---|---|---|
| Cluster purity | weighted mean purity of built clusters against the golden cluster labels | >= 0.85 |
| Assignment coverage | fraction of golden items assigned to some cluster (guards purity against vacuous passes) | >= 0.90 |
| State-machine legality | every planted legal transition accepted AND every planted illegal transition rejected with the typed error | = 1.00 |
| Severity monotonicity | every planted ordering pair (the more frequent and more recent issue) scores strictly higher, and duplicating an issue's item multiset strictly raises its score | = 1.00 |
| Reproducibility | two consecutive `make eval` runs | identical reports |

Aspect-extraction quality (the LLM stage) is measured separately and key-gated —
`scripts/eval_llm.py` observes planted-aspect recall >= 0.70 through the real gateway and
paraphrase jaccard >= 0.60 on canonicalized aspect anchors (never on raw model labels; the
Seismograph contract in `contracts/aspect-extraction-stability.yaml` states the same
invariant). It is reported when a key is present, never a required keyless check, and never
silently skipped: the deterministic report states loudly when the key-gated section did not
run. The detection-lag, changepoint, hypothesis, outcome, and span-NLI metrics below join in
Phase 2/3 with the code they measure.

## How `make eval` will measure it

Evaluation is planted-defect, driven by the portfolio's Seismograph harness: synthetic feedback
streams with **known injected issues, lifecycles, and causal events**. Because the ground truth is
planted, every metric below is checkable rather than vibes-based.

| Metric | What it checks |
|---|---|
| Issue detection precision / recall | Detected issues matched against injected ones — no misses, no phantoms. |
| Detection lag | Elapsed time from an issue's true onset to Triage flagging it. |
| State-transition accuracy | Lifecycle transitions fire on the correct measured volume/velocity thresholds. |
| Hypothesis hit rate | Drafted hypotheses matched to planted causal events, scored by guarded-state correctness, not narrative confidence. |
| Outcome-measurement correctness | On simulated fixes, the assigned grade matches the injected effect (or correctly reports insufficient power). |
| Span fidelity | Extracted quotes entail their cited source spans, audited with a cross-encoder NLI gate. |

Red-team prompt-injection cases (feedback text that tries to issue instructions) ship in the suite,
per the Security and Trust Baseline. Results are published per release once the harness is
implemented.

## Status

The Phase 1 harness is real: `scripts/eval.py` enforces the acceptance table above (first
published run 2026-07-27 — cluster purity 1.0, assignment coverage 1.0, state-machine
legality 1.0, severity monotonicity 1.0, all PASS, byte-reproducible; `eval_report.md`).
The CI eval job is required. The key-gated section (`scripts/eval_llm.py`) was observed
for real on google/gemini-2.5-flash: planted-aspect recall 1.00 and paraphrase jaccard
(min) 0.86 on canonical anchors (`eval_report_llm.md`) — its first run FAILED the 0.60
jaccard bound at 0.29 and the root causes were fixed in the prompt and the canonical
stemmer, not by lowering the bound (FAILURES.md FAIL-0006). The detection-lag,
changepoint, hypothesis, outcome, and span-NLI metrics below join in Phase 2/3 with the
code they measure. A release is gated on the eval report: no green eval, no release.
