import os
import sys

from sqlalchemy import create_engine, text


def main():
    # Standard 4: the table count is asserted, never assumed. A missing or zero
    # EXPECTED_TABLE_COUNT must fail loud — a vacuous pass is a silent no-op of the gate.
    raw = os.getenv("EXPECTED_TABLE_COUNT", "")
    expected = int(raw) if raw.strip().isdigit() else 0
    if expected <= 0:
        print("MIGRATION CHECK FAILED: EXPECTED_TABLE_COUNT is unset or not a positive "
              "integer; the Standard 4 table-count gate cannot run", file=sys.stderr)
        sys.exit(1)
    url = os.environ["DATABASE_URL"]
    with create_engine(url).connect() as c:
        n = c.execute(
            text("select count(*) from information_schema.tables where table_schema='public'")
        ).scalar_one()
    if n != expected:
        print(f"MIGRATION CHECK FAILED: expected {expected} tables, found {n}", file=sys.stderr)
        sys.exit(1)
    print(f"MIGRATION OK: {n} tables")


if __name__ == "__main__":
    main()
