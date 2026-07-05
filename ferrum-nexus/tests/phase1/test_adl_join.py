import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from db import connect  # noqa: E402
from adl import request_adl, mark_adl_received, cross_join_gaps  # noqa: E402


def _seed_minimal(conn):
    conn.execute(
        "INSERT INTO opportunities (notion_url, title, product_type, pipeline, active) "
        "VALUES ('opp://1', 'Test valve NSN', 'Valves/Piping', 'Quote', 1)"
    )
    conn.execute(
        "INSERT INTO opportunities (notion_url, title, product_type, pipeline, active) "
        "VALUES ('opp://2', 'Test off-lane', 'Construction/Services', 'No-bid', 1)"
    )
    conn.execute(
        "INSERT INTO opportunities (notion_url, title, product_type, pipeline, active) "
        "VALUES ('opp://3', 'Test uncovered fastener', 'Fasteners', 'Inbox', 1)"
    )
    conn.execute(
        "INSERT INTO suppliers (notion_url, supplier_name, categories, status) "
        "VALUES ('sup://1', 'Test Valve Co', 'Valves/Piping', 'Contacted')"
    )
    conn.execute(
        "INSERT INTO opportunity_supplier_links (opportunity_id, supplier_id) "
        "VALUES ('opp://1', 'sup://1')"
    )
    conn.commit()


def test_solicitation_with_known_cage_and_no_adl_is_flagged_missing(tmp_path):
    conn = connect(db_path=tmp_path / "adl1.db", key="a1" * 32)
    _seed_minimal(conn)

    gaps = {g["opportunity_id"]: g for g in cross_join_gaps(conn)}
    conn.close()

    assert gaps["opp://1"]["adl_missing"] is True


def test_solicitation_with_adl_on_file_is_not_flagged(tmp_path):
    conn = connect(db_path=tmp_path / "adl2.db", key="a2" * 32)
    _seed_minimal(conn)

    request_adl(conn, "sup://1")
    mark_adl_received(conn, "sup://1")

    gaps = {g["opportunity_id"]: g for g in cross_join_gaps(conn)}
    conn.close()

    assert gaps["opp://1"]["adl_missing"] is False


def test_no_bid_lane_is_excluded_entirely(tmp_path):
    conn = connect(db_path=tmp_path / "adl3.db", key="a3" * 32)
    _seed_minimal(conn)

    gaps = {g["opportunity_id"]: g for g in cross_join_gaps(conn)}
    conn.close()

    assert "opp://2" not in gaps  # No-bid lane never enters the ADL check


def test_opportunity_with_no_linked_supplier_is_reported_but_not_adl_missing(tmp_path):
    conn = connect(db_path=tmp_path / "adl4.db", key="a4" * 32)
    _seed_minimal(conn)

    gaps = {g["opportunity_id"]: g for g in cross_join_gaps(conn)}
    conn.close()

    assert gaps["opp://3"]["adl_missing"] is None
    assert gaps["opp://3"]["linked_suppliers"] == []
