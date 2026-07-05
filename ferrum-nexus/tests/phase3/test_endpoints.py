"""[3.1 consensus fix #8] Endpoint pinning is a real deliverable -- this test
fails on drift, not on prose. If SAM.gov changes a path, this breaks loudly
instead of the client silently hitting a dead/wrong URL."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import sam_client  # noqa: E402


def test_search_endpoint_pinned():
    assert sam_client.SEARCH_ENDPOINT == "https://api.sam.gov/opportunities/v2/search"


def test_notice_desc_endpoint_pinned():
    assert sam_client.NOTICE_DESC_ENDPOINT == (
        "https://api.sam.gov/opportunities/v1/noticedesc/{notice_id}"
    )
    assert sam_client.NOTICE_DESC_ENDPOINT.format(notice_id="ABC123") == (
        "https://api.sam.gov/opportunities/v1/noticedesc/ABC123"
    )


def test_resources_endpoint_pinned():
    assert sam_client.RESOURCES_ENDPOINT == (
        "https://api.sam.gov/opportunities/v2/notices/{notice_id}/resources"
    )
    assert sam_client.RESOURCES_ENDPOINT.format(notice_id="ABC123") == (
        "https://api.sam.gov/opportunities/v2/notices/ABC123/resources"
    )
