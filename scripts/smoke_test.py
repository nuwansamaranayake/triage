"""Smoke test: the real keyless business loop against a running instance.

import (pre-labeled aspects + one unlabeled item) -> triage run -> issues listed ->
legal transition accepted -> illegal transition rejected with the typed 409. Uses a
per-run nonce so consecutive runs against the same database exercise fresh issues.
"""
import os
import secrets
import sys

import httpx

BASE = f"http://{os.getenv('API_HOST', '127.0.0.1')}:{os.getenv('API_PORT', '8000')}"
TOKEN = os.getenv("SMOKE_TEST_TOKEN", "")
HEADERS = {"Authorization": f"Bearer {TOKEN}"}


def get(path: str):
    r = httpx.get(BASE + path, headers=HEADERS, timeout=10)
    r.raise_for_status()
    body = r.json()
    assert body, f"{path} returned an empty body"
    return body


def post(path: str, payload: dict, expect: int):
    r = httpx.post(BASE + path, json=payload, headers=HEADERS, timeout=10)
    assert r.status_code == expect, f"{path} -> {r.status_code} (wanted {expect}): {r.text}"
    return r.json()


def main():
    get("/health")
    nonce = secrets.token_hex(4)
    label = f"checkout failure {nonce}"
    items = [
        {"external_id": "a1", "submitted_at": "2026-07-20T10:00:00Z",
         "text": f"Checkout failure {nonce} when I apply a coupon.",
         "aspects": [{"label": label, "sentiment": "negative",
                      "quote": f"Checkout failure {nonce}"}]},
        {"external_id": "a2", "submitted_at": "2026-07-21T11:00:00Z",
         "text": f"Another checkout failure {nonce}, the pay button dies.",
         "aspects": [{"label": label, "sentiment": "negative",
                      "quote": f"checkout failure {nonce}"}]},
        {"external_id": "a3", "submitted_at": "2026-07-22T09:00:00Z",
         "text": f"The checkout failure {nonce} strikes again for me too."},
    ]
    imp = post("/api/v1/feedback/import",
               {"source": {"name": f"smoke-{nonce}", "kind": "app_reviews"},
                "items": items}, 201)
    assert imp["imported"] == 3, imp
    assert imp["aspects_stored"] == 2, imp

    run = post("/api/v1/triage/run", {}, 201)
    assert run["clusters"] >= 1, run

    issues = get("/api/v1/issues")["issues"]
    mine = [i for i in issues if nonce in i["cluster_key"]]
    assert len(mine) == 1, f"expected exactly one issue for nonce {nonce}: {issues}"
    issue = mine[0]
    assert issue["state"] == "new" and issue["frequency"] == 3, issue
    assert issue["severity"] and issue["severity"] > 0, issue

    iid = issue["id"]
    tr = post(f"/api/v1/issues/{iid}/transition", {"to_state": "triaged"}, 200)
    assert tr["to_state"] == "triaged", tr
    bad = post(f"/api/v1/issues/{iid}/transition", {"to_state": "new"}, 409)
    assert bad["detail"]["error"] == "illegal_transition", bad

    detail = get(f"/api/v1/issues/{iid}")
    assert detail["state"] == "triaged", detail
    assert len(detail["members"]) == 3, detail
    assert len(detail["transitions"]) == 1, detail
    methods = {m["method"] for m in detail["members"]}
    assert methods == {"seeded", "embedding"}, detail

    print("SMOKE OK")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"SMOKE FAILED: {e}", file=sys.stderr)
        sys.exit(1)
