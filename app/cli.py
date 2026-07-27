"""CLI triage run: keyless, serverless, honest.

Usage:
    python -m app.cli triage --data data/synthetic/golden/golden.json [--report out.md]

Loads a golden-format feedback file (items with optional pre-labeled aspects and a fixed
reference_now), runs the deterministic loop in memory — aspect claims, seeded clustering,
severity — and prints the registry ranked by severity. No LLM, no database, no network.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from .engine.aspects import aspects_from_entries
from .engine.clustering import ItemForClustering, build_clusters
from .engine.embedding import HashingEmbedder
from .engine.severity import observation_sentiment, severity


def triage(data_path: str, report_path: str | None) -> int:
    data = json.loads(Path(data_path).read_text(encoding="utf-8"))
    now = datetime.fromisoformat(data["reference_now"].replace("Z", "+00:00"))
    items = data["items"]
    sentiments: dict[int, list[str]] = {}
    inputs: list[ItemForClustering] = []
    for it in items:
        claims = aspects_from_entries(it.get("aspects", []), it["text"],
                                      source_name=f"cli-{it['id']}")
        ok = [c for c in claims if c.core.verification.status != "rejected"]
        sentiments[it["id"]] = [c.sentiment.value for c in ok]
        inputs.append(ItemForClustering(
            item_id=it["id"], text=it["text"],
            aspect_keys=sorted({c.aspect_key for c in ok})))
    result = build_clusters(inputs, HashingEmbedder())

    scored = []
    for key in sorted(result.clusters):
        members = result.clusters[key]
        obs = []
        for m in members:
            it = next(i for i in items if i["id"] == m.item_id)
            when = datetime.fromisoformat(it["submitted_at"].replace("Z", "+00:00"))
            obs.append((when, observation_sentiment(sentiments[m.item_id])))
        scored.append((key, severity(obs, now)))
    scored.sort(key=lambda kv: (-kv[1].score, kv[0]))

    lines = ["# Triage registry (CLI, deterministic)", ""]
    lines.append("| rank | issue | frequency | recency | impact | severity |")
    lines.append("|---|---|---|---|---|---|")
    for rank, (key, b) in enumerate(scored, start=1):
        lines.append(f"| {rank} | {key} | {b.frequency} | {b.recency_weight:.4f} "
                     f"| {b.impact_weight:.4f} | {b.score:.4f} |")
    if result.unassigned:
        lines += ["", f"unassigned items (below similarity threshold): "
                      f"{sorted(result.unassigned)}"]
    text = "\n".join(lines) + "\n"
    if report_path:
        Path(report_path).write_text(text, encoding="utf-8", newline="\n")
    print(text)
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(prog="triage")
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("triage", help="run the deterministic triage loop from a data file")
    t.add_argument("--data", required=True)
    t.add_argument("--report", default=None)
    args = ap.parse_args()
    sys.exit(triage(args.data, args.report))


if __name__ == "__main__":
    main()
