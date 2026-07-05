"""1.3 — /fn-adl: Authorized Distributor Letter acquisition engine.

The cross-join Notion can't do: for each active, live-lane opportunity, resolve
its linked supplier(s) (opportunity_supplier_links) and check whether at least
one has an ADL on file. Surfaces the gap so nothing gets quoted without one.
"""
from datetime import datetime, timezone
from pathlib import Path

from db import connect

TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "templates" / "adl-request.md"

ADL_STATUSES = ("requested", "received", "on_file")
ADL_SATISFIED_STATUSES = ("received", "on_file")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def request_adl(conn, supplier_id: str, notes: str | None = None) -> str:
    """Create or move an ADL request to 'requested' for the given supplier."""
    row = conn.execute(
        "SELECT supplier_name FROM suppliers WHERE notion_url = ?", (supplier_id,)
    ).fetchone()
    if row is None:
        raise ValueError(f"unknown supplier_id: {supplier_id}")
    supplier_name = row[0]

    conn.execute(
        """INSERT INTO adls (adl_key, oem_or_manufacturer, cage_code, status, requested_at, notes)
           VALUES (?, ?, NULL, 'requested', ?, ?)
           ON CONFLICT(adl_key) DO UPDATE SET
             status='requested', requested_at=excluded.requested_at,
             notes=COALESCE(excluded.notes, adls.notes)""",
        (supplier_id, supplier_name, _now(), notes),
    )
    conn.commit()
    return supplier_id


def mark_adl_received(conn, supplier_id: str) -> None:
    conn.execute(
        "UPDATE adls SET status='on_file', received_at=? WHERE adl_key=?",
        (_now(), supplier_id),
    )
    conn.commit()


def render_request_letter(supplier_name: str, entity_config: dict) -> str:
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    return (
        template
        .replace("{{OEM_NAME}}", supplier_name)
        .replace("{{ENTITY_LEGAL_NAME}}", entity_config.get("legal_name", ""))
        .replace("{{ENTITY_DBA}}", entity_config.get("dba", ""))
        .replace("{{ENTITY_UEI}}", entity_config.get("uei") or "PENDING")
        .replace("{{ENTITY_CAGE}}", entity_config.get("cage_code") or "PENDING")
    )


def cross_join_gaps(conn) -> list[dict]:
    """For each active, non-excluded-lane opportunity with >=1 linked supplier,
    flag adl_missing=True unless at least one linked supplier has an ADL on file.

    Opportunities with zero linked suppliers are reported separately (a
    supplier-coverage gap, not an ADL gap -- there's nothing to request an
    ADL from yet).
    """
    opps = conn.execute(
        "SELECT notion_url, title FROM opportunities "
        "WHERE active = 1 AND pipeline != 'No-bid'"
    ).fetchall()

    results = []
    for opp_id, title in opps:
        linked = conn.execute(
            "SELECT supplier_id FROM opportunity_supplier_links WHERE opportunity_id = ?",
            (opp_id,),
        ).fetchall()
        supplier_ids = [r[0] for r in linked]

        if not supplier_ids:
            results.append({
                "opportunity_id": opp_id, "title": title, "linked_suppliers": [],
                "adl_missing": None,  # no supplier link at all -- not an ADL gap yet
            })
            continue

        placeholders = ",".join("?" for _ in supplier_ids)
        adl_rows = conn.execute(
            f"SELECT adl_key, status FROM adls WHERE adl_key IN ({placeholders})",
            supplier_ids,
        ).fetchall()
        satisfied = {k for k, status in adl_rows if status in ADL_SATISFIED_STATUSES}

        results.append({
            "opportunity_id": opp_id,
            "title": title,
            "linked_suppliers": supplier_ids,
            "adl_missing": not any(sid in satisfied for sid in supplier_ids),
        })
    return results


def main() -> None:
    conn = connect()
    gaps = cross_join_gaps(conn)
    conn.close()

    missing = [g for g in gaps if g["adl_missing"] is True]
    no_supplier = [g for g in gaps if g["adl_missing"] is None]
    covered = [g for g in gaps if g["adl_missing"] is False]

    print(f"{len(gaps)} live-lane opportunities checked.")
    print(f"  {len(covered)} have an ADL on file for a linked supplier.")
    print(f"  {len(missing)} have a linked supplier but NO ADL on file yet:")
    for g in missing[:20]:
        print(f"    - {g['title']} ({len(g['linked_suppliers'])} supplier(s) linked)")
    if len(missing) > 20:
        print(f"    ... and {len(missing) - 20} more")
    print(f"  {len(no_supplier)} have no supplier linked at all (coverage gap, not an ADL gap).")


if __name__ == "__main__":
    main()
