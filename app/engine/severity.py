"""Severity is a formula, not a feeling — deterministic and documented here.

    severity = frequency x recency_weight x impact_weight

frequency        number of feedback items on the issue (its cluster member count)
recency_weight   mean over items of 0.5 ** (age_days / HALF_LIFE_DAYS), floored at
                 MIN_WEIGHT: recent pain outweighs old pain, smoothly, with a 30-day
                 half-life
impact_weight    mean over items of the sentiment impact map, floored at MIN_WEIGHT

Monotone in frequency: recency_weight and impact_weight are means in (0, 1], so holding
them fixed, severity is strictly increasing in frequency — equivalently, duplicating the
item multiset (same ages, same sentiments) strictly raises the score. The eval plants both
properties and fails on any violation.

Unknown sentiments raise (Standard 3): a typo never silently becomes "neutral".
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

HALF_LIFE_DAYS = 30.0
MIN_WEIGHT = 1e-6
IMPACT = {"negative": 1.0, "neutral": 0.4, "positive": 0.1}


class SeverityBreakdown(BaseModel):
    frequency: int
    recency_weight: float
    impact_weight: float
    score: float


def severity(
    observations: list[tuple[datetime, str]],
    now: datetime,
    half_life_days: float = HALF_LIFE_DAYS,
) -> SeverityBreakdown:
    """Score one issue from its (submitted_at, sentiment) observations at reference time
    `now`. `now` is always an explicit argument: the eval feeds a fixed clock so the
    report is byte-reproducible; the API feeds the request time."""
    if not observations:
        return SeverityBreakdown(frequency=0, recency_weight=0.0,
                                 impact_weight=0.0, score=0.0)
    decays: list[float] = []
    impacts: list[float] = []
    for submitted_at, sentiment in observations:
        age_days = max(0.0, (now - submitted_at).total_seconds() / 86400.0)
        decays.append(max(MIN_WEIGHT, 0.5 ** (age_days / half_life_days)))
        impacts.append(max(MIN_WEIGHT, IMPACT[sentiment]))  # KeyError on unknown: loud
    n = len(observations)
    recency_weight = sum(decays) / n
    impact_weight = sum(impacts) / n
    return SeverityBreakdown(
        frequency=n,
        recency_weight=recency_weight,
        impact_weight=impact_weight,
        score=n * recency_weight * impact_weight,
    )
