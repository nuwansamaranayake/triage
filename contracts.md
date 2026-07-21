# API Contracts: Triage

Standard 6: every frontend call maps to exactly one backend endpoint, and CI diffs this file against
the live OpenAPI spec served at `/openapi.json` (Swagger UI at `/docs`). The frontend is deferred to
Phase 2, so the "Frontend call" column names the planned view or action that will consume each
endpoint; today only the two implemented endpoints exist and are exercised by the smoke test.

| Frontend call (Phase 2) | Method | Path | Status | Notes |
|---|---|---|---|---|
| — (liveness probe) | GET | `/health` | implemented | Returns `{status, env}`. Used by smoke test and ops. |
| — (dev demo only) | GET | `/api/v1/demo` | implemented | Returns `{items:[...]}` from `data/synthetic/`. Development-only; **503** outside development per Standard 3. |
| — (API discovery) | GET | `/openapi.json`, `/docs` | implemented | OpenAPI spec + Swagger UI, served by FastAPI. CI diffs this file against the spec. |
| Ingest feedback batch | POST | `/api/v1/feedback:ingest` | planned — Phase 1 | Deterministic dedup, spam filter, PII redaction before any model call. |
| Issue registry list | GET | `/api/v1/issues` | planned — Phase 1 | Issues with lifecycle state, severity, first/last seen; filter by state and segment. |
| Issue detail | GET | `/api/v1/issues/{id}` | planned — Phase 1 | Span-anchored evidence quotes, transitions, severity breakdown, prevalence estimate. |
| Hypothesis ledger | GET | `/api/v1/issues/{id}/hypotheses` | planned — Phase 2 | Guarded causal states, evidence checks, alternative candidate events. |
| Export ticket | POST | `/api/v1/issues/{id}/export` | planned — Phase 2 | Push to Jira / Linear with quotes, timeline, state. Consequential write — requires human approval. |
| Outcome panel | GET | `/api/v1/issues/{id}/outcome` | planned — Phase 3 | Post-fix measurement (ITS / cohort / pre-post), grade, and regression-watch status. |
| Link fix | POST | `/api/v1/issues/{id}/fix-link` | planned — Phase 3 | Attach a shipped fix and arm outcome measurement. Consequential write — requires human approval. |
