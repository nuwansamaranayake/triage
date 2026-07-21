# SECURITY: Triage

Triage inherits the AiGNITE Security and Trust Baseline. Its two reference frameworks are the
**OWASP Top 10 for LLM Applications (2025)** and the **NIST AI Risk Management Framework — Generative
AI Profile (NIST AI 600-1)**. This app is a special case: it ingests untrusted, adversarial text
(reviews, social mentions) at high volume, and it reads business-internal data (event timelines,
plan tiers). Both are treated as untrusted input at their trust boundary.

## OWASP LLM Top 10 (2025) mapping

| ID | Risk | Triage control |
|---|---|---|
| LLM01 | Prompt Injection | Feedback text is untrusted **data**, never instructions. System prompt and content travel in separate channels; extraction returns typed claims only. Red-team injection cases ship in the eval suite. |
| LLM02 | Sensitive Information Disclosure | Deterministic **PII redaction at ingestion, before any model call**. Cohort views enforce a minimum cohort size to prevent re-identification. A local-model mode allows fully private operation. |
| LLM05 | Improper Output Handling | LLM output is validated against Pydantic claim schemas; quotes must entail their source span (NLI gate) or are dropped. No LLM output is executed, and no causal claim is rendered without its guarded state. |
| LLM06 | Excessive Agency | The LLM decides nothing. State transitions, severity, changepoints, and hypothesis promotion are computed deterministically. Ticket export and issue reopen are consequential writes requiring human approval; tools are allowlisted with schema-validated arguments and idempotency keys. |
| LLM08 | Vector & Embedding Weaknesses | Embeddings are computed from redacted text only. Clustering is seeded and stability-checked with minimum-support thresholds, limiting poisoning and phantom clusters. |
| LLM09 | Misinformation | Guarded hypothesis states (`observed_signal -> ... -> supported`) with deterministic promotion checks. Below the detector's statistical power, Triage degrades honestly to evidence collection and says so. |
| LLM10 | Unbounded Consumption | Hard budgets on tokens, tool calls, and loop depth. A runaway extraction or agent loop is treated as a security incident, not a quirk. |

## NIST Generative AI Profile

Triage instruments the NIST AI RMF functions rather than asserting them. **Map:** trust boundaries,
the claim data model, and known failure modes are documented (this file, RISKS.md, FAILURES.md).
**Measure:** the planted-defect eval harness and per-call traces (model, version, prompt hash,
temperature, latency, cost, claims) make behavior auditable. **Manage:** guarded states, human
approval on writes, and armed regression watches keep probabilistic output from acting unchecked.
**Govern:** ADRs and DOCTRINE.md record the judgment behind each control. Emotion signals prioritize
issues only — never scoring individual customers or agents — enforcing the no-surveillance-creep
boundary.

## Secrets

No provider SDK is called directly; the `groundwork` gateway reads `OPENROUTER_API_KEY` from the
environment and pins model IDs. `.env` is gitignored and never committed; `.env.example` ships with
blank keys. The demo runs on synthetic data with **no keys set at all** — keys are required only for
Phase 1 extraction, persistence, and migrations.
