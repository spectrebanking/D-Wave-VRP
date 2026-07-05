import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from db import connect  # noqa: E402
from notion_client import NotionClient  # noqa: E402
import notion_sync  # noqa: E402


def _opp_page(page_id: str, title: str, naics: str, active: bool = True) -> dict:
    return {
        "id": page_id,
        "properties": {
            "Title": {"type": "title", "title": [{"plain_text": title}]},
            "Product Type": {"type": "select", "select": {"name": "Steel/Fab"}},
            "Pipeline": {"type": "status", "status": {"name": "Inbox"}},
            "Active": {"type": "checkbox", "checkbox": active},
            "Supplier Coverage Status": {"type": "select", "select": {"name": "No Supplier"}},
            "NaicsCode": {"type": "rich_text", "rich_text": [{"plain_text": naics}]},
        },
    }


def _supplier_page(page_id: str, name: str) -> dict:
    return {
        "id": page_id,
        "properties": {
            "Supplier": {"type": "title", "title": [{"plain_text": name}]},
            "Categories": {"type": "multi_select", "multi_select": [{"name": "Steel/Fab"}]},
            "Status": {"type": "status", "status": {"name": "Prospect"}},
            "Email": {"type": "email", "email": "sales@example.test"},
            "Keywords": {"type": "rich_text", "rich_text": []},
            "NAICS": {"type": "rich_text", "rich_text": [{"plain_text": "332722"}]},
            "Supplier Type": {"type": "select", "select": {"name": "Distributor"}},
        },
    }


def _link_page(page_id: str, opp_ids: list[str], supplier_ids: list[str] | None) -> dict:
    return {
        "id": page_id,
        "properties": {
            "Outreach": {"type": "title", "title": [{"plain_text": "Test outreach"}]},
            "Opportunity": {"type": "relation", "relation": [{"id": i} for i in opp_ids]},
            "Supplier": {
                "type": "relation",
                "relation": [{"id": i} for i in supplier_ids] if supplier_ids else [],
            },
        },
    }


def _one_page_transport(results: list[dict]):
    def transport(url, body):
        return 200, {"results": results, "has_more": False, "next_cursor": None}
    return transport


def test_sync_opportunities_upserts_via_shared_seed_helper(tmp_path):
    conn = connect(db_path=tmp_path / "t1.db", key="a" * 64)
    client = NotionClient(
        token="fake",
        transport=_one_page_transport([_opp_page("opp1234", "Test Opportunity", "332722")]),
    )
    n = notion_sync.sync_opportunities(conn, client)
    assert n == 1

    row = conn.execute(
        "SELECT title, naics_code, active FROM opportunities WHERE notion_url = ?",
        ("https://app.notion.com/opp1234",),
    ).fetchone()
    assert row == ("Test Opportunity", "332722", 1)
    conn.close()


def test_sync_opportunities_skips_rows_with_no_title(tmp_path):
    conn = connect(db_path=tmp_path / "t2.db", key="b" * 64)
    blank = _opp_page("opp0000", "", "332722")
    blank["properties"]["Title"]["title"] = []
    client = NotionClient(token="fake", transport=_one_page_transport([blank]))

    n = notion_sync.sync_opportunities(conn, client)
    assert n == 0
    conn.close()


def test_sync_suppliers_upserts_via_shared_seed_helper(tmp_path):
    conn = connect(db_path=tmp_path / "t3.db", key="c" * 64)
    client = NotionClient(
        token="fake",
        transport=_one_page_transport([_supplier_page("sup1234", "Test Supplier Co")]),
    )
    n = notion_sync.sync_suppliers(conn, client)
    assert n == 1

    row = conn.execute(
        "SELECT supplier_name, supplier_type FROM suppliers WHERE notion_url = ?",
        ("https://app.notion.com/sup1234",),
    ).fetchone()
    assert row == ("Test Supplier Co", "Distributor")
    conn.close()


def test_sync_links_cross_joins_relation_arrays(tmp_path):
    conn = connect(db_path=tmp_path / "t4.db", key="d" * 64)
    client = NotionClient(
        token="fake",
        transport=_one_page_transport([
            _link_page("lnk0001", ["oppA", "oppB"], ["supX", "supY"]),
        ]),
    )
    n = notion_sync.sync_links(conn, client)
    assert n == 4  # 2 opportunities x 2 suppliers

    rows = conn.execute(
        "SELECT opportunity_id, supplier_id FROM opportunity_supplier_links ORDER BY 1, 2"
    ).fetchall()
    assert len(rows) == 4
    assert ("https://app.notion.com/oppA", "https://app.notion.com/supX") in rows
    conn.close()


def test_sync_links_excludes_co_contact_rows_with_no_supplier(tmp_path):
    conn = connect(db_path=tmp_path / "t5.db", key="e" * 64)
    client = NotionClient(
        token="fake",
        transport=_one_page_transport([_link_page("lnk0002", ["oppC"], None)]),
    )
    n = notion_sync.sync_links(conn, client)
    assert n == 0
    conn.close()


def test_sync_all_returns_counts_for_all_three_tables(tmp_path):
    conn = connect(db_path=tmp_path / "t6.db", key="f" * 64)

    def multi_transport(url, body):
        if "acb1ce83" in url:
            return 200, {"results": [_opp_page("oppZ", "Z Opp", "332722")], "has_more": False}
        if "9e990aac" in url:
            return 200, {"results": [_supplier_page("supZ", "Z Supplier")], "has_more": False}
        return 200, {"results": [_link_page("lnkZ", ["oppZ"], ["supZ"])], "has_more": False}

    client = NotionClient(token="fake", transport=multi_transport)
    counts = notion_sync.sync_all(conn, client)

    assert counts == {"opportunities": 1, "suppliers": 1, "opportunity_supplier_links": 1}
    conn.close()
