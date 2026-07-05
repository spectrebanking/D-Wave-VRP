"""/fn-sync's live half: pulls opportunities, suppliers, and supplier links
directly from Notion and upserts them through the exact same seed.py helpers
the CSV path uses -- one upsert path for both, no drift between a live sync
and a one-shot CSV seed.

Data source IDs are pinned below (confirmed live 2026-07-05 against this
workspace's actual schemas -- property names came from fetching each data
source's schema directly, not guessed). Requires a real Notion integration
token (credentials.get_notion_token()); not exercised against the live API in
this build/test environment -- see notion_client.py's module docstring and
DECISIONS.md for the same posture already documented for sam_client.py.
"""
from notion_client import NotionClient, flatten_page

import seed

OPPORTUNITIES_DATA_SOURCE = "acb1ce83-f079-4067-8a4c-aa531215e547"
SUPPLIERS_DATA_SOURCE = "9e990aac-304a-4819-ab91-ad1a594ead37"
LINKS_DATA_SOURCE = "be75b27b-51dd-4e3b-88fd-580759df5122"


def _opportunity_row(flat: dict) -> dict:
    return {
        "notion_url": flat["notion_url"],
        "title": flat.get("Title") or "",
        "product_type": flat.get("Product Type"),
        "pipeline": flat.get("Pipeline"),
        "active": "True" if flat.get("Active") else "False",
        "supplier_coverage_status": flat.get("Supplier Coverage Status"),
        "naics_code": flat.get("NaicsCode"),
    }


def _supplier_row(flat: dict) -> dict:
    return {
        "notion_url": flat["notion_url"],
        "supplier_name": flat.get("Supplier") or "",
        "categories": flat.get("Categories"),
        "status": flat.get("Status"),
        "email": flat.get("Email"),
        "keywords": flat.get("Keywords"),
        "naics": flat.get("NAICS"),
        "supplier_type": flat.get("Supplier Type"),
    }


def sync_opportunities(conn, client: NotionClient) -> int:
    n = 0
    for page_payload in client.query_all_pages(OPPORTUNITIES_DATA_SOURCE):
        for page in page_payload.get("results", []):
            row = _opportunity_row(flatten_page(page))
            if not row["title"]:
                continue
            seed.upsert_opportunity(conn, row)
            n += 1
    conn.commit()
    return n


def sync_suppliers(conn, client: NotionClient) -> int:
    n = 0
    for page_payload in client.query_all_pages(SUPPLIERS_DATA_SOURCE):
        for page in page_payload.get("results", []):
            row = _supplier_row(flatten_page(page))
            if not row["supplier_name"]:
                continue
            seed.upsert_supplier(conn, row)
            n += 1
    conn.commit()
    return n


def sync_links(conn, client: NotionClient) -> int:
    """Cross-joins each outreach row's Opportunity/Supplier relation arrays,
    same rule as the seed export: a CO-contact row with no Supplier relation
    contributes no links (a CO is not a supplier)."""
    n = 0
    for page_payload in client.query_all_pages(LINKS_DATA_SOURCE):
        for page in page_payload.get("results", []):
            flat = flatten_page(page)
            opportunities = flat.get("Opportunity") or []
            suppliers = flat.get("Supplier") or []
            for opp_url in opportunities:
                for sup_url in suppliers:
                    seed.upsert_link(conn, opp_url, sup_url)
                    n += 1
    conn.commit()
    return n


def sync_all(conn, client: NotionClient) -> dict:
    return {
        "opportunities": sync_opportunities(conn, client),
        "suppliers": sync_suppliers(conn, client),
        "opportunity_supplier_links": sync_links(conn, client),
    }


if __name__ == "__main__":
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import credentials
    from db import connect

    token = credentials.get_notion_token()
    if not token:
        print("No Notion integration token on file -- run /fn-setup or "
              "credentials.store_notion_token() first.")
        sys.exit(1)

    conn = connect()
    client = NotionClient(token=token)
    counts = sync_all(conn, client)
    for k, v in counts.items():
        print(f"{k}: {v} synced from live Notion")
    conn.close()
