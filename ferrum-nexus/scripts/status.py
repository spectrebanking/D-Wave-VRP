"""1.2 — /fn-status: plain-English rollup with the dated critical-path map.

SAM activation is node zero (FSD ref INC-GSAFSD21159287): nothing else in the
critical path can close until it does.
"""
from db import connect
from blockers import list_blockers, critical_path_order, next_action_now


def pipeline_counts(conn) -> dict:
    rows = conn.execute(
        "SELECT pipeline, COUNT(*) FROM opportunities GROUP BY pipeline"
    ).fetchall()
    return dict(rows)


def render(conn) -> str:
    blockers = list_blockers(conn)
    ordered = critical_path_order(blockers)
    nxt = next_action_now(blockers)
    counts = pipeline_counts(conn)

    lines = ["Ferrum Nexus -- status", ""]
    lines.append("Critical path (SAM activation = node zero):")
    for i, b in enumerate(ordered):
        state = "OPEN" if b["status"] == "open" else b["status"].upper()
        lines.append(f"  {i}. [{state}] {b['blocker_key']} -- {b['description']}")
    lines.append("")
    if nxt:
        lines.append(f"NEXT ACTION: {nxt['next_action']}")
        lines.append(f"OWNER: {nxt['owner']}")
        lines.append(f"FOLLOW-UP: {nxt['due_date']}")
    else:
        lines.append("NEXT ACTION: none -- all blockers resolved.")
    lines.append("")
    lines.append("Opportunity pipeline:")
    for stage, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        lines.append(f"  {stage or '(none)'}: {n}")
    return "\n".join(lines)


def main() -> None:
    conn = connect()
    print(render(conn))
    conn.close()


if __name__ == "__main__":
    main()
