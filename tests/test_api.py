import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient

from app import db
from app.main import app

ITEMS = [
    {"external_id": "r1", "submitted_at": "2026-06-30T09:00:00Z",
     "text": "App crashes on login every single time since the update.",
     "aspects": [{"label": "login crash", "sentiment": "negative",
                  "quote": "crashes on login"}]},
    {"external_id": "r2", "submitted_at": "2026-06-29T09:00:00Z",
     "text": "Login crashes after I enter my password.",
     "aspects": [{"label": "login crash", "sentiment": "negative",
                  "quote": "Login crashes"}]},
    {"external_id": "r3", "submitted_at": "2026-06-28T09:00:00Z",
     "text": "Cannot login anymore, it just crashes back to the home screen."},
]


@pytest.fixture()
def client():
    engine = sa.create_engine(
        "sqlite://",
        poolclass=sa.pool.StaticPool,
        connect_args={"check_same_thread": False},   # TestClient serves on another thread
    )
    db.metadata.create_all(engine)
    db.set_engine_for_tests(engine)
    return TestClient(app)


def _seed(client):
    r = client.post("/api/v1/feedback/import", json={
        "source": {"name": "reviews", "kind": "app_reviews"}, "items": ITEMS})
    assert r.status_code == 201, r.text
    return r.json()


def test_import_dedups_and_stores_aspects(client):
    body = _seed(client)
    assert body["imported"] == 3
    assert body["aspects_stored"] == 2
    again = _seed(client)
    assert again["imported"] == 0
    assert again["duplicates"] == 3


def test_import_requires_exactly_one_payload_kind(client):
    r = client.post("/api/v1/feedback/import",
                    json={"source": {"name": "s"}})
    assert r.status_code == 422
    r = client.post("/api/v1/feedback/import",
                    json={"source": {"name": "s"}, "items": [], "csv_text": "x"})
    assert r.status_code == 422


def test_import_csv_path(client):
    csv_text = ("external_id,text,author,submitted_at\n"
                "c1,Sync is painfully slow lately,ann,2026-06-20T10:00:00Z\n")
    r = client.post("/api/v1/feedback/import", json={
        "source": {"name": "csv-drop", "kind": "import"}, "csv_text": csv_text})
    assert r.status_code == 201, r.text
    assert r.json()["imported"] == 1


def test_full_triage_loop_and_state_machine(client):
    _seed(client)
    run = client.post("/api/v1/triage/run", json={})
    assert run.status_code == 201, run.text
    body = run.json()
    assert body["clusters"] == 1
    assert body["assigned_seeded"] == 2
    assert body["assigned_embedding"] == 1
    assert body["issues_created"] == 1

    issues = client.get("/api/v1/issues").json()["issues"]
    assert len(issues) == 1
    issue = issues[0]
    assert issue["cluster_key"] == "crash_login"
    assert issue["state"] == "new"
    assert issue["frequency"] == 3
    assert issue["severity"] > 0

    iid = issue["id"]
    r = client.post(f"/api/v1/issues/{iid}/transition", json={"to_state": "triaged"})
    assert r.status_code == 200, r.text

    r = client.post(f"/api/v1/issues/{iid}/transition", json={"to_state": "verified"})
    assert r.status_code == 409
    assert r.json()["detail"]["error"] == "illegal_transition"

    detail = client.get(f"/api/v1/issues/{iid}").json()
    assert detail["state"] == "triaged"
    assert len(detail["transitions"]) == 1
    assert len(detail["members"]) == 3


def test_rerun_updates_issue_without_duplicating(client):
    _seed(client)
    client.post("/api/v1/triage/run", json={})
    run2 = client.post("/api/v1/triage/run", json={}).json()
    assert run2["issues_created"] == 0
    assert run2["issues_updated"] == 1
    assert len(client.get("/api/v1/issues").json()["issues"]) == 1


def test_triage_run_with_no_feedback_fails_loud(client):
    r = client.post("/api/v1/triage/run", json={})
    assert r.status_code == 422


def test_unknown_state_rejected_by_validation(client):
    _seed(client)
    client.post("/api/v1/triage/run", json={})
    iid = client.get("/api/v1/issues").json()["issues"][0]["id"]
    r = client.post(f"/api/v1/issues/{iid}/transition", json={"to_state": "reopened"})
    assert r.status_code == 422


def test_extract_without_key_fails_loud(client, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "openrouter_api_key", "")
    _seed(client)
    r = client.post("/api/v1/feedback/1/aspects/extract")
    assert r.status_code == 503
    assert "OPENROUTER_API_KEY" in r.json()["detail"]


def test_bearer_auth_enforced_when_token_set(client, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "smoke_test_token", "sekrit")
    r = client.post("/api/v1/feedback/import", json={
        "source": {"name": "s"}, "items": ITEMS})
    assert r.status_code == 401
    r = client.post("/api/v1/feedback/import", json={
        "source": {"name": "s"}, "items": ITEMS},
        headers={"Authorization": "Bearer sekrit"})
    assert r.status_code == 201


