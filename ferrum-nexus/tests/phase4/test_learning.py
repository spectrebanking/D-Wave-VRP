import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import pytest  # noqa: E402
from db import connect  # noqa: E402
from quote_add import add_quote  # noqa: E402
import learning  # noqa: E402


@pytest.fixture()
def conn(tmp_path):
    c = connect(db_path=tmp_path / "test.db", key="a" * 64)
    c.execute("INSERT INTO suppliers (notion_url, supplier_name) VALUES ('sup://1', 'Co A')")
    c.execute("INSERT INTO suppliers (notion_url, supplier_name) VALUES ('sup://2', 'Co B')")
    c.commit()
    yield c
    c.close()


def test_record_outcome_rejects_unknown_outcome(conn):
    add_quote(conn, "SOL-1", "sup://1")
    with pytest.raises(ValueError, match="outcome must be one of"):
        learning.record_outcome(conn, "SOL-1::sup://1", "maybe")


def test_record_outcome_rejects_unknown_quote_key(conn):
    with pytest.raises(ValueError, match="unknown quote_key"):
        learning.record_outcome(conn, "SOL-nope::sup://1", "won")


def test_supplier_reliability_is_none_with_no_decided_history(conn):
    add_quote(conn, "SOL-1", "sup://1")
    assert learning.supplier_reliability(conn, "sup://1") is None


def test_supplier_reliability_excludes_no_response_from_denominator(conn):
    add_quote(conn, "SOL-1", "sup://1")
    add_quote(conn, "SOL-2", "sup://1")
    learning.record_outcome(conn, "SOL-1::sup://1", "won")
    learning.record_outcome(conn, "SOL-2::sup://1", "no_response")

    # Only the 'won' outcome is decided -- no_response doesn't count as a loss.
    assert learning.supplier_reliability(conn, "sup://1") == 1.0


def test_supplier_reliability_computes_win_rate(conn):
    add_quote(conn, "SOL-1", "sup://1")
    add_quote(conn, "SOL-2", "sup://1")
    learning.record_outcome(conn, "SOL-1::sup://1", "won")
    learning.record_outcome(conn, "SOL-2::sup://1", "lost")

    assert learning.supplier_reliability(conn, "sup://1") == 0.5


def test_pending_outcome_has_no_decided_at(conn):
    add_quote(conn, "SOL-1", "sup://1")
    learning.record_outcome(conn, "SOL-1::sup://1", "pending")
    row = conn.execute(
        "SELECT outcome, decided_at FROM quote_outcomes WHERE quote_key = ?",
        ("SOL-1::sup://1",),
    ).fetchone()
    assert row == ("pending", None)


def test_supplier_scorecard_only_lists_suppliers_with_decided_history(conn):
    add_quote(conn, "SOL-1", "sup://1")
    add_quote(conn, "SOL-2", "sup://2")
    learning.record_outcome(conn, "SOL-1::sup://1", "won")
    # sup://2's quote stays pending -- no decided history.

    scorecard = learning.supplier_scorecard(conn)
    keys = [row["supplier_key"] for row in scorecard]
    assert keys == ["sup://1"]
    assert scorecard[0]["reliability"] == 1.0
    assert scorecard[0]["decided_quotes"] == 1
