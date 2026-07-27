from datetime import datetime, timedelta, timezone

import pytest

from app.engine.severity import severity

NOW = datetime(2026, 7, 1, tzinfo=timezone.utc)


def _obs(n: int, age_days: float, sentiment: str = "negative"):
    return [(NOW - timedelta(days=age_days), sentiment)] * n


def test_empty_scores_zero():
    b = severity([], NOW)
    assert b.frequency == 0 and b.score == 0.0


def test_monotone_in_frequency_duplicating_items_raises_score():
    base = severity(_obs(5, 10.0), NOW)
    doubled = severity(_obs(10, 10.0), NOW)
    assert doubled.frequency == 10
    assert doubled.recency_weight == pytest.approx(base.recency_weight)
    assert doubled.impact_weight == pytest.approx(base.impact_weight)
    assert doubled.score > base.score


def test_more_recent_scores_higher_at_equal_frequency():
    recent = severity(_obs(5, 2.0), NOW)
    stale = severity(_obs(5, 60.0), NOW)
    assert recent.score > stale.score


def test_negative_outweighs_neutral_and_positive():
    neg = severity(_obs(5, 10.0, "negative"), NOW)
    neu = severity(_obs(5, 10.0, "neutral"), NOW)
    pos = severity(_obs(5, 10.0, "positive"), NOW)
    assert neg.score > neu.score > pos.score


def test_future_timestamps_clamp_to_zero_age():
    b = severity([(NOW + timedelta(days=3), "negative")], NOW)
    assert b.recency_weight == pytest.approx(1.0)


def test_unknown_sentiment_fails_loud():
    with pytest.raises(KeyError):
        severity([(NOW, "angry")], NOW)


def test_deterministic():
    a = severity(_obs(7, 3.5), NOW)
    b = severity(_obs(7, 3.5), NOW)
    assert a == b
