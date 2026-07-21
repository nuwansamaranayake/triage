# EVAL: Triage

## What "good" means

Triage is good when it behaves like an honest issue tracker under statistical uncertainty, not a
confident-sounding dashboard. Concretely: it detects real issues early, without inventing phantom
ones; its lifecycle states change for the right measured reasons; its causal hypotheses stay inside
their evidence; and its post-fix grades match what actually happened. A tool that files tickets and
reopens them can be wrong — so "good" is defined by measured behavior against a known-truth stream,
not by prose.

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

## Current status: not yet implemented

`make eval` runs `scripts/eval.py`, which **raises `NotImplementedError` on purpose** today. The
thresholds and metrics above are **targets the Phase-1 harness will enforce**, not measurements that
have been taken. Implementing the harness so `make eval` gates releases is an explicit Phase-1
deliverable (see ROADMAP.md). Until then, any claim of a passing eval would itself be the kind of
silent-success theater the doctrine forbids — so the harness fails loud instead.

Once implemented, a release is gated on the eval report: no green eval, no release.
