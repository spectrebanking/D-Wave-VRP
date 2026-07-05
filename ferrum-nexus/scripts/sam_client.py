"""3.1 -- SAM.gov API client.

No live SAM.gov API key exists in this build/test environment (this session
has no credential of its own, and there's no interactive human to supply
one -- see DECISIONS.md). Every test in tests/phase3 exercises this client
against an injectable `transport` callable with recorded fixture responses,
per the packet's own guidance ("gate on a controlled date-window query OR
recorded fixtures, not 'must pull >=1 page' from a possibly-empty live
window"). The real live pull is a manual step for Brocque to run once he has
a key and SAM is active.

Endpoint pinning [consensus fix #8] -- pinned against the live GSA swagger as
of 2026-07, not generic labels. If SAM.gov changes these, update the
constants here and the pinning test fails loudly instead of silently drifting.
"""
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

_API_KEY_RE = re.compile(r"([?&]api_key=)[^&]*")


def _redact_api_key(url: str) -> str:
    """Strip the live api_key value out of a URL before it goes anywhere
    that might get logged, printed, or pasted into a support/chat channel."""
    return _API_KEY_RE.sub(r"\1***", url)

SEARCH_ENDPOINT = "https://api.sam.gov/opportunities/v2/search"
NOTICE_DESC_ENDPOINT = "https://api.sam.gov/opportunities/v1/noticedesc/{notice_id}"
RESOURCES_ENDPOINT = "https://api.sam.gov/opportunities/v2/notices/{notice_id}/resources"

MAX_WINDOW_DAYS = 366
DEFAULT_LIMIT = 1000
MAX_RETRIES_ON_429 = 3


class SamApiError(Exception):
    pass


class RateLimitExceeded(SamApiError):
    pass


def _default_transport(url: str) -> tuple[int, dict]:
    """Real HTTP GET, used outside tests. Returns (status_code, json_body)."""
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError:
            parsed = {"error": body}
        return exc.code, parsed


def _validate_window(posted_from: str, posted_to: str) -> None:
    fmt = "%m/%d/%Y"
    try:
        start = datetime.strptime(posted_from, fmt)
        end = datetime.strptime(posted_to, fmt)
    except ValueError as exc:
        raise ValueError(f"postedFrom/postedTo must be MM/dd/yyyy: {exc}") from exc
    if end < start:
        raise ValueError("postedTo must not be before postedFrom")
    if (end - start).days > MAX_WINDOW_DAYS:
        raise ValueError(
            f"window of {(end - start).days} days exceeds SAM's {MAX_WINDOW_DAYS}-day max"
        )


class SamClient:
    def __init__(self, api_key: str, transport=None, sleep=time.sleep):
        self.api_key = api_key
        self._transport = transport or _default_transport
        self._sleep = sleep

    def _get(self, url: str) -> dict:
        attempt = 0
        while True:
            status, body = self._transport(url)
            if status == 429:
                attempt += 1
                if attempt > MAX_RETRIES_ON_429:
                    raise RateLimitExceeded(
                        f"429 after {attempt - 1} retries: {_redact_api_key(url)}"
                    )
                self._sleep(2 ** attempt)  # exponential backoff
                continue
            if status != 200:
                raise SamApiError(f"SAM API returned {status} for {_redact_api_key(url)}: {body}")
            return body

    def search_opportunities(
        self, posted_from: str, posted_to: str, limit: int = DEFAULT_LIMIT, offset: int = 0,
    ) -> dict:
        _validate_window(posted_from, posted_to)
        params = urllib.parse.urlencode({
            "api_key": self.api_key,
            "postedFrom": posted_from,
            "postedTo": posted_to,
            "limit": limit,
            "offset": offset,
        })
        return self._get(f"{SEARCH_ENDPOINT}?{params}")

    def search_all_pages(self, posted_from: str, posted_to: str, limit: int = DEFAULT_LIMIT):
        """Generator yielding one page (dict) at a time until exhausted."""
        offset = 0
        while True:
            page = self.search_opportunities(posted_from, posted_to, limit=limit, offset=offset)
            results = page.get("opportunitiesData", [])
            yield page
            if len(results) < limit:
                return
            offset += limit

    def get_notice_description(self, notice_id: str) -> dict:
        params = urllib.parse.urlencode({"api_key": self.api_key})
        url = NOTICE_DESC_ENDPOINT.format(notice_id=notice_id) + f"?{params}"
        return self._get(url)

    def get_resources(self, notice_id: str) -> dict:
        params = urllib.parse.urlencode({"api_key": self.api_key})
        url = RESOURCES_ENDPOINT.format(notice_id=notice_id) + f"?{params}"
        return self._get(url)
