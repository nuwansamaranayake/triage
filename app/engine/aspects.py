"""Aspect claims: span-anchored, typed feedback observations on the groundwork spine.

A feedback item decomposes into aspect claims — what the feedback is about and how the
customer feels about it — each anchored to a literal quote from the feedback text when the
LLM extracted it. The anchor is the deterministic back-check: a claim whose quote cannot be
found verbatim in the source is marked rejected — kept, never silently dropped.

Model-invented labels are NOT stable identity: canonicalize() reduces every label to sorted
anchor tokens before it is compared, clustered, or stored as a key (the CareerCompiler
FAIL-0003 lesson, applied from the start). Aspects also arrive pre-labeled (structured
feedback: ticket categories, form-tagged reviews) — a real product path that needs no LLM.
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from enum import Enum
from typing import Protocol

from groundwork import Claim, ClaimType, EvidenceRef, Extractor, Verification
from pydantic import BaseModel, Field


class Sentiment(str, Enum):
    negative = "negative"
    neutral = "neutral"
    positive = "positive"


class AspectProvenance(str, Enum):
    llm_extracted = "llm_extracted"
    pre_labeled = "pre_labeled"


_TOKEN = re.compile(r"[a-z0-9]+")
_STOPWORDS = {"the", "a", "an", "of", "on", "in", "for", "with", "and", "or", "to",
              "is", "are", "was", "it", "its", "app", "my", "when", "after", "very"}


def _stem(tok: str) -> str:
    """Tiny deterministic suffix rules, enough to unify plural and gerund label variants
    ('crashes'/'crash', 'syncing'/'sync', 'billing'/'bill'). Observed live (FAIL-0005):
    without the -ing rule, paraphrase anchors diverged and the stability contract failed."""
    if len(tok) > 5 and tok.endswith("ing"):
        return tok[:-3]
    if len(tok) > 4 and tok.endswith("es"):
        return tok[:-2]
    if len(tok) > 3 and tok.endswith("s") and not tok.endswith("ss"):
        return tok[:-1]
    return tok


def canonicalize(label: str) -> str:
    """Reduce a label to its sorted anchor tokens: 'Login Crashes' == 'crash on login'."""
    toks = sorted({_stem(t) for t in _TOKEN.findall(label.lower())} - _STOPWORDS)
    return "_".join(toks)


def anchor_tokens(labels: list[str]) -> set[str]:
    """The comparison currency for anything a model named: canonical tokens, never labels."""
    out: set[str] = set()
    for label in labels:
        key = canonicalize(label)
        if key:
            out.update(key.split("_"))
    return out


class AspectClaim(BaseModel):
    """One typed feedback observation. `core` is the portfolio-wide claim atom (provenance,
    verification state, span evidence); the app adds its canonical key and sentiment."""
    core: Claim
    aspect_key: str = Field(min_length=1)   # canonical, from canonicalize()
    label: str = Field(min_length=1)        # as given / as the model named it
    sentiment: Sentiment
    provenance: AspectProvenance


EXTRACTION_SCHEMA = {
    "name": "aspect_claims",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "aspects": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "label": {"type": "string"},
                        "sentiment": {"type": "string",
                                      "enum": [s.value for s in Sentiment]},
                        "statement": {"type": "string"},
                        "quote": {"type": "string"},
                        "confidence": {"type": "number"},
                    },
                    "required": ["label", "sentiment", "statement", "quote", "confidence"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["aspects"],
        "additionalProperties": False,
    },
}


class CompletesJson(Protocol):
    def complete(self, *, model: str, messages: list[dict],
                 json_schema: dict | None = None, temperature: float = 0.0): ...


def _claim_id(source: str, aspect_key: str, statement: str) -> str:
    return hashlib.sha256(f"{source}|{aspect_key}|{statement}".encode()).hexdigest()[:16]


def extract_aspects(
    gateway: CompletesJson,
    model: str,
    feedback_text: str,
    source_name: str,
) -> list[AspectClaim]:
    """LLM decomposes the feedback into aspects; the span anchor disposes.

    Every returned claim carries verification: "pending" when its quote anchors verbatim in
    the source (span recorded), "rejected" when it does not — or when the model's label
    reduces to no anchor tokens. Nothing is silently dropped.
    """
    if not model:
        raise RuntimeError("LLM_MODEL_EXTRACTION is not set. Refusing to guess a model.")
    result = gateway.complete(
        model=model,
        messages=[
            {"role": "system",
             "content": ("Extract the product aspects this customer feedback is about. One "
                         "aspect per entry. label is a short noun phrase naming the product "
                         "component plus the problem or request (e.g. 'checkout crash', "
                         "'slow sync', 'billing charge') — never the user's action or the "
                         "wording of the complaint. Give the aspect's sentiment and a "
                         "one-sentence statement. quote is a VERBATIM substring of the "
                         "feedback that evidences the aspect. Never infer aspects that are "
                         "not in the text. Return JSON.")},
            {"role": "user", "content": feedback_text},
        ],
        json_schema=EXTRACTION_SCHEMA,
    )
    # Provider quirk observed on the estate: despite the strict object schema, some models
    # return the array at the top level. Normalize the envelope only — every item still
    # validates strictly below.
    if isinstance(result, list):
        result = {"aspects": result}
    now = datetime.now(timezone.utc)
    claims: list[AspectClaim] = []
    for item in result.get("aspects", []):
        quote = item["quote"]
        idx = feedback_text.find(quote)
        anchored = idx >= 0 and bool(quote.strip())
        key = canonicalize(item["label"])
        if not key:
            key, anchored = "unresolvable", False  # kept and visible, never dropped
        core = Claim(
            claim_id=_claim_id(source_name, key, item["statement"]),
            type=ClaimType.issue_aspect,
            statement=item["statement"],
            evidence_ref=EvidenceRef(
                source=source_name,
                span=(idx, idx + len(quote)) if anchored else None,
            ),
            recorded_at=now,
            extracted_by=Extractor(model=model, version="phase-1", temp=0.0),
            confidence=max(0.0, min(1.0, float(item["confidence"]))),
            verification=Verification(
                status="pending" if anchored else "rejected",
                gates=["span_anchor"],
                score=1.0 if anchored else 0.0,
            ),
        )
        claims.append(AspectClaim(
            core=core,
            aspect_key=key,
            label=item["label"],
            sentiment=Sentiment(item["sentiment"]),
            provenance=AspectProvenance.llm_extracted,
        ))
    return claims


def aspects_from_entries(
    entries: list[dict],
    feedback_text: str,
    source_name: str = "import",
) -> list[AspectClaim]:
    """Pre-labeled path: structured feedback arrives with its aspects already tagged.
    No LLM involved. Raises on malformed entries — no partial silent acceptance.

    A quote, when provided, must anchor verbatim in the feedback text or the claim is
    marked rejected (same honesty as the LLM path). Without a quote the claim is pending
    on the pre_labeled gate."""
    now = datetime.now(timezone.utc)
    out: list[AspectClaim] = []
    for e in entries:
        key = canonicalize(e["label"])
        if not key:
            raise ValueError(f"label {e['label']!r} reduces to no anchor tokens")
        quote = e.get("quote")
        if quote:
            idx = feedback_text.find(quote)
            anchored = idx >= 0
            span = (idx, idx + len(quote)) if anchored else None
            status = "pending" if anchored else "rejected"
            gates = ["span_anchor", "pre_labeled"]
        else:
            span, status, gates = None, "pending", ["pre_labeled"]
        out.append(AspectClaim(
            core=Claim(
                claim_id=_claim_id(source_name, key, e["label"]),
                type=ClaimType.issue_aspect,
                statement=e["label"],
                evidence_ref=EvidenceRef(source=source_name, span=span),
                recorded_at=now,
                extracted_by=Extractor(model="manual", version="entry", temp=0.0),
                confidence=1.0,
                verification=Verification(status=status, gates=gates,
                                          score=1.0 if status == "pending" else 0.0),
            ),
            aspect_key=key,
            label=e["label"],
            sentiment=Sentiment(e["sentiment"]),
            provenance=AspectProvenance.pre_labeled,
        ))
    return out
