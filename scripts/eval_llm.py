"""Key-gated LLM eval: the real aspect-extraction stage, measured — never a required CI
check, never a silent skip.

Two measures, bounds stated here before the first run:
  planted-aspect recall >= 0.70   anchors planted in a synthetic feedback text recovered
                                  in non-rejected extracted claims
  paraphrase jaccard    >= 0.60   canonicalized aspect-anchor stability across pre-authored
                                  feedback paraphrases (the
                                  contracts/aspect-extraction-stability.yaml invariant);
                                  never compared on raw model labels

Writes eval_report_llm.md. Exits nonzero on a miss (when it runs at all).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from groundwork import BaseConfig, LLMGateway  # noqa: E402

from app.engine.aspects import anchor_tokens, extract_aspects  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "eval_report_llm.md"

FEEDBACK = ("Checkout crashes every time I apply a coupon code on iOS. Also sync to my "
            "laptop is painfully slow since the last update, and I was double charged "
            "on billing this month.")
PARAPHRASES = [
    ("Applying a coupon code at checkout crashes the app on my iPhone every single "
     "time. Syncing with the laptop has become really slow since updating, and my "
     "billing shows a double charge for this month."),
    ("iOS checkout dies whenever a coupon is applied. Laptop sync is very slow after "
     "the latest update. Billing charged me twice this month."),
]
# A planted anchor counts as recalled when its token appears in a non-rejected claim.
ANCHORS = ["checkout", "coupon", "sync", "slow", "billing", "charge"]
# Aspect identity is compared on canonical anchor tokens filtered by this vocab, never on
# the model's invented label strings (naming varies across paraphrases even when the
# aspects are identical — CareerCompiler FAIL-0003, inherited as a design rule). Vocab
# entries are canonical forms (post-_stem): "bill" covers billing, "sync" covers syncing.
ANCHOR_VOCAB = {"checkout", "crash", "coupon", "ios", "sync", "slow", "laptop",
                "bill", "charge", "double", "update", "speed"}

RECALL_BOUND = 0.70
JACCARD_BOUND = 0.60


def _labels_and_text(claims) -> tuple[list[str], str]:
    ok = [c for c in claims if c.core.verification.status != "rejected"]
    text = " ".join(f"{c.label} {c.core.statement}" for c in ok).lower()
    return [c.label for c in ok], text


def _anchor_set(labels: list[str]) -> set[str]:
    return anchor_tokens(labels) & ANCHOR_VOCAB


def _jaccard(a: set, b: set) -> float:
    union = a | b
    return (len(a & b) / len(union)) if union else 1.0


def main() -> None:
    key = os.environ.get("OPENROUTER_API_KEY", "")
    model = os.environ.get("LLM_MODEL_EXTRACTION", "")
    if not key or not model:
        print("eval_llm: NOT RUN — OPENROUTER_API_KEY / LLM_MODEL_EXTRACTION missing. "
              "This section is key-gated by design; the deterministic suite in "
              "scripts/eval.py is the required gate.", file=sys.stderr)
        sys.exit(2)

    gw = LLMGateway(BaseConfig(openrouter_api_key=key))
    base_labels, base_text = _labels_and_text(
        extract_aspects(gw, model, FEEDBACK, "feedback.txt"))
    recall = sum(1 for a in ANCHORS if a in base_text) / len(ANCHORS)
    base_anchors = _anchor_set(base_labels)

    jaccards = []
    for i, txt in enumerate(PARAPHRASES):
        v_labels, _ = _labels_and_text(
            extract_aspects(gw, model, txt, f"paraphrase-{i}.txt"))
        jaccards.append(_jaccard(base_anchors, _anchor_set(v_labels)))
    j_min = min(jaccards)

    rows = [
        "# Triage key-gated aspect-extraction eval",
        "",
        f"model: {model}",
        f"base labels ({len(base_labels)}): {sorted(base_labels)}",
        f"base canonical anchors: {sorted(base_anchors)}",
        "",
        "| metric | value | bound | pass |",
        "|---|---|---|---|",
        f"| planted-aspect recall | {recall:.2f} | >= {RECALL_BOUND} | "
        f"{'PASS' if recall >= RECALL_BOUND else 'FAIL'} |",
        f"| paraphrase jaccard (min) | {j_min:.2f} | >= {JACCARD_BOUND} | "
        f"{'PASS' if j_min >= JACCARD_BOUND else 'FAIL'} |",
        "",
        f"contract: contracts/aspect-extraction-stability.yaml (threshold {JACCARD_BOUND})",
    ]
    text = "\n".join(rows) + "\n"
    REPORT.write_text(text, encoding="utf-8", newline="\n")
    print(text)
    if recall < RECALL_BOUND or j_min < JACCARD_BOUND:
        print("EVAL_LLM FAILED", file=sys.stderr)
        sys.exit(1)
    print("EVAL_LLM OK")


if __name__ == "__main__":
    main()
