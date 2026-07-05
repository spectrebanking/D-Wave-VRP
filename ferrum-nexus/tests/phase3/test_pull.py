import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from db import connect  # noqa: E402
from pull import upsert_opportunity_from_notice, pull_page, current_opportunity_count  # noqa: E402


def test_fresh_notice_inserts_one_row(tmp_path):
    conn = connect(db_path=tmp_path / "p1.db", key="p1" * 32)
    result = upsert_opportunity_from_notice(conn, {
        "noticeId": "N-1", "title": "N0010426QXX01 -- WIDGET", "updatedDate": "2026-07-01",
    })
    conn.close()
    assert result["action"] == "inserted"


def test_repulling_identical_notice_does_not_duplicate(tmp_path):
    conn = connect(db_path=tmp_path / "p2.db", key="p2" * 32)
    notice = {"noticeId": "N-2", "title": "Widget", "updatedDate": "2026-07-01"}
    upsert_opportunity_from_notice(conn, notice)
    result = upsert_opportunity_from_notice(conn, notice)

    count = conn.execute(
        "SELECT COUNT(*) FROM opportunities WHERE notice_id = ?", ("N-2",)
    ).fetchone()[0]
    conn.close()

    assert result["action"] == "unchanged"
    assert count == 1


def test_amended_notice_creates_new_row_and_supersedes_old(tmp_path):
    conn = connect(db_path=tmp_path / "p3.db", key="p3" * 32)
    upsert_opportunity_from_notice(conn, {
        "noticeId": "N-3", "title": "Widget v1", "updatedDate": "2026-07-01",
    })
    v2 = upsert_opportunity_from_notice(conn, {
        "noticeId": "N-3", "title": "Widget v2 (amended)", "updatedDate": "2026-07-04",
    })

    all_rows = conn.execute(
        "SELECT notion_url, title, superseded_by FROM opportunities WHERE notice_id = ? "
        "ORDER BY notice_updated_at",
        ("N-3",),
    ).fetchall()
    current_rows = conn.execute(
        "SELECT notion_url FROM opportunities WHERE notice_id = ? AND superseded_by IS NULL",
        ("N-3",),
    ).fetchall()
    conn.close()

    assert v2["action"] == "superseded"
    assert len(all_rows) == 2, "amendment must keep history, not overwrite"
    assert all_rows[0][2] == v2["notion_url"], "v1 row must point superseded_by at v2"
    assert len(current_rows) == 1, "exactly one current (non-superseded) row per noticeId"
    assert current_rows[0][0] == v2["notion_url"]


def test_pull_page_dedups_across_a_results_page(tmp_path):
    conn = connect(db_path=tmp_path / "p4.db", key="p4" * 32)
    page = {"opportunitiesData": [
        {"noticeId": "N-4", "title": "A", "updatedDate": "2026-07-01"},
        {"noticeId": "N-5", "title": "B", "updatedDate": "2026-07-01"},
    ]}
    counts1 = pull_page(conn, page)
    counts2 = pull_page(conn, page)  # re-pull same page
    total = current_opportunity_count(conn)
    conn.close()

    assert counts1 == {"inserted": 2, "unchanged": 0, "superseded": 0}
    assert counts2 == {"inserted": 0, "unchanged": 2, "superseded": 0}
    assert total >= 2  # at least these 2 current rows (fresh db, so exactly 2)
