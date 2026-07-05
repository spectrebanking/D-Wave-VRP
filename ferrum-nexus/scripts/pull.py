"""3.2 -- /fn-pull: pull opportunities from SAM.gov, upsert by noticeId.

Amendment churn: SAM's search endpoint returns only the latest active
version of a notice per noticeId. On re-pull, if notice_updated_at differs
from what's on file, the OLD row is kept (history) and a NEW row is inserted
for the amended version, with the old row's superseded_by pointing at the
new one. Re-pulling an unchanged notice is a no-op (dedup by noticeId).

Freshly-pulled notices with no corresponding Notion page yet get a synthetic
notion_url of `sam://{notice_id}#{notice_updated_at}` -- see DECISIONS.md for
why (this schema's primary key predates a live SAM feed and assumed Notion
as the id source; Phase 5's optional Notion sync is expected to replace the
synthetic id with a real Notion URL once a page exists).
"""
from id_resolver import parse_sol_number


def _current_row_for_notice(conn, notice_id: str):
    return conn.execute(
        "SELECT notion_url, notice_updated_at FROM opportunities "
        "WHERE notice_id = ? AND superseded_by IS NULL",
        (notice_id,),
    ).fetchone()


def upsert_opportunity_from_notice(conn, notice: dict) -> dict:
    """notice: {'noticeId', 'title', 'type', 'active', 'updatedDate' (or similar)}.
    Returns {'action': 'inserted'|'unchanged'|'superseded', 'notion_url': ...}.
    """
    notice_id = notice["noticeId"]
    title = notice.get("title", "")
    updated_at = notice.get("updatedDate") or notice.get("postedDate") or ""

    current = _current_row_for_notice(conn, notice_id)

    if current is not None:
        current_url, current_updated_at = current
        if current_updated_at == updated_at:
            return {"action": "unchanged", "notion_url": current_url}

    new_url = f"sam://{notice_id}#{updated_at or 'v1'}"
    sol_number = parse_sol_number(title)

    conn.execute(
        """INSERT INTO opportunities
           (notion_url, title, active, solicitation_number, notice_id, notice_updated_at)
           VALUES (?, ?, ?, ?, ?, ?)
           ON CONFLICT(notion_url) DO NOTHING""",
        (new_url, title, 1 if notice.get("active", True) else 0, sol_number,
         notice_id, updated_at),
    )

    if current is not None:
        conn.execute(
            "UPDATE opportunities SET superseded_by = ? WHERE notion_url = ?",
            (new_url, current[0]),
        )
        conn.commit()
        return {"action": "superseded", "notion_url": new_url, "superseded": current[0]}

    conn.commit()
    return {"action": "inserted", "notion_url": new_url}


def pull_page(conn, page: dict) -> dict:
    """Ingest one search-results page. Returns action counts."""
    counts = {"inserted": 0, "unchanged": 0, "superseded": 0}
    for notice in page.get("opportunitiesData", []):
        result = upsert_opportunity_from_notice(conn, notice)
        counts[result["action"]] += 1
    return counts


def current_opportunity_count(conn) -> int:
    return conn.execute(
        "SELECT COUNT(*) FROM opportunities WHERE superseded_by IS NULL"
    ).fetchone()[0]
