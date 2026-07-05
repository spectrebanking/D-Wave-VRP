"""PREREQ P.1 — build seed/*.csv from the raw exports in scripts/_seed_*.py.

Run: uv run python scripts/build_seed_csvs.py
Writes seed/opportunities.csv, seed/suppliers.csv, seed/co_clusters.csv and prints row counts.
"""
import csv
from pathlib import Path

from _seed_opportunities import OPPORTUNITIES
from _seed_suppliers import SUPPLIERS
from _seed_co_clusters import CO_CLUSTERS
from _seed_links import LINKS
from _seed_awards import AWARDS
from _seed_market_intel import MARKET_INTEL

ROOT = Path(__file__).resolve().parent.parent
SEED_DIR = ROOT / "seed"


def write_csv(path, header, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        for row in rows:
            w.writerow(["" if v is None else v for v in row])
    return len(rows)


def main():
    SEED_DIR.mkdir(exist_ok=True)

    n_opps = write_csv(
        SEED_DIR / "opportunities.csv",
        ["notion_url", "title", "product_type", "pipeline", "active",
         "supplier_coverage_status", "naics_code"],
        OPPORTUNITIES,
    )
    n_suppliers = write_csv(
        SEED_DIR / "suppliers.csv",
        ["notion_url", "supplier_name", "categories", "status", "email",
         "keywords", "naics", "supplier_type"],
        SUPPLIERS,
    )
    n_clusters = write_csv(
        SEED_DIR / "co_clusters.csv",
        ["cluster_name", "agency", "item_count", "deadline_window", "notes"],
        CO_CLUSTERS,
    )
    n_links = write_csv(
        SEED_DIR / "links.csv",
        ["opportunity_url", "supplier_url"],
        sorted(set(LINKS)),
    )
    n_awards = write_csv(
        SEED_DIR / "awards.csv",
        ["notion_url", "award_id", "vendor", "cage_code", "uei", "agency", "office",
         "psc", "psc_description", "naics_code", "naics_description", "set_aside",
         "value_used", "fiscal_year", "action_date", "description", "ferrum_score"],
        AWARDS,
    )
    n_intel = write_csv(
        SEED_DIR / "market_intel.csv",
        ["notion_url", "intel_item", "category", "priority", "value_sum",
         "why_it_matters", "next_step"],
        MARKET_INTEL,
    )

    print(f"opportunities.csv: {n_opps} rows")
    print(f"suppliers.csv: {n_suppliers} rows")
    print(f"co_clusters.csv: {n_clusters} rows")
    print(f"links.csv: {n_links} rows")
    print(f"awards.csv: {n_awards} rows")
    print(f"market_intel.csv: {n_intel} rows")


if __name__ == "__main__":
    main()
