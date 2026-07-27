"""Seeded, deterministic clustering. No LLM anywhere in this module.

Canonical aspect keys seed clusters; items carrying a key join that cluster (method
"seeded", similarity 1.0; an item with two aspects joins two clusters). Items with no
labeled aspects are assigned by HashingEmbedder cosine to the nearest cluster centroid
(method "embedding"), subject to a minimum similarity; below it the item stays unassigned
and is counted loudly, never guessed into a cluster.

Determinism: clusters iterate in sorted key order, ties break to the lexicographically
first cluster_key, and the embedder is the deterministic hashing one unless the caller
explicitly injects another.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from .embedding import Embedder, cosine

# Below this cosine similarity an unlabeled item is honestly unassigned, not force-fitted.
ASSIGN_MIN_SIMILARITY = 0.15


class Member(BaseModel):
    item_id: int
    method: str = Field(pattern="^(seeded|embedding)$")
    similarity: float


class ItemForClustering(BaseModel):
    item_id: int
    text: str
    aspect_keys: list[str] = Field(default_factory=list)  # canonical; empty = unlabeled


class ClusterResult(BaseModel):
    clusters: dict[str, list[Member]]  # cluster_key -> members, keys sorted on build
    unassigned: list[int]


def build_clusters(
    items: list[ItemForClustering],
    embedder: Embedder,
    min_similarity: float = ASSIGN_MIN_SIMILARITY,
) -> ClusterResult:
    labeled = [i for i in items if i.aspect_keys]
    unlabeled = [i for i in items if not i.aspect_keys]

    members: dict[str, list[Member]] = {}
    texts: dict[str, list[str]] = {}
    for it in labeled:
        for key in sorted(set(it.aspect_keys)):
            members.setdefault(key, []).append(
                Member(item_id=it.item_id, method="seeded", similarity=1.0))
            texts.setdefault(key, []).append(it.text)

    unassigned: list[int] = []
    if unlabeled:
        keys = sorted(members)
        if not keys:
            unassigned = [i.item_id for i in unlabeled]
        else:
            # Bag-of-tokens hashing makes "concatenate then embed" the centroid of the
            # member texts; the seed key's own tokens join it so a sparse cluster still
            # carries its name's signal.
            centroids = embedder.embed(
                [" ".join([k.replace("_", " ")] + texts[k]) for k in keys])
            for it in unlabeled:
                [v] = embedder.embed([it.text])
                best_key: str | None = None
                best_sim = 0.0
                for k, c in zip(keys, centroids):
                    sim = cosine(v, c)
                    if sim > best_sim:  # strict: ties keep the earlier (sorted) key
                        best_key, best_sim = k, sim
                if best_key is not None and best_sim >= min_similarity:
                    members[best_key].append(
                        Member(item_id=it.item_id, method="embedding",
                               similarity=round(best_sim, 6)))
                else:
                    unassigned.append(it.item_id)

    return ClusterResult(
        clusters={k: members[k] for k in sorted(members)},
        unassigned=unassigned,
    )
