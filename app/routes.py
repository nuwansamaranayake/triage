"""Business endpoints: the import -> aspects -> clusters -> issue registry loop, persisted.

POST /api/v1/feedback/import              bulk import, JSON items or CSV text (keyless connector)
POST /api/v1/feedback/{id}/aspects/extract  LLM aspect extraction (key-gated)
POST /api/v1/triage/run                   deterministic loop: cluster, register issues, score
GET  /api/v1/issues                       registry list with state + latest severity
GET  /api/v1/issues/{id}                  detail: members, transitions, severity breakdown
POST /api/v1/issues/{id}/transition       state machine; illegal transitions -> typed 409

The keyless paths are real product features (structured feedback arrives pre-labeled; CSV
export is how small teams actually hand data over). The LLM path refuses loudly without a
key — no silent fallback between the two (Standard 3). Bearer auth on mutations when
SMOKE_TEST_TOKEN is set.
"""
from __future__ import annotations

import csv
import hashlib
import io
from datetime import datetime, timezone

import sqlalchemy as sa
from fastapi import APIRouter, Header, HTTPException
from groundwork import BaseConfig, LLMGateway
from pydantic import BaseModel, Field

from . import db
from .config import settings
from .engine.aspects import (
    AspectClaim,
    AspectProvenance,
    aspects_from_entries,
    extract_aspects,
)
from .engine.clustering import ItemForClustering, build_clusters
from .engine.embedding import HashingEmbedder
from .engine.registry import INITIAL_STATE, IllegalTransition, validate_transition
from .engine.severity import HALF_LIFE_DAYS, observation_sentiment, severity

router = APIRouter(prefix="/api/v1")


def _auth(authorization: str | None) -> None:
    token = settings.smoke_test_token
    if token and authorization != f"Bearer {token}":
        raise HTTPException(status_code=401, detail="missing or invalid bearer token")


def _gateway() -> LLMGateway:
    if not settings.openrouter_api_key:
        raise HTTPException(
            status_code=503,
            detail="LLM aspect extraction requires OPENROUTER_API_KEY; import feedback "
                   "with pre-labeled aspects for the keyless path",
        )
    return LLMGateway(BaseConfig(
        openrouter_api_key=settings.openrouter_api_key,
        openrouter_base_url=settings.openrouter_base_url,
    ))


def _aware(dt: datetime) -> datetime:
    """Normalize datetimes read back from the DB: postgres returns tz-aware, sqlite (the
    test engine) returns naive UTC. Severity math requires aware everywhere."""
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


def _parse_when(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError, TypeError):
        raise HTTPException(status_code=422,
                            detail=f"submitted_at {value!r} is not ISO-8601")


def _store_aspects(s, fid: int, text: str, claims: list[AspectClaim]) -> int:
    for c in claims:
        span = c.core.evidence_ref.span
        s.execute(db.aspects.insert().values(
            feedback_item_id=fid, claim_id=c.core.claim_id, aspect_key=c.aspect_key,
            label=c.label, sentiment=c.sentiment.value, statement=c.core.statement,
            quote=text[span[0]:span[1]] if span else None,
            span_start=span[0] if span else None, span_end=span[1] if span else None,
            provenance=c.provenance.value, confidence=c.core.confidence or 0.0,
            verification_status=c.core.verification.status,
            gates=c.core.verification.gates))
    return len(claims)


class SourceIn(BaseModel):
    name: str = Field(min_length=1)
    kind: str = Field(default="import", min_length=1)


class ImportIn(BaseModel):
    source: SourceIn
    items: list[dict] | None = None
    csv_text: str | None = None


class TransitionIn(BaseModel):
    to_state: str = Field(pattern="^(new|triaged|in_progress|fixed|verified)$")
    note: str | None = None


def _csv_rows(csv_text: str) -> list[dict]:
    reader = csv.DictReader(io.StringIO(csv_text))
    rows = []
    for row in reader:
        if not (row.get("text") or "").strip() or not (row.get("submitted_at") or "").strip():
            raise HTTPException(status_code=422,
                                detail="csv rows need non-empty text and submitted_at "
                                       "columns")
        rows.append({"external_id": row.get("external_id"), "text": row["text"],
                     "author": row.get("author"), "submitted_at": row["submitted_at"]})
    return rows


