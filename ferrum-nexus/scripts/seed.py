"""0.4 — idempotent seed loader: seed/*.csv -> encrypted store."""
import csv
from pathlib import Path

from db import connect
from id_resolver import backfill_solicitation_numbers

SEED_DIR = Path(__file__).resolve().parent.parent / "seed"


def _rows(csv_path: Path):
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            yield {k: (v if v != "" else None) for k, v in row.items()}


def load_opportunities(conn) -> int:
    rows = list(_rows(SEED_DIR / "opportunities.csv"))
    for r in rows:
        conn.execute(
            """INSERT INTO opportunities
               (notion_url, title, product_type, pipeline, active,
                supplier_coverage_status, naics_code)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(notion_url) DO UPDATE SET
                 title=excluded.title, product_type=excluded.product_type,
                 pipeline=excluded.pipeline, active=excluded.active,
                 supplier_coverage_status=excluded.supplier_coverage_status,
                 naics_code=excluded.naics_code""",
            (
                r["notion_url"], r["title"], r["product_type"], r["pipeline"],
                1 if r["active"] in ("True", "1", True) else 0,
                r["supplier_coverage_status"], r["naics_code"],
            ),
        )
    conn.commit()
    return len(rows)


def load_suppliers(conn) -> int:
    rows = list(_rows(SEED_DIR / "suppliers.csv"))
    for r in rows:
        conn.execute(
            """INSERT INTO suppliers
               (notion_url, supplier_name, categories, status, email,
                keywords, naics, supplier_type)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(notion_url) DO UPDATE SET
                 supplier_name=excluded.supplier_name, categories=excluded.categories,
                 status=excluded.status, email=excluded.email, keywords=excluded.keywords,
                 naics=excluded.naics, supplier_type=excluded.supplier_type""",
            (
                r["notion_url"], r["supplier_name"], r["categories"], r["status"],
                r["email"], r["keywords"], r["naics"], r["supplier_type"],
            ),
        )
    conn.commit()
    return len(rows)


def load_co_clusters(conn) -> int:
    rows = list(_rows(SEED_DIR / "co_clusters.csv"))
    for r in rows:
        conn.execute(
            """INSERT INTO co_clusters (cluster_name, agency, item_count, deadline_window, notes)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(cluster_name) DO UPDATE SET
                 agency=excluded.agency, item_count=excluded.item_count,
                 deadline_window=excluded.deadline_window, notes=excluded.notes""",
            (r["cluster_name"], r["agency"], r["item_count"], r["deadline_window"], r["notes"]),
        )
    conn.commit()
    return len(rows)


def load_links(conn) -> int:
    rows = list(_rows(SEED_DIR / "links.csv"))
    for r in rows:
        conn.execute(
            """INSERT INTO opportunity_supplier_links (opportunity_id, supplier_id)
               VALUES (?, ?)
               ON CONFLICT(opportunity_id, supplier_id) DO NOTHING""",
            (r["opportunity_url"], r["supplier_url"]),
        )
    conn.commit()
    return len(rows)


def load_all(conn) -> dict:
    # Order matters: links.csv references opportunities + suppliers by URL.
    counts = {
        "opportunities": load_opportunities(conn),
        "suppliers": load_suppliers(conn),
        "co_clusters": load_co_clusters(conn),
    }
    counts["opportunity_supplier_links"] = load_links(conn)
    backfill_solicitation_numbers(conn)
    return counts


if __name__ == "__main__":
    conn = connect()
    counts = load_all(conn)
    for k, v in counts.items():
        print(f"{k}: {v}")
    conn.close()
