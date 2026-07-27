"""Standard 6 gate: contracts.md must match what the app actually serves.

Parses the contracts.md table and asserts every row marked `implemented` exists in the
app's OpenAPI spec (the same document served at /openapi.json) with that method. The two
FastAPI meta endpoints (/openapi.json, /docs) are absent from spec["paths"] by design, so
they are probed live instead. Drift between the doc and the API fails CI here — the claim
in contracts.md is backed by this test, not by convention.
"""
import re
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

CONTRACTS = Path(__file__).resolve().parent.parent / "contracts.md"
META_PATHS = {"/openapi.json", "/docs"}  # served by FastAPI itself, not in spec["paths"]
_PLACEHOLDER = re.compile(r"\{[^}]+\}")


def _normalize(path: str) -> str:
    """Compare path shapes, not parameter names: /issues/{id} == /issues/{iid}."""
    return _PLACEHOLDER.sub("{}", path)


def _implemented_rows() -> list[tuple[str, str]]:
    rows = []
    for line in CONTRACTS.read_text(encoding="utf-8").splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 4 and cells[3] == "implemented":
            method = cells[1].lower()
            for path in re.findall(r"`([^`]+)`", cells[2]):
                rows.append((method, path))
    return rows


def test_every_implemented_contract_row_is_in_the_openapi_spec():
    spec = app.openapi()
    served = {(m.lower(), _normalize(p))
              for p, ops in spec["paths"].items() for m in ops}
    rows = _implemented_rows()
    assert rows, "no implemented rows parsed from contracts.md — table format changed?"
    missing = [(m, p) for m, p in rows
               if p not in META_PATHS and (m, _normalize(p)) not in served]
    assert not missing, f"contracts.md claims implemented but the spec lacks: {missing}"


def test_meta_endpoints_are_served_live():
    client = TestClient(app)
    for method, path in _implemented_rows():
        if path in META_PATHS:
            assert method == "get"
            assert client.get(path).status_code == 200, f"{path} not served"
