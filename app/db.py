"""Schema and session plumbing. metadata is the single source of truth; the alembic
migration applies it, and EXPECTED_TABLE_COUNT asserts the result (Standard 4)."""
from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import sessionmaker

from .config import settings

JSON = sa.JSON().with_variant(JSONB(), "postgresql")

metadata = sa.MetaData()

sources = sa.Table(
    "sources", metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("name", sa.Text, nullable=False, unique=True),
    sa.Column("kind", sa.Text, nullable=False),            # e.g. app_reviews | tickets | import
    sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
)

feedback_items = sa.Table(
    "feedback_items", metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("source_id", sa.Integer, sa.ForeignKey("sources.id"), nullable=False),
    sa.Column("external_id", sa.Text),
    sa.Column("text", sa.Text, nullable=False),
    sa.Column("author", sa.Text),
    sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("content_hash", sa.Text, nullable=False, unique=True),  # dedup, deterministic
    sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
)

aspects = sa.Table(
    "aspects", metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("feedback_item_id", sa.Integer, sa.ForeignKey("feedback_items.id"),
              nullable=False),
    sa.Column("claim_id", sa.Text, nullable=False),
    sa.Column("aspect_key", sa.Text, nullable=False),      # canonical (canonicalize())
    sa.Column("label", sa.Text, nullable=False),           # raw, as given / model-named
    sa.Column("sentiment", sa.Text, nullable=False),       # negative | neutral | positive
    sa.Column("statement", sa.Text, nullable=False),
    sa.Column("quote", sa.Text),
    sa.Column("span_start", sa.Integer),
    sa.Column("span_end", sa.Integer),
    sa.Column("provenance", sa.Text, nullable=False),      # llm_extracted | pre_labeled
    sa.Column("confidence", sa.Float, nullable=False),
    sa.Column("verification_status", sa.Text, nullable=False),  # pending|passed|rejected
    sa.Column("gates", JSON, nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
)

clusters = sa.Table(
    "clusters", metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("cluster_key", sa.Text, nullable=False, unique=True),  # canonical aspect key
    sa.Column("label", sa.Text, nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
)

cluster_members = sa.Table(
    "cluster_members", metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("cluster_id", sa.Integer, sa.ForeignKey("clusters.id"), nullable=False),
    sa.Column("feedback_item_id", sa.Integer, sa.ForeignKey("feedback_items.id"),
              nullable=False),
    sa.Column("method", sa.Text, nullable=False),          # seeded | embedding
    sa.Column("similarity", sa.Float, nullable=False),
)

issues = sa.Table(
    "issues", metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("cluster_id", sa.Integer, sa.ForeignKey("clusters.id"),
              nullable=False, unique=True),
    sa.Column("title", sa.Text, nullable=False),
    sa.Column("state", sa.Text, nullable=False),           # registry.STATES
    sa.Column("first_seen", sa.DateTime(timezone=True), nullable=False),
    sa.Column("last_seen", sa.DateTime(timezone=True), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
)

issue_transitions = sa.Table(
    "issue_transitions", metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("issue_id", sa.Integer, sa.ForeignKey("issues.id"), nullable=False),
    sa.Column("from_state", sa.Text, nullable=False),
    sa.Column("to_state", sa.Text, nullable=False),
    sa.Column("note", sa.Text),
    sa.Column("at", sa.DateTime(timezone=True), server_default=sa.func.now()),
)

severity_scores = sa.Table(
    "severity_scores", metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("issue_id", sa.Integer, sa.ForeignKey("issues.id"), nullable=False),
    sa.Column("frequency", sa.Integer, nullable=False),
    sa.Column("recency_weight", sa.Float, nullable=False),
    sa.Column("impact_weight", sa.Float, nullable=False),
    sa.Column("score", sa.Float, nullable=False),
    sa.Column("params", JSON, nullable=False),             # half_life_days etc., provenance
    sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
)

_engine = None
_Session = None


def get_engine():
    global _engine, _Session
    if _engine is None:
        _engine = sa.create_engine(settings.database_url, pool_pre_ping=True)
        _Session = sessionmaker(bind=_engine)
    return _engine


def get_session():
    get_engine()
    return _Session()


def set_engine_for_tests(engine) -> None:
    """Tests inject their own engine (sqlite in-memory). Explicit, never automatic."""
    global _engine, _Session
    _engine = engine
    _Session = sessionmaker(bind=engine)
