"""/fn-awards -- FPDS award/market intelligence. Awards are ALREADY-AWARDED
contracts pulled as competitor/market intel, not opportunities to bid on;
this module reads them read-only and cross-references against live seeded
opportunities to find lanes with proven government buying history."""

_PRIORITY_ORDER = {"P0 Review Now": 0, "P1 Good": 1, "P2 Watch": 2}


def naics_matches_for_award(conn, naics_code: str):
    """Live, current opportunities sharing this award's NAICS code -- i.e. a
    lane where we've already seen the government actually buy, not just post
    a solicitation that may go nowhere."""
    if not naics_code:
        return []
    return conn.execute(
        "SELECT notion_url, title FROM opportunities "
        "WHERE naics_code = ? AND active = 1 AND superseded_by IS NULL",
        (naics_code,),
    ).fetchall()


def award_naics_overlap_report(conn) -> list[dict]:
    """For every seeded award, which live opportunities share its NAICS code."""
    awards = conn.execute(
        "SELECT notion_url, award_id, vendor, naics_code, naics_description, "
        "psc, psc_description, value_used FROM awards"
    ).fetchall()
    report = []
    for notion_url, award_id, vendor, naics_code, naics_description, psc, psc_description, value_used in awards:
        matches = naics_matches_for_award(conn, naics_code)
        report.append({
            "notion_url": notion_url,
            "award_id": award_id,
            "vendor": vendor,
            "naics_code": naics_code,
            "naics_description": naics_description,
            "psc": psc,
            "psc_description": psc_description,
            "value_used": value_used,
            "matching_opportunities": [{"notion_url": u, "title": t} for u, t in matches],
        })
    return report


def render_market_intel(conn) -> str:
    rows = conn.execute(
        "SELECT intel_item, category, priority, value_sum, why_it_matters, next_step "
        "FROM market_intel"
    ).fetchall()
    rows.sort(key=lambda r: (_PRIORITY_ORDER.get(r[2], 9), -(r[3] or 0)))

    lines = ["FERRUM MARKET INTELLIGENCE (from FPDS award pull)", ""]
    for intel_item, category, priority, value_sum, why_it_matters, next_step in rows:
        value_str = f"${value_sum:,.0f}" if value_sum else "n/a"
        lines.append(f"[{priority}] ({category}) {intel_item}")
        lines.append(f"  value: {value_str}")
        lines.append(f"  why: {why_it_matters}")
        lines.append(f"  next: {next_step}")
        lines.append("")
    return "\n".join(lines)


def render_naics_overlap(conn) -> str:
    report = award_naics_overlap_report(conn)
    lines = ["FPDS AWARDS <-> LIVE OPPORTUNITY NAICS OVERLAP", ""]
    for entry in report:
        lines.append(
            f"{entry['award_id']} — {entry['vendor']} "
            f"(NAICS {entry['naics_code']}: {entry['naics_description']}, "
            f"${entry['value_used']:,.0f})" if entry["value_used"] else
            f"{entry['award_id']} — {entry['vendor']} (NAICS {entry['naics_code']})"
        )
        if entry["matching_opportunities"]:
            for m in entry["matching_opportunities"]:
                lines.append(f"    -> live match: {m['title']}")
        else:
            lines.append("    -> no live opportunity shares this NAICS code yet")
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from db import connect

    conn = connect()
    print(render_market_intel(conn))
    print(render_naics_overlap(conn))
    conn.close()
