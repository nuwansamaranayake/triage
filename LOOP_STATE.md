# LOOP_STATE — Triage Phase 1

Branch: `phase-1`. Ledger cell: Triage Phase 1. BLUEPRINT L555-559 (MVP path, Phase 1): **one
source, aspect extraction, seeded clustering, issue registry with state machine, severity
formula.** Phase 1 cut (binding scope): bulk JSON/CSV import (the keyless connector), LLM
aspect extraction key-gated via the groundwork gateway PLUS a keyless pre-labeled-aspects
entry path, deterministic aspect-key-seeded clustering with embedding assignment of unlabeled
items (no LLM in clustering), issue registry state machine `new -> triaged -> in_progress ->
fixed -> verified` with illegal transitions rejected loudly, and a documented deterministic
severity formula monotone in frequency. Exit also requires: real eval meeting EVAL.md bounds
(byte-reproducible, keyless), smoke through the real persisted loop, alembic migration with
table count updated, CI eval flipped to required, and the flywheel duty (a Seismograph
contract ships with the LLM stage).

## Milestones (commit each; gate.py after each)

- [x] M1  EVAL.md numeric thresholds first; LOOP_STATE; branch `phase-1`
- [ ] M2  engine/aspects: AspectClaim on groundwork.Claim (type issue_aspect, span-anchored
         quote); LLM extractor via gateway (strict JSON schema); canonicalize() anchor
         tokens (model labels are not identity — CareerCompiler FAIL-0003); keyless
         pre-labeled entry path (+tests, stub gateway)
- [ ] M3  engine/clustering: deterministic aspect-key-seeded clusters + HashingEmbedder
         cosine assignment of unlabeled items (threshold, sorted tie-break, no LLM);
         engine/registry: state machine with typed IllegalTransition; engine/severity:
         severity = frequency x recency_weight x impact_weight, monotone in frequency
         (+tests each)
- [ ] M4  scripts/eval.py: golden feedback set (30 items, labeled aspects, known clusters,
         planted severity ordering, planted illegal transitions) meeting the EVAL.md bounds;
         byte-reproducible (fixed reference clock from the golden file)
- [ ] M5  schema + alembic 0002 (sources, feedback_items, aspects, clusters,
         cluster_members, issues, issue_transitions, severity_scores)
         EXPECTED_TABLE_COUNT=9; API: import (keyless bulk JSON/CSV), key-gated extract,
         triage run (persisted deterministic loop), issues list/detail, transition endpoint
         (409 on illegal); CLI `python -m app.cli triage`; smoke = real keyless processing
         loop; Dockerfile migrate-on-start
- [ ] M6  flywheel: contracts/aspect-extraction-stability.yaml (Seismograph DSL, validated
         via the Seismograph loader); key-gated eval_llm.py observed for real (recall +
         paraphrase jaccard on canonical anchors)
- [ ] M7  CI eval -> required; README/contracts.md/CHANGELOG/EVAL.md truth pass; full gate +
         migration check + prod-guard + byte-reproducibility check

## DECISION log

- Keyless entry path: bulk import accepts pre-labeled aspects (structured feedback — ticket
  categories, form-tagged reviews — a real product path, not a fallback). The LLM extraction
  endpoint refuses loudly with a typed 503 when OPENROUTER_API_KEY is empty (Standard 3: no
  silent fallback between paths).
- Clustering is deterministic end to end: canonical aspect keys seed clusters; labeled items
  join by their aspect keys; unlabeled items are assigned by HashingEmbedder cosine to
  cluster centroids with a minimum-similarity threshold and sorted tie-breaks. No LLM call
  anywhere in clustering.
- Model-invented aspect labels are not stable identity: canonicalize() reduces labels to
  sorted anchor tokens before any comparison (CareerCompiler FAIL-0003 lesson applied from
  the start).
- Severity is a documented formula: frequency x recency_weight x impact_weight, where
  recency_weight is the mean exponential half-life decay of item ages and impact_weight the
  mean sentiment impact. Holding the weights fixed it is strictly increasing in frequency;
  the eval plants both an ordering and a duplication check.
- Aspect atom = groundwork.Claim (type issue_aspect, evidence_ref.span into the feedback
  text) extended with app fields (aspect_key, label, sentiment, provenance). The portfolio
  spine is reused, not reinvented.
- CSV and JSON import share one endpoint: the body carries either `items` or `csv_text`,
  exactly one (422 otherwise). Both are keyless product paths.

## BLOCKED

(none)

## Next task

M2 — engine/aspects with tests (stub gateway, no network).
