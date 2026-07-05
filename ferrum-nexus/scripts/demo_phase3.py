"""Phase 3 gate acceptance command.

Per consensus fix #10 ("avoid flakiness -- gate on a controlled date-window
query OR recorded fixtures, not 'must pull >=1 page' from a possibly-empty
live window"), and because this environment has no real SAM.gov API key
(see DECISIONS.md), this gate runs against a recorded fixture page rather
than a live call. It still asserts every invariant the live gate would:
dedup by noticeId, amendment supersession, 0 unhandled 429s, and 100%
attachment accountability (every detected attachment recorded; public
downloaded; controlled recorded access_required, never dropped).

Brocque: once SAM.gov is active and you have a real API key, run
`SamClient(api_key=...).search_all_pages(...)` for the true live pull --
this script proves the ingestion logic is correct against known input, not
that the live API is reachable today.
"""
import sys

from db import connect
from setup import run_noninteractive_for_tests
from sam_client import SamClient
from pull import pull_page, current_opportunity_count
from attachments import detect_resources, ingest_attachments, attachment_count_for_notice

FIXTURE_PAGE_V1 = {
    "opportunitiesData": [
        {"noticeId": "DEMO-N-1", "title": "DEMO-SOL-0001 -- WIDGET ASSEMBLY",
         "updatedDate": "2026-07-01", "active": True},
        {"noticeId": "DEMO-N-2", "title": "DEMO-SOL-0002 -- BRACKET",
         "updatedDate": "2026-07-01", "active": True},
    ]
}
FIXTURE_PAGE_AMENDED = {
    "opportunitiesData": [
        {"noticeId": "DEMO-N-1", "title": "DEMO-SOL-0001 -- WIDGET ASSEMBLY (AMENDMENT 1)",
         "updatedDate": "2026-07-03", "active": True},
    ]
}
FIXTURE_NOTICE = {"resourceLinks": ["https://api.sam.gov/prod/resources/demo-public-1"]}
FIXTURE_RESOURCES = {"resources": [
    {"resourceId": "demo-r2", "url": "https://api.sam.gov/prod/resources/demo-r2",
     "fileName": "spec.pdf", "contentType": "application/pdf",
     "packageAccessLevel": "public", "explicitAccess": False, "sizeInBytes": 100},
    {"resourceId": "demo-r3", "url": "https://api.sam.gov/prod/resources/demo-r3",
     "fileName": "drawing_cui.pdf", "contentType": "application/pdf",
     "packageAccessLevel": "private", "explicitAccess": True, "sizeInBytes": 500},
]}


def _fixture_transport(url: str):
    """Records 429 -> retry -> 200 to prove the client's backoff path fires
    even in this fixture-based gate."""
    if "429demo" not in _fixture_transport.seen:
        _fixture_transport.seen.add("429demo")
        return 429, {"error": "rate limited"}
    return 200, FIXTURE_PAGE_V1


_fixture_transport.seen = set()


def run() -> None:
    run_noninteractive_for_tests()
    conn = connect()

    # -- 3.1: client backs off on 429 without raising, then succeeds --
    client = SamClient(api_key="demo", transport=_fixture_transport, sleep=lambda s: None)
    page = client.search_opportunities("01/01/2026", "07/01/2026")
    assert page == FIXTURE_PAGE_V1, "gate failed: client did not recover after 429 backoff"
    print("[1/5] SAM client survived a 429 via backoff, 0 unhandled rate-limit errors")

    # -- 3.2: pull dedups by noticeId and handles amendment churn --
    counts_v1 = pull_page(conn, FIXTURE_PAGE_V1)
    counts_v1_again = pull_page(conn, FIXTURE_PAGE_V1)
    counts_amended = pull_page(conn, FIXTURE_PAGE_AMENDED)
    assert counts_v1 == {"inserted": 2, "unchanged": 0, "superseded": 0}
    assert counts_v1_again == {"inserted": 0, "unchanged": 2, "superseded": 0}, (
        "gate failed: re-pulling the same page duplicated rows"
    )
    assert counts_amended == {"inserted": 0, "unchanged": 0, "superseded": 1}, (
        "gate failed: amendment churn did not supersede the old row"
    )
    current_row = conn.execute(
        "SELECT notion_url FROM opportunities WHERE notice_id='DEMO-N-1' "
        "AND superseded_by IS NULL"
    ).fetchall()
    assert len(current_row) == 1, "gate failed: more than one current row survives an amendment"
    print(f"[2/5] pull dedups by noticeId + amendment churn correct "
          f"({current_opportunity_count(conn)} current opportunities on file)")

    # -- 3.3: attachment ingestion -- 100% accountability --
    resources = detect_resources(FIXTURE_NOTICE, FIXTURE_RESOURCES)
    assert len(resources) == 3, "gate failed: detect_resources did not union+dedup correctly"

    def fixture_download(url: str) -> bytes:
        return f"fixture bytes for {url}".encode()

    recorded = ingest_attachments(
        conn, current_row[0][0], "DEMO-N-1", "DEMO-SOL-0001", resources,
        download=fixture_download,
    )
    detected_count = len(resources)
    recorded_count = attachment_count_for_notice(conn, "DEMO-N-1")
    assert detected_count == recorded_count == len(recorded), (
        "gate failed: attachment accountability broken -- "
        f"detected={detected_count} recorded={recorded_count}"
    )
    statuses = {r["resource_id"]: r["download_status"] for r in recorded}
    assert statuses["demo-r2"] == "downloaded", "gate failed: public file was not downloaded"
    assert statuses["demo-r3"] == "access_required", (
        "gate failed: controlled file was not routed to access_required"
    )
    print(f"[3/5] attachment ingestion: {detected_count} detected == {recorded_count} recorded, "
          f"public downloaded, controlled routed to access_required (never dropped)")

    # -- 3.5: sole-source auto no-bid still holds on freshly-pulled rows --
    from score import score_opportunity
    result = score_opportunity(conn, current_row[0][0], ["332722"])
    assert result["no_bid"] is False  # DEMO-SOL-0001 isn't sole-source
    print(f"[4/5] /fn-score ran on the freshly-pulled row: {result}")

    print("[5/5] all Phase 3 invariants held against recorded fixtures")
    conn.close()
    print("\nPHASE 3 GATE: PASS (fixture-based -- run a real /fn-pull once SAM is "
          "active + a real API key is on file for a true live-pull check)")


def main() -> int:
    try:
        run()
    except AssertionError as exc:
        print(f"\nPHASE 3 GATE: FAIL -- {exc}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
