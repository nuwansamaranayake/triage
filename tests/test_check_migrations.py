"""The Standard 4 table-count gate must never pass vacuously: with EXPECTED_TABLE_COUNT
unset (e.g. a bare `docker run` without the env file) the check exits nonzero and says why,
instead of printing MIGRATION OK without asserting anything."""
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def _run(extra_env: dict) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if k != "EXPECTED_TABLE_COUNT"}
    env["DATABASE_URL"] = "postgresql+psycopg://unused:unused@127.0.0.1:1/none"
    env.update(extra_env)
    return subprocess.run([sys.executable, "scripts/check_migrations.py"],
                          cwd=str(REPO), env=env, capture_output=True, text=True,
                          timeout=30)


def test_unset_expected_table_count_fails_loud():
    r = _run({})
    assert r.returncode == 1
    assert "EXPECTED_TABLE_COUNT" in r.stderr
    assert "MIGRATION OK" not in r.stdout


def test_zero_expected_table_count_fails_loud():
    r = _run({"EXPECTED_TABLE_COUNT": "0"})
    assert r.returncode == 1
    assert "EXPECTED_TABLE_COUNT" in r.stderr
