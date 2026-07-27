"""Eval harness: the golden feedback suite against the EVAL.md Phase 1 thresholds.

Deterministic and keyless (HashingEmbedder, pre-labeled golden aspects, planted transitions
and severity ordering, a fixed reference clock read from the golden file — never wall
time). Writes eval_report.md so consecutive runs can be compared byte-for-byte. The
key-gated extraction section (real gateway) is reported separately by scripts/eval_llm.py
and is never a required check — and never a silent skip: this harness says loudly whether
it ran.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.engine.aspects import aspects_from_entries  # noqa: E402
from app.engine.clustering import ItemForClustering, build_clusters  # noqa: E402
from app.engine.embedding import HashingEmbedder  # noqa: E402
from app.engine.registry import IllegalTransition, validate_transition  # noqa: E402
from app.engine.severity import observation_sentiment, severity  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
GOLDEN = ROOT / "data" / "synthetic" / "golden" / "golden.json"
REPORT = ROOT / "eval_report.md"

BOUNDS = {
    "cluster_purity": 0.85,
    "assignment_coverage": 0.90,
    "state_machine_legality": 1.00,
    "severity_monotonicity": 1.00,
}


def main() -> None:
    data = json.loads(GOLDEN.read_text(encoding="utf-8"))
    now = datetime.fromisoformat(data["reference_now"].replace("Z", "+00:00"))
    items = data["items"]
    golden_of = {it["id"]: it["golden_cluster"] for it in items}

    # 1) Aspect claims through the real pre-labeled path, then deterministic clustering.
    sentiments: dict[int, list[str]] = {}
    cluster_inputs: list[ItemForClustering] = []
    for it in items:
        claims = aspects_from_entries(it.get("aspects", []), it["text"],
                                      source_name=f"golden-{it['id']}")
        keys = sorted({c.aspect_key for c in claims
                       if c.core.verification.status != "rejected"})
        sentiments[it["id"]] = [c.sentiment.value for c in claims
                                if c.core.verification.status != "rejected"]
        cluster_inputs.append(
            ItemForClustering(item_id=it["id"], text=it["text"], aspect_keys=keys))
    result = build_clusters(cluster_inputs, HashingEmbedder())

    rows_out: list[str] = []
    total_members = pure_members = 0
    assigned_ids: set[int] = set()
    for key in sorted(result.clusters):
        members = result.clusters[key]
        assigned_ids.update(m.item_id for m in members)
        labels: dict[str, int] = {}
        for m in members:
            g = golden_of[m.item_id]
            labels[g] = labels.get(g, 0) + 1
        majority = max(labels.values())
        total_members += len(members)
        pure_members += majority
        seeded = sum(1 for m in members if m.method == "seeded")
        rows_out.append(f"cluster {key}: {len(members)} members "
                        f"({seeded} seeded, {len(members) - seeded} embedding), "
                        f"majority golden label share {majority}/{len(members)}")
    purity = pure_members / total_members if total_members else 0.0
    coverage = len(assigned_ids) / len(items)
    if result.unassigned:
        rows_out.append(f"unassigned items: {sorted(result.unassigned)}")

    # 2) State-machine legality: planted legal accepted, planted illegal rejected (typed).
    legality_total = legality_ok = 0
    for frm, to in data["transitions"]["legal"]:
        legality_total += 1
        try:
            validate_transition(frm, to)
            legality_ok += 1
        except IllegalTransition:
            rows_out.append(f"LEGALITY MISS: legal {frm} -> {to} was rejected")
    for frm, to in data["transitions"]["illegal"]:
        legality_total += 1
        try:
            validate_transition(frm, to)
            rows_out.append(f"LEGALITY MISS: illegal {frm} -> {to} was accepted")
        except IllegalTransition:
            legality_ok += 1
    legality = legality_ok / legality_total

    # 3) Severity: planted ordering over every pair, plus the duplication property.
    obs_of: dict[str, list[tuple[datetime, str]]] = {}
    for key in sorted(result.clusters):
        obs = []
        for m in result.clusters[key]:
            it = next(i for i in items if i["id"] == m.item_id)
            when = datetime.fromisoformat(it["submitted_at"].replace("Z", "+00:00"))
            obs.append((when, observation_sentiment(sentiments[m.item_id])))
        obs_of[key] = obs
    scores = {key: severity(obs, now) for key, obs in obs_of.items()}
    order = data["expected_severity_order"]
    mono_total = mono_ok = 0
    for i in range(len(order)):
        for j in range(i + 1, len(order)):
            hi, lo = order[i], order[j]
            mono_total += 1
            if scores[hi].score > scores[lo].score:
                mono_ok += 1
            else:
                rows_out.append(f"MONOTONICITY MISS: {hi} ({scores[hi].score:.4f}) "
                                f"not > {lo} ({scores[lo].score:.4f})")
    mono_total += 1  # duplication: same multiset twice must score strictly higher
    top = order[0]
    if severity(obs_of[top] * 2, now).score > scores[top].score:
        mono_ok += 1
    else:
        rows_out.append("MONOTONICITY MISS: duplicating the top issue did not raise it")
    monotonicity = mono_ok / mono_total

    for key in order:
        b = scores[key]
        rows_out.append(f"severity {key}: frequency={b.frequency} "
                        f"recency={b.recency_weight:.4f} impact={b.impact_weight:.4f} "
                        f"score={b.score:.4f}")

    metrics = {
        "cluster_purity": purity,
        "assignment_coverage": coverage,
        "state_machine_legality": legality,
        "severity_monotonicity": monotonicity,
    }
    passes = {k: metrics[k] >= BOUNDS[k] for k in BOUNDS}

    lines = ["# Triage golden feedback eval report", ""]
    lines += rows_out + ["", "| metric | value | bound | pass |", "|---|---|---|---|"]
    for k, v in metrics.items():
        lines.append(f"| {k} | {round(v, 4)} | >= {BOUNDS[k]} | "
                     f"{'PASS' if passes[k] else 'FAIL'} |")
    if os.environ.get("OPENROUTER_API_KEY"):
        lines += ["", "key-gated extraction section: run scripts/eval_llm.py "
                      "(not part of this deterministic report)"]
    else:
        lines += ["", "key-gated extraction section: NOT RUN (no OPENROUTER_API_KEY); "
                      "deterministic bounds above are the required gate"]
    text = "\n".join(lines) + "\n"
    REPORT.write_text(text, encoding="utf-8", newline="\n")
    print(text)
    if not all(passes.values()):
        print("EVAL FAILED: at least one threshold missed (see rows above)", file=sys.stderr)
        sys.exit(1)
    print("EVAL OK")


if __name__ == "__main__":
    main()