@router.post("/feedback/import", status_code=201)
def import_feedback(body: ImportIn, authorization: str | None = Header(default=None)):
    _auth(authorization)
    if (body.items is None) == (body.csv_text is None):
        raise HTTPException(status_code=422,
                            detail="provide exactly one of items or csv_text")
    entries = body.items if body.items is not None else _csv_rows(body.csv_text)
    if not entries:
        raise HTTPException(status_code=422, detail="import contains no items")
    with db.get_session() as s, s.begin():
        src = s.execute(sa.select(db.sources)
                        .where(db.sources.c.name == body.source.name)).first()
        sid = src.id if src else s.execute(db.sources.insert().values(
            name=body.source.name, kind=body.source.kind)).inserted_primary_key[0]
        imported = duplicates = aspects_stored = 0
        for i, e in enumerate(entries):
            text = (e.get("text") or "").strip()
            if not text:
                raise HTTPException(status_code=422, detail=f"item {i} has empty text")
            when = _parse_when(e.get("submitted_at"))
            # Dedup identity includes external_id when the source provides one: distinct
            # records with identical text are distinct observations, not duplicates.
            ext = e.get("external_id")
            hash_key = (f"{body.source.name}|{ext}|{text}" if ext
                        else f"{body.source.name}|{text}")
            content_hash = hashlib.sha256(hash_key.encode()).hexdigest()
            if s.execute(sa.select(db.feedback_items.c.id)
                         .where(db.feedback_items.c.content_hash == content_hash)).first():
                duplicates += 1
                continue
            fid = s.execute(db.feedback_items.insert().values(
                source_id=sid, external_id=e.get("external_id"), text=text,
                author=e.get("author"), submitted_at=when,
                content_hash=content_hash)).inserted_primary_key[0]
            imported += 1
            if e.get("aspects"):
                try:
                    claims = aspects_from_entries(
                        e["aspects"], text, source_name=f"{body.source.name}:{fid}")
                except (ValueError, KeyError) as exc:
                    raise HTTPException(status_code=422,
                                        detail=f"item {i} aspects invalid: {exc}")
                aspects_stored += _store_aspects(s, fid, text, claims)
    return {"source_id": sid, "imported": imported, "duplicates": duplicates,
            "aspects_stored": aspects_stored, "provenance": "pre_labeled"}


@router.post("/feedback/{fid}/aspects/extract", status_code=201)
def extract_feedback_aspects(fid: int, authorization: str | None = Header(default=None)):
    _auth(authorization)
    gateway = _gateway()
    # Read in a short session that closes before the network call: a hung LLM request
    # must never pin a pooled connection or hold a transaction open.
    with db.get_session() as s:
        item = s.execute(sa.select(db.feedback_items)
                         .where(db.feedback_items.c.id == fid)).first()
    if item is None:
        raise HTTPException(status_code=404, detail="feedback item not found")
    claims = extract_aspects(gateway, settings.llm_model_extraction, item.text,
                             f"feedback-{fid}")
    with db.get_session() as s, s.begin():
        # Idempotent retry: replace this item's previous LLM extraction instead of
        # appending duplicate rows (duplicates skew the sentiment majority and severity).
        s.execute(db.aspects.delete().where(
            db.aspects.c.feedback_item_id == fid,
            db.aspects.c.provenance == AspectProvenance.llm_extracted.value))
        n = _store_aspects(s, fid, item.text, claims)
    rejected = sum(1 for c in claims if c.core.verification.status == "rejected")
    return {"stored": n, "rejected_span_anchor": rejected, "provenance": "llm_extracted"}


@router.post("/triage/run", status_code=201)
def run_triage(authorization: str | None = Header(default=None)):
    _auth(authorization)
    now = datetime.now(timezone.utc)
    with db.get_session() as s, s.begin():
        items = s.execute(sa.select(db.feedback_items)).mappings().all()
        if not items:
            raise HTTPException(status_code=422, detail="no feedback items to triage")
        rows = s.execute(sa.select(db.aspects)
                         .where(db.aspects.c.verification_status != "rejected")
                         ).mappings().all()
        keys_of: dict[int, set[str]] = {}
        sentiments_of: dict[int, list[str]] = {}
        labels_of: dict[str, list[str]] = {}
        for r in rows:
            keys_of.setdefault(r["feedback_item_id"], set()).add(r["aspect_key"])
            sentiments_of.setdefault(r["feedback_item_id"], []).append(r["sentiment"])
            labels_of.setdefault(r["aspect_key"], []).append(r["label"])
        result = build_clusters(
            [ItemForClustering(item_id=it["id"], text=it["text"],
                               aspect_keys=sorted(keys_of.get(it["id"], set())))
             for it in items],
            HashingEmbedder())

        when_of = {it["id"]: _aware(it["submitted_at"]) for it in items}
        s.execute(db.cluster_members.delete())  # assignments are derived, rebuilt each run
        issues_created = issues_updated = 0
        for key in sorted(result.clusters):
            members = result.clusters[key]
            existing = s.execute(sa.select(db.clusters)
                                 .where(db.clusters.c.cluster_key == key)).first()
            labels = sorted(labels_of.get(key, []))
            # Majority label with a total order: count ties break lexicographically, never
            # by set iteration order (which varies with PYTHONHASHSEED across processes).
            label = (min(set(labels), key=lambda lab: (-labels.count(lab), lab)) if labels
                     else key.replace("_", " "))
            cid = existing.id if existing else s.execute(db.clusters.insert().values(
                cluster_key=key, label=label)).inserted_primary_key[0]
            for m in members:
                s.execute(db.cluster_members.insert().values(
                    cluster_id=cid, feedback_item_id=m.item_id, method=m.method,
                    similarity=m.similarity))
            times = [when_of[m.item_id] for m in members]
            first_seen, last_seen = min(times), max(times)
            issue = s.execute(sa.select(db.issues)
                              .where(db.issues.c.cluster_id == cid)).first()
            if issue is None:
                iid = s.execute(db.issues.insert().values(
                    cluster_id=cid, title=label, state=INITIAL_STATE,
                    first_seen=first_seen, last_seen=last_seen)).inserted_primary_key[0]
                issues_created += 1
            else:
                iid = issue.id
                s.execute(db.issues.update().where(db.issues.c.id == iid)
                          .values(first_seen=first_seen, last_seen=last_seen))
                issues_updated += 1
            obs = [(when_of[m.item_id],
                    observation_sentiment(sentiments_of.get(m.item_id, [])))
                   for m in members]
            b = severity(obs, now)
            s.execute(db.severity_scores.insert().values(
                issue_id=iid, frequency=b.frequency, recency_weight=b.recency_weight,
                impact_weight=b.impact_weight, score=b.score,
                params={"half_life_days": HALF_LIFE_DAYS,
                        "reference_now": now.isoformat()}))
        seeded = sum(1 for ms in result.clusters.values()
                     for m in ms if m.method == "seeded")
        embedded = sum(1 for ms in result.clusters.values()
                       for m in ms if m.method == "embedding")
    return {"clusters": len(result.clusters), "assigned_seeded": seeded,
            "assigned_embedding": embedded, "unassigned": len(result.unassigned),
            "issues_created": issues_created, "issues_updated": issues_updated}


