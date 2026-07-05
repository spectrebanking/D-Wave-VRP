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


def upsert_opportunity(conn, r: dict) -> None:
    """Shared by the CSV seed loader and notion_sync.py's live path -- both
    produce this exact dict shape, so there's one upsert to keep correct."""
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


def load_opportunities(conn) -> int:
    rows = list(_rows(SEED_DIR / "opportunities.csv"))
    for r in rows:
        upsert_opportunity(conn, r)
    conn.commit()
    return len(rows)


def upsert_supplier(conn, r: dict) -> None:
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


def load_suppliers(conn) -> int:
    rows = list(_rows(SEED_DIR / "suppliers.csv"))
    for r in rows:
        upsert_supplier(conn, r)
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


def upsert_link(conn, opportunity_url: str, supplier_url: str) -> None:
    conn.execute(
        """INSERT INTO opportunity_supplier_links (opportunity_id, supplier_id)
           VALUES (?, ?)
           ON CONFLICT(opportunity_id, supplier_id) DO NOTHING""",
        (opportunity_url, supplier_url),
    )


def load_links(conn) -> int:
    rows = list(_rows(SEED_DIR / "links.csv"))
    for r in rows:
        upsert_link(conn, r["opportunity_url"], r["supplier_url"])
    conn.commit()
    return len(rows)


def load_awards(conn) -> int:
    rows = list(_rows(SEED_DIR / "awards.csv"))
    for r in rows:
        conn.execute(
            """INSERT INTO awards
               (notion_url, award_id, vendor, cage_code, uei, agency, office,
                psc, psc_description, naics_code, naics_description, set_aside,
                value_used, fiscal_year, action_date, description, ferrum_score)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(notion_url) DO UPDATE SET
                 award_id=excluded.award_id, vendor=excluded.vendor,
                 cage_code=excluded.cage_code, uei=excluded.uei,
                 agency=excluded.agency, office=excluded.office, psc=excluded.psc,
                 psc_description=excluded.psc_description, naics_code=excluded.naics_code,
                 naics_description=excluded.naics_description, set_aside=excluded.set_aside,
                 value_used=excluded.value_used, fiscal_year=excluded.fiscal_year,
                 action_date=excluded.action_date, description=excluded.description,
                 ferrum_score=excluded.ferrum_score""",
            (
                r["notion_url"], r["award_id"], r["vendor"], r["cage_code"], r["uei"],
                r["agency"], r["office"], r["psc"], r["psc_description"], r["naics_code"],
                r["naics_description"], r["set_aside"], r["value_used"], r["fiscal_year"],
                r["action_date"], r["description"], r["ferrum_score"],
            ),
        )
    conn.commit()
    return len(rows)


def load_market_intel(conn) -> int:
    rows = list(_rows(SEED_DIR / "market_intel.csv"))
    for r in rows:
        conn.execute(
            """INSERT INTO market_intel
               (notion_url, intel_item, category, priority, value_sum,
                why_it_matters, next_step)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(notion_url) DO UPDATE SET
                 intel_item=excluded.intel_item, category=excluded.category,
                 priority=excluded.priority, value_sum=excluded.value_sum,
                 why_it_matters=excluded.why_it_matters, next_step=excluded.next_step""",
            (
                r["notion_url"], r["intel_item"], r["category"], r["priority"],
                r["value_sum"], r["why_it_matters"], r["next_step"],
            ),
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
    counts["awards"] = load_awards(conn)
    counts["market_intel"] = load_market_intel(conn)
    backfill_solicitation_numbers(conn)
    return counts


if __name__ == "__main__":
    conn = connect()
    counts = load_all(conn)
    for k, v in counts.items():
        print(f"{k}: {v}")
    conn.close()
