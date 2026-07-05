"""3.5 -- /fn-score: transparent weighted ranking, weights in config.json.

Components (each 0-1, combined by weight):
  lane_coverage -- do we already have >=1 supplier linked for this opportunity?
  naics_match   -- does the opportunity's NAICS code match one of ours?

Sole-source opportunities (title says so) are auto no-bid regardless of
score -- ferrum-nexus-BUILD-PACKET.md 3.5's explicit rule, and it matches the
real Ferrum Nexus operating rule ("move ... sole-source OEM ... to No-bid").

Data gap, documented in DECISIONS.md: the Notion export used to seed this
tool did not capture a response-deadline field or set-aside type on
opportunities, so a "deadline band" / "set-aside fit" weight the plan
mentions isn't implemented -- there's nothing to compute it from yet. Adding
those columns to the seed export would let this module pick them up without
changing its shape.

Optional third component, supplier_track_record (see scripts/learning.py):
the average win rate of this opportunity's linked suppliers, across their
DECIDED quote outcomes only. Ships at weight 0.0 by default -- Ferrum Nexus
has no closed transactions yet, so there's no real history to learn from
today, and a weight of 0 keeps every existing score identical until real
outcomes accumulate and someone opts in by raising the weight.
"""
import re

import learning

DEFAULT_WEIGHTS = {"lane_coverage": 0.6, "naics_match": 0.4, "supplier_track_record": 0.0}

_SOLE_SOURCE_RE = re.compile(r"sole[\s-]source", re.IGNORECASE)


def is_sole_source(title: str) -> bool:
    return bool(_SOLE_SOURCE_RE.search(title))


def score_opportunity(conn, opportunity_id: str, entity_naics_codes: list[str],
                       weights: dict | None = None) -> dict:
    weights = weights or DEFAULT_WEIGHTS

    row = conn.execute(
        "SELECT title, naics_code, active, pipeline FROM opportunities WHERE notion_url = ?",
        (opportunity_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"unknown opportunity_id: {opportunity_id}")
    title, naics_code, active, pipeline = row

    if is_sole_source(title):
        return {
            "opportunity_id": opportunity_id, "score": 0.0, "no_bid": True,
            "reasons": ["sole-source -- auto no-bid"],
        }

    if pipeline == "No-bid" or not active:
        return {
            "opportunity_id": opportunity_id, "score": 0.0, "no_bid": True,
            "reasons": [f"pipeline={pipeline!r}, active={bool(active)}"],
        }

    linked_suppliers = conn.execute(
        "SELECT supplier_id FROM opportunity_supplier_links WHERE opportunity_id = ?",
        (opportunity_id,),
    ).fetchall()
    linked = len(linked_suppliers)
    lane_coverage = 1.0 if linked > 0 else 0.0
    naics_match = 1.0 if naics_code and naics_code in entity_naics_codes else 0.0

    score = weights["lane_coverage"] * lane_coverage + weights["naics_match"] * naics_match
    reasons = [
        f"lane_coverage={lane_coverage} ({linked} supplier(s) linked)",
        f"naics_match={naics_match} (opportunity NAICS {naics_code!r})",
    ]

    track_weight = weights.get("supplier_track_record", 0.0)
    if track_weight:
        known = [
            r for (sid,) in linked_suppliers
            if (r := learning.supplier_reliability(conn, sid)) is not None
        ]
        supplier_track_record = sum(known) / len(known) if known else 0.5
        score += track_weight * supplier_track_record
        reasons.append(
            f"supplier_track_record={supplier_track_record:.2f} "
            f"({len(known)}/{linked} linked supplier(s) with decided quote history)"
        )

    return {"opportunity_id": opportunity_id, "score": round(score, 4), "no_bid": False,
            "reasons": reasons}


def score_all(conn, entity_naics_codes: list[str], weights: dict | None = None) -> list[dict]:
    ids = conn.execute(
        "SELECT notion_url FROM opportunities WHERE superseded_by IS NULL"
    ).fetchall()
    results = [score_opportunity(conn, oid, entity_naics_codes, weights) for (oid,) in ids]
    results.sort(key=lambda r: r["score"], reverse=True)
    return results
