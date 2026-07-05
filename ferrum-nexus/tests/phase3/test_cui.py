import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from db import connect  # noqa: E402
from attachments import ingest_attachments  # noqa: E402
from cui import mark_cui_imported, is_cui_tagged, access_log_for, NotControlledError  # noqa: E402


def _seed_controlled_and_public(conn):
    conn.execute("INSERT INTO opportunities (notion_url, title) VALUES ('opp://c1', 'X')")
    conn.commit()
    resources = [
        {"source_url": "https://x/public.pdf", "resource_id": "pub1", "filename": "public.pdf",
         "mime_type": "application/pdf", "size": 10, "access_level": "public",
         "explicit_access": 0},
        {"source_url": "https://x/drawing.pdf", "resource_id": "ctrl1",
         "filename": "drawing.pdf", "mime_type": "application/pdf", "size": 20,
         "access_level": "private", "explicit_access": 1},
    ]
    ingest_attachments(conn, "opp://c1", "N-C1", "SOL-1", resources, download=lambda u: b"x")


def test_controlled_file_is_tagged_cui_and_access_logged_on_import(tmp_path):
    conn = connect(db_path=tmp_path / "c1.db", key="c1" * 32)
    _seed_controlled_and_public(conn)

    mark_cui_imported(conn, "N-C1::ctrl1", actor="Brocque", local_path="/secure/drawing.pdf")

    tagged = is_cui_tagged(conn, "N-C1::ctrl1")
    log = access_log_for(conn, "N-C1::ctrl1")
    conn.close()

    assert tagged is True
    assert len(log) == 1
    assert log[0]["action"] == "imported"
    assert log[0]["actor"] == "Brocque"


def test_public_file_cannot_be_cui_tagged(tmp_path):
    conn = connect(db_path=tmp_path / "c2.db", key="c2" * 32)
    _seed_controlled_and_public(conn)

    try:
        mark_cui_imported(conn, "N-C1::pub1", actor="Brocque", local_path="/tmp/public.pdf")
        assert False, "expected NotControlledError for a public attachment"
    except NotControlledError:
        pass
    finally:
        conn.close()
