# API Contracts: Triage

Standard 6: every frontend call maps to exactly one backend endpoint. The CI test job runs
`tests/test_contracts.py`, which parses this table and asserts every `implemented` row exists in the
app's OpenAPI route table (the same spec served at `/openapi.json`; Swagger UI at `/docs`). The
frontend is deferred to Phase 2, so the "Frontend call" column names the planned view or action that
will consume each endpoint; the Phase 1 endpoints below are implemented and exercised live by the
smoke test.

| Frontend call (Phase 2) | Method | Path | Status | Notes |
|---|---|---|---|---|
| — (liveness probe) | GET | `/health` | implemented | Returns `{status, env}`. Used by smoke test and ops. |
| — (dev demo only) | GET | `/api/v1/demo` | implemented | Returns `{items:[...]}` from `data/synthetic/`. Development-only; **503** outside development per Standard 3. |
| — (API discovery) | GET | `/openapi.json`, `/docs` | implemented | OpenAPI spec + Swagger UI, served by FastAPI. `tests/test_contracts.py` checks this table against the spec in CI. |
| Ingest feedback batch | POST | `/api/v1/feedback/import` | implemented | Keyless bulk connector: JSON `items` or `csv_text` (exactly one), deterministic content-hash dedup, optional pre-labeled aspects stored as span-anchored claims. |
| Extract aspects (LLM) | POST | `/api/v1/feedback/{id}/aspects/extract` | implemented | Key-gated via the groundwork gateway (strict JSON schema); typed **503** without `OPENROUTER_API_KEY`. Rejected span anchors kept, never dropped. |
| Run triage loop | POST | `/api/v1/triage/run` | implemented | Deterministic: aspect-key-seeded clustering + embedding assignment, issue registry upsert, severity history append. **422** when there is nothing to triage. |
| Issue registry list | GET | `/api/v1/issues` | implemented | Issues with lifecycle state, latest severity, frequency, first/last seen. |
| Issue detail | GET | `/api/v1/issues/{id}` | implemented | Members (seeded vs embedding), transition history, severity breakdown with formula params. |
| Transition issue state | POST | `/api/v1/issues/{id}/transition` | implemented | State machine `new -> triaged -> in_progress -> fixed -> verified`; illegal moves return a typed **409**, unknown states **422**. |
| Hypothesis ledger | GET | `/api/v1/issues/{id}/hypotheses` | planned — Phase 2 | Guarded causal states, evidence checks, alternative candidate events. |
| Export ticket | POST | `/api/v1/issues/{id}/export` | planned — Phase 2 | Push to Jira / Linear with quotes, timeline, state. Consequential write — requires human approval. |
| Outcome panel | GET | `/api/v1/issues/{id}/outcome` | planned — Phase 3 | Post-fix measurement (ITS / cohort / pre-post), grade, and regression-watch status. |
| Link fix | POST | `/api/v1/issues/{id}/fix-link` | planned — Phase 3 | Attach a shipped fix and arm outcome measurement. Consequential write — requires human approval. |
