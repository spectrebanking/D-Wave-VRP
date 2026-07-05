import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import pytest  # noqa: E402
from notion_client import (  # noqa: E402
    NotionClient, NotionApiError, RateLimitExceeded, flatten_page, flatten_property, page_url,
)


def _page(page_id: str, title: str) -> dict:
    return {
        "object": "page",
        "id": page_id,
        "properties": {
            "Name": {"type": "title", "title": [{"plain_text": title}]},
            "Status": {"type": "status", "status": {"name": "Active"}},
            "Tags": {"type": "multi_select", "multi_select": [{"name": "A"}, {"name": "B"}]},
            "Active": {"type": "checkbox", "checkbox": True},
            "Score": {"type": "number", "number": 4.5},
            "Link": {"type": "relation", "relation": [{"id": "abcd-1234"}]},
        },
    }


def test_paginates_until_has_more_false():
    calls = []

    def fake_transport(url, body):
        calls.append(body.get("start_cursor"))
        if body.get("start_cursor") is None:
            return 200, {"results": [_page("p1", "one")], "has_more": True, "next_cursor": "c2"}
        return 200, {"results": [_page("p2", "two")], "has_more": False, "next_cursor": None}

    client = NotionClient(token="fake", transport=fake_transport)
    pages = list(client.query_all_pages("ds-1"))

    assert len(pages) == 2
    assert calls == [None, "c2"]
    all_ids = [p["id"] for page in pages for p in page["results"]]
    assert all_ids == ["p1", "p2"]


def test_backs_off_on_429_then_succeeds():
    attempts = {"n": 0}
    sleeps = []

    def fake_transport(url, body):
        attempts["n"] += 1
        if attempts["n"] < 3:
            return 429, {"message": "rate limited"}
        return 200, {"results": [], "has_more": False}

    client = NotionClient(token="fake", transport=fake_transport, sleep=lambda s: sleeps.append(s))
    result = client.query_data_source("ds-1")

    assert attempts["n"] == 3
    assert result["results"] == []
    assert sleeps == [2, 4]


def test_gives_up_after_max_retries_on_sustained_429():
    def fake_transport(url, body):
        return 429, {"message": "rate limited"}

    client = NotionClient(token="fake", transport=fake_transport, sleep=lambda s: None)
    with pytest.raises(RateLimitExceeded):
        client.query_data_source("ds-1")


def test_non_200_non_429_raises_notion_api_error():
    def fake_transport(url, body):
        return 500, {"message": "boom"}

    client = NotionClient(token="fake", transport=fake_transport)
    with pytest.raises(NotionApiError):
        client.query_data_source("ds-1")


def test_page_url_strips_dashes():
    assert page_url({"id": "382ed5bb-5bca-8129-bec8-fba292056bdb"}) == (
        "https://app.notion.com/382ed5bb5bca8129bec8fba292056bdb"
    )


def test_flatten_page_covers_common_property_types():
    flat = flatten_page(_page("382ed5bb-5bca-8129-bec8-fba292056bdb", "Test Row"))
    assert flat["notion_url"] == "https://app.notion.com/382ed5bb5bca8129bec8fba292056bdb"
    assert flat["Name"] == "Test Row"
    assert flat["Status"] == "Active"
    assert flat["Tags"] == "A, B"
    assert flat["Active"] is True
    assert flat["Score"] == 4.5
    assert flat["Link"] == ["https://app.notion.com/abcd1234"]


def test_flatten_property_returns_none_for_empty_title():
    assert flatten_property({"type": "title", "title": []}) is None


def test_flatten_property_returns_none_for_unset_select():
    assert flatten_property({"type": "select", "select": None}) is None
