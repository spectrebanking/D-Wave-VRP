import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from db import connect  # noqa: E402
from id_resolver import parse_sol_number, backfill_solicitation_numbers, resolve_opportunity  # noqa: E402


def test_parse_sol_number_em_dash_title():
    assert parse_sol_number("N0010426QNB47 — NUT,SELF-LOCKING,HEXAGON") == "N0010426QNB47"


def test_parse_sol_number_hyphenated_title():
    assert parse_sol_number(
        "W912CH-25-Q-0015 for Airflow Valve; NSN: 4240-01-055-1493"
    ) == "W912CH-25-Q-0015"


def test_parse_sol_number_returns_none_for_plain_title():
    assert parse_sol_number("GASKET, HYBRID") is None


def test_parse_sol_number_returns_none_for_psc_code_prefixed_title():
    # Real false positive caught in this dataset: "87" is a PSC code, not part
    # of a solicitation number -- digit-sparse token, must not match.
    assert parse_sol_number("87--WI-GENOA NFH-CHIRONOMID BLOODWORMS") is None


def test_parse_sol_number_matches_digit_dense_project_number():
    assert parse_sol_number(
        "Z2NE--544-22-115 Replace Water and Fire Piping Loop"
    ) == "Z2NE--544-22-115"


def test_backfill_and_resolve_by_sol_number(tmp_path):
    conn = connect(db_path=tmp_path / "r1.db", key="r1" * 32)
    conn.execute(
        "INSERT INTO opportunities (notion_url, title) VALUES "
        "('opp://1', 'N0010426QNB47 — NUT,SELF-LOCKING,HEXAGON')"
    )
    conn.commit()

    updated = backfill_solicitation_numbers(conn)
    assert updated == 1

    found = resolve_opportunity(conn, "N0010426QNB47")
    conn.close()
    assert found["notion_url"] == "opp://1"


def test_resolve_by_notice_id_once_phase3_populates_it(tmp_path):
    conn = connect(db_path=tmp_path / "r2.db", key="r2" * 32)
    conn.execute(
        "INSERT INTO opportunities (notion_url, title, notice_id) VALUES "
        "('opp://2', 'N0010426QNB48 — BALL,SEAT SET', 'NOTICE-XYZ')"
    )
    conn.commit()

    # Phase 2 never populated solicitation_number for this row; a Phase-3-style
    # ingestion identifies it purely by noticeId. resolve_opportunity must still
    # find it -- that's the point of the resolver.
    found = resolve_opportunity(conn, "NOTICE-XYZ")
    conn.close()
    assert found["notion_url"] == "opp://2"


def test_resolve_returns_none_for_unknown_key(tmp_path):
    conn = connect(db_path=tmp_path / "r3.db", key="r3" * 32)
    result = resolve_opportunity(conn, "NOPE")
    conn.close()
    assert result is None
