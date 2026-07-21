# 2. The LLM senses, deterministic code decides

Date: 2026-07-21

## Status

Accepted

## Context

Triage sits on a stream of messy, adversarial natural language — reviews, support tickets, NPS
verbatims, social mentions — and must turn it into tracked issues with states, severity numbers,
causal hypotheses, and post-fix grades. The tempting shortcut is to let a capable LLM do all of it:
read the feedback, name the issues, decide they are growing, guess the cause, and declare the fix
worked. That path produces a system whose most consequential outputs — a lifecycle transition, a
causal claim, an outcome grade — rest on model confidence that cannot be audited or reproduced. The
portfolio thesis rejects it: the LLM is a **sensor**, not a judge.

## Decision

We draw a hard line between sensing and deciding, matching this app's Deterministic vs
Non-Deterministic split.

**The LLM senses** — and only senses. Its outputs are typed, provenance-carrying claims:

- **Aspect and quote extraction:** span-anchored `AspectClaim` objects, each pointing to an exact
  `SourceSpan`, audited by an NLI entailment gate.
- **Issue naming and merge suggestions:** proposed, never auto-applied; human-confirmed.
- **Causal hypothesis drafting:** a `CausalHypothesis` written from aligned evidence, entering the
  ledger at `plausible_hypothesis` — a proposal, not a verdict.
- **Weekly digest narration:** grounded in the ledger, never beyond it.

**Deterministic code decides and computes** everything consequential:

- Ingestion, dedup, spam filter, PII redaction.
- Seeded clustering and stability checks.
- The issue state machine, transition thresholds, and hysteresis.
- The severity formula and bias-adjusted prevalence with uncertainty.
- Changepoint detection (PELT / CUSUM), false-discovery control, and event alignment.
- Hypothesis **promotion** between guarded states — gated on deterministic evidence checks (temporal
  precedence, cohort specificity, magnitude), never on narrative confidence.
- Outcome estimators (ITS / cohort compare / pre-post) and regression-watch triggers.

Humans approve anything that acts: ticket export, issue reopen, fix linkage.

## Consequences

- **Auditable and reproducible.** Every number and state transition comes from code a reviewer can
  read and re-run; the LLM's contribution is confined to claims that carry their own provenance.
- **Honesty is enforceable.** Because promotion is deterministic, a `plausible_hypothesis` cannot
  silently become "the cause"; guarded states render in every surface.
- **The failure surface shrinks and clarifies.** A hallucinated quote is caught by the span/NLI gate,
  not shipped in a ticket. Model drift changes what is *proposed*, never what is *decided*.
- **Cost:** more engineering than a prompt-and-pray pipeline — a state machine, estimators, and
  evidence-check code that a single mega-prompt would skip. We accept it; that code is the product.
