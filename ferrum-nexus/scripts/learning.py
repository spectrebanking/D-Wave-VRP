"""/fn-outcome + the recursive-learning feedback loop: quote outcomes (won /
lost / no_response) feed back into a per-supplier reliability figure that
score.py can optionally weigh via the 'supplier_track_record' component.

This does NOT retroactively rewrite scoring behavior by default --
score.DEFAULT_WEIGHTS ships supplier_track_record at 0.0, so nothing changes
until real outcomes accumulate and someone opts in by raising that weight.
That's a deliberate choice: Ferrum Nexus has no closed transactions yet (per
the live Notion execution-status notes), so there is no real history to learn
from today -- this wires the mechanism so it activates itself as outcomes get
recorded, without a code change later.
"""
from datetime import datetime, timezone

_VALID_OUTCOMES = {"pending", "won", "lost", "no_response"}
_DECIDED_FILTER_SQL = "qo.outcome IN ('won', 'lost')"


def record_outcome(conn, quote_key: str, outcome: str, notes: str | None = None) -> None:
    if outcome not in _VALID_OUTCOMES:
        raise ValueError(f"outcome must be one of {sorted(_VALID_OUTCOMES)}, got {outcome!r}")

    quote_row = conn.execute(
        "SELECT quote_key FROM quotes WHERE quote_key = ?", (quote_key,)
    ).fetchone()
    if quote_row is None:
        raise ValueError(f"unknown quote_key: {quote_key!r} -- run /fn-quote-add first")

    decided_at = None if outcome == "pending" else datetime.now(timezone.utc).isoformat()
    conn.execute(
        """INSERT INTO quote_outcomes (quote_key, outcome, decided_at, notes)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(quote_key) DO UPDATE SET
             outcome=excluded.outcome, decided_at=excluded.decided_at, notes=excluded.notes""",
        (quote_key, outcome, decided_at, notes),
    )
    conn.commit()


def supplier_reliability(conn, supplier_key: str) -> float | None:
    """Win rate across this supplier's DECIDED quote outcomes. Returns None
    when there's no decided history yet -- callers must treat that as
    'unknown', never as zero (an unproven supplier is not the same as an
    unreliable one)."""
    rows = conn.execute(
        f"""SELECT qo.outcome FROM quote_outcomes qo
            JOIN quotes q ON q.quote_key = qo.quote_key
            WHERE q.supplier_key = ? AND {_DECIDED_FILTER_SQL}""",
        (supplier_key,),
    ).fetchall()
    if not rows:
        return None
    wins = sum(1 for (outcome,) in rows if outcome == "won")
    return wins / len(rows)


def supplier_scorecard(conn) -> list[dict]:
    """One row per supplier with decided quote history, most reliable first."""
    supplier_keys = conn.execute(
        "SELECT DISTINCT supplier_key FROM quotes WHERE supplier_key IS NOT NULL"
    ).fetchall()

    scorecard = []
    for (supplier_key,) in supplier_keys:
        reliability = supplier_reliability(conn, supplier_key)
        if reliability is None:
            continue
        n_decided = conn.execute(
            f"""SELECT COUNT(*) FROM quote_outcomes qo
                JOIN quotes q ON q.quote_key = qo.quote_key
                WHERE q.supplier_key = ? AND {_DECIDED_FILTER_SQL}""",
            (supplier_key,),
        ).fetchone()[0]
        scorecard.append({
            "supplier_key": supplier_key,
            "reliability": round(reliability, 4),
            "decided_quotes": n_decided,
        })
    scorecard.sort(key=lambda r: r["reliability"], reverse=True)
    return scorecard
