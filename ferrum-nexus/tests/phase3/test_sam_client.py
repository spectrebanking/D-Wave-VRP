"""Recorded-fixture tests for the SAM client -- no live network call, no real
API key required. Exercises pagination, window validation, and 429 backoff."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import pytest  # noqa: E402
from sam_client import SamClient, RateLimitExceeded, SamApiError, _redact_api_key  # noqa: E402


def _page(n_results: int, offset: int) -> dict:
    return {
        "totalRecords": 1250,
        "opportunitiesData": [
            {"noticeId": f"NOTICE-{offset + i}", "title": f"Item {offset + i}"}
            for i in range(n_results)
        ],
    }


def test_paginates_until_short_page(monkeypatch):
    calls = []

    def fake_transport(url):
        calls.append(url)
        offset = int(url.split("offset=")[1].split("&")[0])
        # first two pages full (limit=2), third page short -> stop
        if offset == 0:
            return 200, _page(2, 0)
        if offset == 2:
            return 200, _page(2, 2)
        return 200, _page(1, 4)

    client = SamClient(api_key="fake", transport=fake_transport)
    pages = list(client.search_all_pages("01/01/2026", "06/01/2026", limit=2))

    assert len(pages) == 3
    assert len(calls) == 3
    all_ids = [r["noticeId"] for p in pages for r in p["opportunitiesData"]]
    assert all_ids == [f"NOTICE-{i}" for i in range(5)]


def test_respects_window_max_one_year():
    client = SamClient(api_key="fake", transport=lambda url: (200, {"opportunitiesData": []}))
    with pytest.raises(ValueError, match="366-day max"):
        client.search_opportunities("01/01/2025", "01/01/2027")


def test_rejects_malformed_dates():
    client = SamClient(api_key="fake", transport=lambda url: (200, {}))
    with pytest.raises(ValueError, match="MM/dd/yyyy"):
        client.search_opportunities("2026-01-01", "2026-02-01")


def test_backs_off_on_429_then_succeeds(monkeypatch):
    attempts = {"n": 0}
    sleeps = []

    def fake_transport(url):
        attempts["n"] += 1
        if attempts["n"] < 3:
            return 429, {"error": "rate limited"}
        return 200, _page(1, 0)

    client = SamClient(
        api_key="fake", transport=fake_transport, sleep=lambda s: sleeps.append(s)
    )
    result = client.search_opportunities("01/01/2026", "02/01/2026")

    assert attempts["n"] == 3
    assert result["opportunitiesData"][0]["noticeId"] == "NOTICE-0"
    assert sleeps == [2, 4]  # exponential backoff, 2 retries before success


def test_gives_up_after_max_retries_on_sustained_429():
    def fake_transport(url):
        return 429, {"error": "rate limited"}

    client = SamClient(api_key="fake", transport=fake_transport, sleep=lambda s: None)
    with pytest.raises(RateLimitExceeded):
        client.search_opportunities("01/01/2026", "02/01/2026")


def test_redact_api_key_strips_value_but_keeps_url_shape():
    url = "https://api.sam.gov/opportunities/v2/search?api_key=SUPERSECRET123&limit=1"
    redacted = _redact_api_key(url)
    assert "SUPERSECRET123" not in redacted
    assert "api_key=***" in redacted
    assert "limit=1" in redacted


def test_error_messages_never_contain_the_live_api_key():
    """Security regression: exception text must not leak api_key, since
    RUNBOOK.md tells the operator to paste errors into a chat assistant."""
    def fake_transport(url):
        return 500, {"error": "boom"}

    client = SamClient(api_key="LIVE-SECRET-KEY", transport=fake_transport)
    with pytest.raises(SamApiError) as exc_info:
        client.search_opportunities("01/01/2026", "02/01/2026")
    assert "LIVE-SECRET-KEY" not in str(exc_info.value)


def test_rate_limit_error_never_contains_the_live_api_key():
    def fake_transport(url):
        return 429, {"error": "rate limited"}

    client = SamClient(api_key="LIVE-SECRET-KEY", transport=fake_transport, sleep=lambda s: None)
    with pytest.raises(RateLimitExceeded) as exc_info:
        client.search_opportunities("01/01/2026", "02/01/2026")
    assert "LIVE-SECRET-KEY" not in str(exc_info.value)


def test_notice_description_uses_pinned_endpoint():
    seen_urls = []

    def fake_transport(url):
        seen_urls.append(url)
        return 200, {"description": "text"}

    client = SamClient(api_key="fake", transport=fake_transport)
    client.get_notice_description("NOTICE-123")

    assert seen_urls[0].startswith(
        "https://api.sam.gov/opportunities/v1/noticedesc/NOTICE-123"
    )
