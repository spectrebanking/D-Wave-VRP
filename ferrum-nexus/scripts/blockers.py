"""1.1 — Blocker model + /fn-blockers.

Seeds the blocker chain (SAM activation -> API role -> JCP/DD-2345 ->
distributor onboarding -> ADL acquisition -> past-performance/PPQ), each with
an owner + next action + follow-up date, per ferrum-nexus-BUILD-PLAN-v2.md
sections 3-4.
"""
from db import connect

# (blocker_key, description, owner, next_action, due_date, depends_on)
SEED_BLOCKERS = [
    (
        "sam_activation",
        "SAM.gov entity registration (UEI + CAGE) is PENDING, not ACTIVE.",
        "Brocque",
        "Call SAM.gov FSD (866) 606-8220, ref INC-GSAFSD21159287, entity "
        "Apollo Credit Processing LLC, 1111 6th Ave Ste 300, San Diego CA 92101.",
        "Immediate -- call today, then follow up every 3 business days until active",
        None,
    ),
    (
        "api_role_tier",
        "SAM.gov API role tier stuck at 10/day (unauthenticated); needs "
        "entity role for the 1,000/day tier.",
        "Brocque",
        "Confirm entity API role assignment in SAM.gov once activation completes.",
        "Within 24h of SAM activation",
        "sam_activation",
    ),
    (
        "jcp_dd2345",
        "No JCP/DD-2345 certification -> cannot access CUI/export-controlled "
        "engineering drawings (IRPODs) behind SAM's explicit-access wall.",
        "Brocque",
        "File DD-2345 with DLIS once SAM is active.",
        "Within 1 week of SAM activation",
        "sam_activation",
    ),
    (
        "distributor_onboarding",
        "Grainger + MSC both require a Letter of Authorization, Letter of "
        "Introduction, and Sales Tax Certificate before extending government pricing.",
        "Brocque",
        "Send the drafted Letter of Introduction & Authorization (template on file) "
        "plus CA CDTFA-230 resale certificate to Grainger (case #99064281) and MSC "
        "once UEI/CAGE are in hand to fill the entity block.",
        "Within 3 business days of UEI/CAGE issuance",
        "sam_activation",
    ),
    (
        "adl_acquisition",
        "Zero Authorized Distributor Letters collected; NAVSUP disqualifies any "
        "reseller quote without one per line item's manufacturer.",
        "Brocque",
        "Send the ADL request template (templates/adl-request.md) to every "
        "Contacted supplier; track requested/received/on-file in the adls table.",
        "Ongoing -- within 24h of any supplier moving to Contacted",
        None,
    ),
    (
        "past_performance_ppq",
        "Navy BPA path needs 3 Past Performance Questionnaires from customers; "
        "Ferrum has zero closed transactions.",
        "Brocque",
        "Do not spend effort here yet -- route to non-BPA solicitations that "
        "don't require past performance until after the first award.",
        "Revisit after first award; no action before then",
        "sam_activation",
    ),
]


def seed_blockers(conn) -> int:
    for key, desc, owner, next_action, due_date, depends_on in SEED_BLOCKERS:
        conn.execute(
            """INSERT INTO blockers
               (blocker_key, description, owner, next_action, due_date, status, depends_on)
               VALUES (?, ?, ?, ?, ?, 'open', ?)
               ON CONFLICT(blocker_key) DO UPDATE SET
                 description=excluded.description, owner=excluded.owner,
                 next_action=excluded.next_action, due_date=excluded.due_date,
                 depends_on=excluded.depends_on""",
            (key, desc, owner, next_action, due_date, depends_on),
        )
    conn.commit()
    return len(SEED_BLOCKERS)


def list_blockers(conn) -> list[dict]:
    rows = conn.execute(
        "SELECT blocker_key, description, owner, next_action, due_date, status, depends_on "
        "FROM blockers"
    ).fetchall()
    cols = ["blocker_key", "description", "owner", "next_action", "due_date", "status",
            "depends_on"]
    return [dict(zip(cols, row)) for row in rows]


def critical_path_order(blockers: list[dict]) -> list[dict]:
    """Topological order by depends_on, root (depends_on=None) first."""
    by_key = {b["blocker_key"]: b for b in blockers}
    ordered: list[dict] = []
    seen: set[str] = set()

    def visit(b: dict):
        if b["blocker_key"] in seen:
            return
        if b["depends_on"] and b["depends_on"] in by_key:
            visit(by_key[b["depends_on"]])
        seen.add(b["blocker_key"])
        ordered.append(b)

    for b in blockers:
        visit(b)
    return ordered


def next_action_now(blockers: list[dict]) -> dict | None:
    """First still-open blocker in critical-path order -- the single next action."""
    for b in critical_path_order(blockers):
        if b["status"] == "open":
            return b
    return None


def main() -> None:
    conn = connect()
    n = seed_blockers(conn)
    blockers = list_blockers(conn)
    conn.close()

    print(f"{n} blockers on file.\n")
    print("Critical path (root -> leaf):")
    for b in critical_path_order(blockers):
        marker = "->" if b["status"] == "open" else "  "
        print(f"  {marker} [{b['status']:>4}] {b['blocker_key']}: {b['description']}")
        print(f"        owner: {b['owner']} | next action: {b['next_action']}")
        if b["due_date"]:
            print(f"        due: {b['due_date']}")

    nxt = next_action_now(blockers)
    if nxt:
        print(f"\nSINGLE NEXT ACTION: {nxt['next_action']} (owner: {nxt['owner']})")
    else:
        print("\nAll blockers resolved.")


if __name__ == "__main__":
    main()