def test_malformed_aspects_rejected(client):
    r = client.post("/api/v1/feedback/import", json={
        "source": {"name": "s"},
        "items": [{"text": "hello world", "submitted_at": "2026-06-01T00:00:00Z",
                   "aspects": [{"label": "ok aspect", "sentiment": "furious"}]}]})
    assert r.status_code == 422


def test_distinct_external_ids_with_identical_text_both_import(client):
    """Dedup identity includes external_id: two distinct records with the same text are
    two observations, not one (undercounting frequency understates severity)."""
    items = [
        {"external_id": "t1", "submitted_at": "2026-07-01T00:00:00Z", "text": "Great app"},
        {"external_id": "t2", "submitted_at": "2026-07-02T00:00:00Z", "text": "Great app"},
    ]
    r = client.post("/api/v1/feedback/import", json={
        "source": {"name": "reviews", "kind": "app_reviews"}, "items": items})
    assert r.status_code == 201, r.text
    assert r.json()["imported"] == 2
    assert r.json()["duplicates"] == 0
    again = client.post("/api/v1/feedback/import", json={
        "source": {"name": "reviews", "kind": "app_reviews"}, "items": items}).json()
    assert again["imported"] == 0 and again["duplicates"] == 2


def test_extract_is_idempotent_replaces_prior_llm_aspects(client, monkeypatch):
    """A retried extract must replace the previous LLM claims, never append duplicates:
    duplicated sentiments flip the observation majority and silently deflate severity."""
    from app import routes
    from app.config import settings

    class FakeGateway:
        def complete(self, *, model, messages, json_schema=None, temperature=0.0):
            return {"aspects": [{"label": "login crash", "sentiment": "negative",
                                 "statement": "login crashes for the user",
                                 "quote": "crashes on login", "confidence": 0.9}]}

    monkeypatch.setattr(settings, "openrouter_api_key", "test-key")
    monkeypatch.setattr(settings, "llm_model_extraction", "test/model")
    monkeypatch.setattr(routes, "_gateway", lambda: FakeGateway())

    _seed(client)
    for _ in range(2):  # second call is the retry
        r = client.post("/api/v1/feedback/1/aspects/extract")
        assert r.status_code == 201, r.text
        assert r.json()["stored"] == 1

    with db.get_session() as s:
        llm = s.execute(sa.select(db.aspects).where(
            db.aspects.c.feedback_item_id == 1,
            db.aspects.c.provenance == "llm_extracted")).mappings().all()
        pre = s.execute(sa.select(db.aspects).where(
            db.aspects.c.feedback_item_id == 1,
            db.aspects.c.provenance == "pre_labeled")).mappings().all()
    assert len(llm) == 1, "retry appended duplicate LLM claim rows instead of replacing"
    assert len(pre) == 1, "replace must not touch pre-labeled claims"


def test_cluster_label_tie_breaks_deterministically(client):
    """Count ties break lexicographically, never by set iteration order (PYTHONHASHSEED)."""
    items = [
        {"external_id": "x1", "submitted_at": "2026-06-30T09:00:00Z",
         "text": "It crashes when I login.",
         "aspects": [{"label": "login crash", "sentiment": "negative"}]},
        {"external_id": "x2", "submitted_at": "2026-06-29T09:00:00Z",
         "text": "Crash at login again.",
         "aspects": [{"label": "crash login", "sentiment": "negative"}]},
    ]
    r = client.post("/api/v1/feedback/import", json={
        "source": {"name": "reviews", "kind": "app_reviews"}, "items": items})
    assert r.status_code == 201, r.text
    client.post("/api/v1/triage/run", json={})
    issues = client.get("/api/v1/issues").json()["issues"]
    assert len(issues) == 1
    assert issues[0]["title"] == "crash login"  # 1-1 tie -> lexicographically smallest


def test_concurrent_transition_conflict_returns_409(client, monkeypatch):
    """If the issue state changes between validation and the write, the guarded UPDATE
    matches zero rows and the request gets a typed 409 instead of a duplicate transition."""
    from app import routes

    _seed(client)
    client.post("/api/v1/triage/run", json={})
    iid = client.get("/api/v1/issues").json()["issues"][0]["id"]

    real_validate = routes.validate_transition

    def racing_validate(from_state, to_state):
        real_validate(from_state, to_state)
        # Simulate a concurrent request committing between validation and the write.
        with db.get_session() as s2:
            s2.execute(db.issues.update().where(db.issues.c.id == iid)
                       .values(state="triaged"))
            s2.commit()

    monkeypatch.setattr(routes, "validate_transition", racing_validate)
    r = client.post(f"/api/v1/issues/{iid}/transition", json={"to_state": "triaged"})
    assert r.status_code == 409, r.text
    assert r.json()["detail"]["error"] == "concurrent_transition"

    monkeypatch.setattr(routes, "validate_transition", real_validate)
    detail = client.get(f"/api/v1/issues/{iid}").json()
    assert detail["transitions"] == [], "conflicting request must not append a transition"
