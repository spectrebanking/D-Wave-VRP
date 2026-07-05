"""Live Notion API client -- the Notion analog of sam_client.py. Same design:
pinned endpoint, injectable transport for fixture-based testing, exponential
backoff on 429. No real Notion integration token exists in this build/test
environment (mirrors the SAM.gov posture in DECISIONS.md), so this is
fixture-tested only until a token is on file.

To run this for real: create an internal integration at
notion.so/my-integrations, share the relevant databases with it (Contract
Opportunities, Supplier Matrix, Supplier Outreach Control), then store the
token via credentials.store_notion_token() -- see scripts/notion_sync.py.
"""
import json
import time
import urllib.error
import urllib.request

NOTION_VERSION = "2025-09-03"
DATA_SOURCE_QUERY_ENDPOINT = "https://api.notion.com/v1/data_sources/{data_source_id}/query"

_MAX_RETRIES = 3


class NotionApiError(Exception):
    pass


class RateLimitExceeded(NotionApiError):
    pass


def _default_transport(url: str, token: str, body: dict):
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        payload_bytes = exc.read()
        payload = json.loads(payload_bytes.decode("utf-8")) if payload_bytes else {}
        return exc.code, payload


class NotionClient:
    def __init__(self, token: str, transport=None, sleep=time.sleep):
        self._token = token
        self._transport = transport or (
            lambda url, body: _default_transport(url, self._token, body)
        )
        self._sleep = sleep

    def query_data_source(self, data_source_id: str, start_cursor: str | None = None,
                           page_size: int = 100) -> dict:
        url = DATA_SOURCE_QUERY_ENDPOINT.format(data_source_id=data_source_id)
        body = {"page_size": page_size}
        if start_cursor:
            body["start_cursor"] = start_cursor

        attempt = 0
        while True:
            status, payload = self._transport(url, body)
            if status == 200:
                return payload
            if status == 429:
                attempt += 1
                if attempt > _MAX_RETRIES:
                    raise RateLimitExceeded(
                        f"Notion API rate limit exceeded after {_MAX_RETRIES} retries"
                    )
                self._sleep(2 ** attempt)
                continue
            raise NotionApiError(
                f"Notion API error {status} querying data source {data_source_id}: "
                f"{payload.get('message', payload)}"
            )

    def query_all_pages(self, data_source_id: str, page_size: int = 100):
        """Yields each Notion API page response (the raw {"results": [...], ...}
        payload) until has_more is false."""
        cursor = None
        while True:
            payload = self.query_data_source(data_source_id, start_cursor=cursor,
                                              page_size=page_size)
            yield payload
            if not payload.get("has_more"):
                return
            cursor = payload.get("next_cursor")


def page_url(page: dict) -> str:
    return f"https://app.notion.com/{page['id'].replace('-', '')}"


def flatten_property(prop: dict):
    ptype = prop.get("type")
    if ptype == "title":
        parts = prop.get("title") or []
        text = "".join(p.get("plain_text", "") for p in parts)
        return text or None
    if ptype == "rich_text":
        parts = prop.get("rich_text") or []
        text = "".join(p.get("plain_text", "") for p in parts)
        return text or None
    if ptype in ("select", "status"):
        value = prop.get(ptype)
        return value["name"] if value else None
    if ptype == "multi_select":
        options = prop.get("multi_select") or []
        return ", ".join(o["name"] for o in options) or None
    if ptype == "number":
        return prop.get("number")
    if ptype == "checkbox":
        return bool(prop.get("checkbox"))
    if ptype == "url":
        return prop.get("url")
    if ptype == "email":
        return prop.get("email")
    if ptype == "phone_number":
        return prop.get("phone_number")
    if ptype == "date":
        d = prop.get("date")
        return d.get("start") if d else None
    if ptype == "relation":
        rels = prop.get("relation") or []
        return [page_url({"id": r["id"]}) for r in rels]
    return None


def flatten_page(page: dict) -> dict:
    """A Notion API page -> {"notion_url": ..., <property name>: <flattened value>, ...}."""
    flat = {"notion_url": page_url(page)}
    for name, prop in page.get("properties", {}).items():
        flat[name] = flatten_property(prop)
    return flat
