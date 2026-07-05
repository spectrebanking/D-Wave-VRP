import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from db import connect  # noqa: E402
from attachments import detect_resources, ingest_attachments, attachment_count_for_notice  # noqa: E402


def test_detect_unions_resource_links_and_resources_endpoint():
    notice = {"resourceLinks": ["https://api.sam.gov/prod/opportunities/v1/resources/abc"]}
    resources_response = {"resources": [
        {"resourceId": "r1", "url": "https://api.sam.gov/prod/opportunities/v1/resources/xyz",
         "fileName": "drawing.pdf", "contentType": "application/pdf",
         "packageAccessLevel": "public", "explicitAccess": False, "sizeInBytes": 1024},
    ]}

    resources = detect_resources(notice, resources_response)

    assert len(resources) == 2  # the bare link + the one from the resources endpoint
    urls = {r["source_url"] for r in resources}
    assert "https://api.sam.gov/prod/opportunities/v1/resources/abc" in urls
    assert "https://api.sam.gov/prod/opportunities/v1/resources/xyz" in urls


def test_public_and_controlled_files_both_recorded_only_public_downloaded(tmp_path):
    conn = connect(db_path=tmp_path / "a1.db", key="a1" * 32)
    conn.execute("INSERT INTO opportunities (notion_url, title) VALUES ('opp://1', 'X')")
    conn.commit()

    resources = [
        {"source_url": "https://x/public.pdf", "resource_id": "pub1", "filename": "public.pdf",
         "mime_type": "application/pdf", "size": 10, "access_level": "public",
         "explicit_access": 0},
        {"source_url": "https://x/drawing_cui.pdf", "resource_id": "ctrl1",
         "filename": "drawing_cui.pdf", "mime_type": "application/pdf", "size": 20,
         "access_level": "private", "explicit_access": 1},
    ]

    def fake_download(url):
        return b"fake pdf bytes"

    recorded = ingest_attachments(
        conn, "opp://1", "N-1", "N0010426QNB47", resources,
        download=fake_download, local_dir=tmp_path / "attach_store",
    )

    rows = {r[0]: r[1:] for r in conn.execute(
        "SELECT resource_id, download_status, access_request_status, sha256, local_path "
        "FROM attachments WHERE notice_id = 'N-1'"
    ).fetchall()}
    conn.close()

    assert len(recorded) == 2
    pub_status, pub_access_req, pub_sha, pub_path = rows["pub1"]
    assert pub_status == "downloaded"
    assert pub_sha is not None
    assert pub_path is not None and Path(pub_path).exists()

    ctrl_status, ctrl_access_req, ctrl_sha, ctrl_path = rows["ctrl1"]
    assert ctrl_status == "access_required"
    assert ctrl_access_req == "none"
    assert ctrl_sha is None
    assert ctrl_path is None  # controlled bytes are never fabricated or force-downloaded


def test_one_failed_download_does_not_stall_the_rest(tmp_path):
    conn = connect(db_path=tmp_path / "a2.db", key="a2" * 32)
    conn.execute("INSERT INTO opportunities (notion_url, title) VALUES ('opp://2', 'X')")
    conn.commit()

    resources = [
        {"source_url": "https://x/good1.pdf", "resource_id": "g1", "filename": "good1.pdf",
         "mime_type": "application/pdf", "size": 5, "access_level": "public",
         "explicit_access": 0},
        {"source_url": "https://x/bad.pdf", "resource_id": "bad1", "filename": "bad.pdf",
         "mime_type": "application/pdf", "size": 5, "access_level": "public",
         "explicit_access": 0},
        {"source_url": "https://x/good2.pdf", "resource_id": "g2", "filename": "good2.pdf",
         "mime_type": "application/pdf", "size": 5, "access_level": "public",
         "explicit_access": 0},
    ]

    def flaky_download(url):
        if "bad" in url:
            raise ConnectionError("simulated network failure")
        return b"ok bytes"

    recorded = ingest_attachments(
        conn, "opp://2", "N-2", None, resources,
        download=flaky_download, local_dir=tmp_path / "attach_store2",
    )

    statuses = {r["resource_id"]: r["download_status"] for r in recorded}
    total_in_db = attachment_count_for_notice(conn, "N-2")
    conn.close()

    assert statuses == {"g1": "downloaded", "bad1": "failed", "g2": "downloaded"}
    assert total_in_db == 3, "no attachment unaccounted -- the failed one is still recorded"


def test_no_attachment_unaccounted_detected_equals_recorded(tmp_path):
    conn = connect(db_path=tmp_path / "a3.db", key="a3" * 32)
    conn.execute("INSERT INTO opportunities (notion_url, title) VALUES ('opp://3', 'X')")
    conn.commit()

    notice = {"resourceLinks": [f"https://x/{i}.pdf" for i in range(4)]}
    resources_response = {"resources": []}
    resources = detect_resources(notice, resources_response)

    ingest_attachments(
        conn, "opp://3", "N-3", None, resources,
        download=lambda url: b"bytes", local_dir=tmp_path / "attach_store3",
    )
    total = attachment_count_for_notice(conn, "N-3")
    conn.close()

    assert total == len(resources) == 4
