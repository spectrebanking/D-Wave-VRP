import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import pytest  # noqa: E402
from db import connect, table_names  # noqa: E402

SEED_DIR = ROOT / "seed"

REQUIRED_TABLES = {
    "opportunities", "suppliers", "co_clusters", "blockers", "adls",
    "onboarding_docs", "past_performance", "attachments", "quotes",
    "awards", "market_intel", "quote_outcomes",
}


@pytest.fixture()
def tmp_conn(tmp_path):
    conn = connect(db_path=tmp_path / "test.db", key="a" * 64)
    yield conn
    conn.close()


def _csv_row_count(name: str) -> int:
    with open(SEED_DIR / name, newline="", encoding="utf-8") as f:
        return sum(1 for _ in csv.DictReader(f))


def test_tables_exist(tmp_conn):
    assert REQUIRED_TABLES.issubset(table_names(tmp_conn))


def test_encrypt_decrypt_round_trip(tmp_path):
    db_path = tmp_path / "roundtrip.db"
    conn = connect(db_path=db_path, key="b" * 64)
    conn.execute(
        "INSERT INTO opportunities (notion_url, title) VALUES (?, ?)",
        ("https://example.test/x", "round trip test"),
    )
    conn.commit()
    conn.close()

    # Wrong key must fail.
    with pytest.raises(Exception):
        bad = connect(db_path=db_path, key="c" * 64)
        bad.execute("SELECT * FROM opportunities").fetchall()

    # Right key must succeed and return the row.
    good = connect(db_path=db_path, key="b" * 64)
    row = good.execute("SELECT title FROM opportunities WHERE notion_url=?",
                        ("https://example.test/x",)).fetchone()
    good.close()
    assert row == ("round trip test",)


def test_db_file_is_not_plaintext_sqlite(tmp_path):
    db_path = tmp_path / "opaque.db"
    conn = connect(db_path=db_path, key="d" * 64)
    conn.execute("INSERT INTO opportunities (notion_url, title) VALUES ('u', 't')")
    conn.commit()
    conn.close()
    header = db_path.read_bytes()[:16]
    assert header != b"SQLite format 3\x00"


def test_seed_csvs_present_and_nonempty():
    for name in ("opportunities.csv", "suppliers.csv", "co_clusters.csv", "links.csv",
                 "awards.csv", "market_intel.csv"):
        assert (SEED_DIR / name).exists(), f"missing {name}"
        assert _csv_row_count(name) > 0, f"{name} has no rows"


def test_seed_loader_matches_csv_row_counts(tmp_path):
    sys.path.insert(0, str(ROOT / "scripts"))
    from seed import load_all

    conn = connect(db_path=tmp_path / "seeded.db", key="e" * 64)
    counts = load_all(conn)

    assert counts["opportunities"] == _csv_row_count("opportunities.csv")
    assert counts["suppliers"] == _csv_row_count("suppliers.csv")
    assert counts["co_clusters"] == _csv_row_count("co_clusters.csv")
    assert counts["opportunity_supplier_links"] == _csv_row_count("links.csv")
    assert counts["awards"] == _csv_row_count("awards.csv")
    assert counts["market_intel"] == _csv_row_count("market_intel.csv")

    for table, expected in counts.items():
        actual = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        assert actual == expected, f"{table}: db has {actual}, csv had {expected}"
    conn.close()


def test_seed_loader_is_idempotent(tmp_path):
    sys.path.insert(0, str(ROOT / "scripts"))
    from seed import load_all

    db_path = tmp_path / "idempotent.db"
    conn = connect(db_path=db_path, key="f" * 64)
    first = load_all(conn)
    second = load_all(conn)
    assert first == second
    for table, expected in second.items():
        actual = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        assert actual == expected
    conn.close()
