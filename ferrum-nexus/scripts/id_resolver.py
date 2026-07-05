"""[0.6 consensus fix] sol# <-> noticeId resolver.

Phase 2 (/fn-specs, /fn-quote) keys work by solicitation number, parsed today
from the opportunity title (e.g. "N0010426QNB47 -- NUT,SELF-LOCKING,HEXAGON"
-> "N0010426QNB47"). Phase 3 (/fn-pull) will upsert opportunities by
SAM.gov's noticeId instead. Both columns live on the same `opportunities` row
(see schema.sql) so a Phase-2 lookup by sol# still finds a row that Phase 3
later enriches with its noticeId -- no migration needed when Phase 3 lands.
"""
import re

# Solicitation numbers in this dataset look like: N0010426QNB47, SPRMM126QHC20,
# W912CH-25-Q-0015, 15BFA023Q00000117, SPRHA1-26-Q-0641 -- always the leading
# whitespace-delimited token, 11+ chars of [A-Z0-9-], digit-dense (>=30% of
# characters are digits). Plain nomenclature titles ("GASKET") fail length;
# PSC-code-prefixed titles ("87--WI-GENOA NFH-...", a real false positive
# caught during Phase 2 verification) are long enough and contain a digit but
# are digit-*sparse* (2/12 = 17%), so the density check correctly excludes them.
_SOL_TOKEN_RE = re.compile(r"^[A-Z0-9][A-Z0-9\-]{10,}$")
_MIN_DIGIT_DENSITY = 0.3


def parse_sol_number(title: str) -> str | None:
    """Best-effort extraction of a solicitation number from an opportunity title."""
    first_token = title.split(None, 1)[0] if title.split() else ""
    if not _SOL_TOKEN_RE.match(first_token):
        return None
    digit_density = sum(c.isdigit() for c in first_token) / len(first_token)
    if digit_density < _MIN_DIGIT_DENSITY:
        return None
    return first_token


def backfill_solicitation_numbers(conn) -> int:
    """Populate opportunities.solicitation_number from title for rows missing it."""
    rows = conn.execute(
        "SELECT notion_url, title FROM opportunities WHERE solicitation_number IS NULL"
    ).fetchall()
    updated = 0
    for notion_url, title in rows:
        sol = parse_sol_number(title)
        if sol:
            conn.execute(
                "UPDATE opportunities SET solicitation_number = ? WHERE notion_url = ?",
                (sol, notion_url),
            )
            updated += 1
    conn.commit()
    return updated


def resolve_opportunity(conn, key: str) -> dict | None:
    """Resolve an opportunity by solicitation_number OR notice_id OR notion_url.

    Returns the row as a dict, or None if no match. This is the single lookup
    path both Phase 2 (sol#) and Phase 3 (noticeId) should use, so neither
    phase needs to know which identifier the other populated.
    """
    row = conn.execute(
        """SELECT notion_url, title, product_type, pipeline, active,
                  solicitation_number, notice_id
           FROM opportunities
           WHERE solicitation_number = ? OR notice_id = ? OR notion_url = ?
           LIMIT 1""",
        (key, key, key),
    ).fetchone()
    if row is None:
        return None
    cols = ["notion_url", "title", "product_type", "pipeline", "active",
            "solicitation_number", "notice_id"]
    return dict(zip(cols, row))
