import pytest

from app.engine.aspects import (
    AspectProvenance,
    anchor_tokens,
    aspects_from_entries,
    canonicalize,
    extract_aspects,
)

TEXT = "The app crashes on login every time after the last update. Also dark mode please."


class StubGateway:
    """Typed stub: returns a canned strict-schema payload. No network."""

    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def complete(self, *, model, messages, json_schema=None, temperature=0.0):
        self.calls.append({"model": model, "json_schema": json_schema})
        return self.payload


def test_canonicalize_unifies_label_variants():
    assert canonicalize("Login Crashes") == canonicalize("crash on login") == "crash_login"
    assert canonicalize("the of a") == ""


def test_anchor_tokens_from_labels():
    assert anchor_tokens(["Login Crashes", "slow sync"]) == {"crash", "login", "slow", "sync"}


def test_pre_labeled_entries_are_typed_and_anchored():
    claims = aspects_from_entries(
        [{"label": "login crash", "sentiment": "negative", "quote": "crashes on login"}],
        TEXT)
    [c] = claims
    assert c.aspect_key == "crash_login"
    assert c.provenance is AspectProvenance.pre_labeled
    assert c.core.verification.status == "pending"
    start, end = c.core.evidence_ref.span
    assert TEXT[start:end] == "crashes on login"


def test_pre_labeled_bad_quote_is_rejected_not_dropped():
    [c] = aspects_from_entries(
        [{"label": "login crash", "sentiment": "negative", "quote": "never in the text"}],
        TEXT)
    assert c.core.verification.status == "rejected"
    assert c.core.evidence_ref.span is None


def test_pre_labeled_rejects_malformed_entries():
    with pytest.raises(ValueError):
        aspects_from_entries([{"label": "the of", "sentiment": "negative"}], TEXT)
    with pytest.raises(ValueError):
        aspects_from_entries([{"label": "login crash", "sentiment": "angry"}], TEXT)
    with pytest.raises(KeyError):
        aspects_from_entries([{"sentiment": "negative"}], TEXT)


def test_extract_aspects_span_anchor_disposes():
    gw = StubGateway({"aspects": [
        {"label": "login crash", "sentiment": "negative",
         "statement": "App crashes on login", "quote": "crashes on login",
         "confidence": 0.9},
        {"label": "dark mode", "sentiment": "neutral",
         "statement": "Dark mode requested", "quote": "NOT A REAL QUOTE",
         "confidence": 0.8},
    ]})
    claims = extract_aspects(gw, "test-model", TEXT, "feedback-1")
    assert len(claims) == 2  # the bad one is kept, never dropped
    good, bad = claims
    assert good.core.verification.status == "pending"
    assert good.aspect_key == "crash_login"
    assert bad.core.verification.status == "rejected"
    assert gw.calls[0]["json_schema"]["name"] == "aspect_claims"


def test_extract_aspects_normalizes_top_level_array():
    gw = StubGateway([
        {"label": "sync speed", "sentiment": "negative",
         "statement": "Sync is slow", "quote": "login", "confidence": 0.5},
    ])
    claims = extract_aspects(gw, "test-model", TEXT, "feedback-1")
    assert [c.aspect_key for c in claims] == ["speed_sync"]


def test_extract_aspects_requires_model():
    with pytest.raises(RuntimeError):
        extract_aspects(StubGateway({"aspects": []}), "", TEXT, "feedback-1")