def _latest_severity(s, iid: int):
    return s.execute(sa.select(db.severity_scores)
                     .where(db.severity_scores.c.issue_id == iid)
                     .order_by(db.severity_scores.c.id.desc())).mappings().first()


@router.get("/issues")
def list_issues():
    with db.get_session() as s:
        rows = s.execute(
            sa.select(db.issues, db.clusters.c.cluster_key)
            .join(db.clusters, db.issues.c.cluster_id == db.clusters.c.id)
            .order_by(db.issues.c.id)).mappings().all()
        out = []
        for r in rows:
            sev = _latest_severity(s, r["id"])
            out.append({"id": r["id"], "cluster_key": r["cluster_key"],
                        "title": r["title"], "state": r["state"],
                        "first_seen": str(r["first_seen"]),
                        "last_seen": str(r["last_seen"]),
                        "severity": sev["score"] if sev else None,
                        "frequency": sev["frequency"] if sev else None})
    return {"issues": out}


@router.get("/issues/{iid}")
def get_issue(iid: int):
    with db.get_session() as s:
        issue = s.execute(
            sa.select(db.issues, db.clusters.c.cluster_key)
            .join(db.clusters, db.issues.c.cluster_id == db.clusters.c.id)
            .where(db.issues.c.id == iid)).mappings().first()
        if issue is None:
            raise HTTPException(status_code=404, detail="issue not found")
        members = s.execute(sa.select(db.cluster_members)
                            .where(db.cluster_members.c.cluster_id ==
                                   issue["cluster_id"])).mappings().all()
        transitions = s.execute(sa.select(db.issue_transitions)
                                .where(db.issue_transitions.c.issue_id == iid)
                                .order_by(db.issue_transitions.c.id)).mappings().all()
        sev = _latest_severity(s, iid)
    return {
        "id": issue["id"], "cluster_key": issue["cluster_key"], "title": issue["title"],
        "state": issue["state"], "first_seen": str(issue["first_seen"]),
        "last_seen": str(issue["last_seen"]),
        "members": [{"feedback_item_id": m["feedback_item_id"], "method": m["method"],
                     "similarity": m["similarity"]} for m in members],
        "transitions": [{"from_state": t["from_state"], "to_state": t["to_state"],
                         "note": t["note"], "at": str(t["at"])} for t in transitions],
        "severity": dict(sev) if sev else None,
    }


@router.post("/issues/{iid}/transition")
def transition_issue(iid: int, body: TransitionIn,
                     authorization: str | None = Header(default=None)):
    _auth(authorization)
    with db.get_session() as s, s.begin():
        issue = s.execute(sa.select(db.issues).where(db.issues.c.id == iid)).first()
        if issue is None:
            raise HTTPException(status_code=404, detail="issue not found")
        try:
            validate_transition(issue.state, body.to_state)
        except IllegalTransition as exc:
            raise HTTPException(status_code=409, detail={
                "error": "illegal_transition", "from_state": exc.from_state,
                "to_state": exc.to_state, "reason": exc.reason})
        # Guarded write: the UPDATE only lands if the state is still the one we validated,
        # so two concurrent requests cannot both append the same transition (lost update).
        result = s.execute(db.issues.update()
                           .where(db.issues.c.id == iid,
                                  db.issues.c.state == issue.state)
                           .values(state=body.to_state))
        if result.rowcount == 0:
            raise HTTPException(status_code=409, detail={
                "error": "concurrent_transition", "from_state": issue.state,
                "to_state": body.to_state,
                "reason": "issue state changed between validation and write; re-read and retry"})
        s.execute(db.issue_transitions.insert().values(
            issue_id=iid, from_state=issue.state, to_state=body.to_state,
            note=body.note))
    return {"issue_id": iid, "from_state": issue.state, "to_state": body.to_state}
