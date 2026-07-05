"""3.3 -- Attachment ingestion pipeline (plan section 7A).

detect -> classify -> download (public) / route to access_required
(controlled) -> link + stamp to the opportunity. Every detected attachment
gets a row in `attachments`, no matter what happens next -- "100% attachment
accountability": tracked always, retrieved only when public. A failed
download on one file must not stop the others (per-file try/except).

detect_resources() unions notice['resourceLinks'] (plain URLs, no metadata)
with the resources-endpoint response (full metadata: resourceId, fileName,
contentType, packageAccessLevel, explicitAccess) per plan 7A's
"don't trust one source" rule. Dedup key: resourceId when the resources
endpoint provides one, else the source URL itself -- see DECISIONS.md for why
URL-based dedup is the practical fallback without a live API to verify SAM's
actual resourceLinks/resources overlap shape against.
"""
import hashlib
import tempfile
from datetime import datetime, timezone
from pathlib import Path


def detect_resources(notice: dict, resources_response: dict) -> list[dict]:
    merged: dict[str, dict] = {}

    for url in notice.get("resourceLinks", []) or []:
        merged[url] = {
            "source_url": url, "resource_id": None, "filename": None,
            "mime_type": None, "size": None, "access_level": "public",
            "explicit_access": 0,
        }

    for r in resources_response.get("resources", []) or []:
        key = r.get("resourceId") or r.get("url")
        is_private = r.get("packageAccessLevel") == "private"
        merged[key] = {
            "source_url": r.get("url"),
            "resource_id": r.get("resourceId"),
            "filename": r.get("fileName"),
            "mime_type": r.get("contentType"),
            "size": r.get("sizeInBytes"),
            "access_level": "private" if is_private else "public",
            "explicit_access": 1 if r.get("explicitAccess") else 0,
        }

    return list(merged.values())


def _default_download(url: str) -> bytes:
    import urllib.request
    with urllib.request.urlopen(url, timeout=30) as resp:  # pragma: no cover -- real network
        return resp.read()


def ingest_attachments(
    conn,
    opportunity_id: str,
    notice_id: str,
    solicitation_number: str | None,
    resources: list[dict],
    download=None,
    local_dir: Path | None = None,
) -> list[dict]:
    download = download or _default_download
    local_dir = local_dir or Path(tempfile.gettempdir()) / "ferrum_nexus_attachments"
    local_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()

    recorded = []
    for i, res in enumerate(resources):
        attachment_key = f"{notice_id}::{res.get('resource_id') or i}"
        is_controlled = res["access_level"] == "private" or res["explicit_access"] == 1

        row = {
            "attachment_key": attachment_key,
            "opportunity_id": opportunity_id,
            "notice_id": notice_id,
            "solicitation_number": solicitation_number,
            "filename": res.get("filename"),
            "resource_id": res.get("resource_id"),
            "mime_type": res.get("mime_type"),
            "size": res.get("size"),
            "sha256": None,
            "source_url": res.get("source_url"),
            "access_level": res["access_level"],
            "explicit_access": res["explicit_access"],
            "retrieved_via": None,
            "download_status": None,
            "access_request_status": None,
            "local_path": None,
            "pulled_at": now,
        }

        if is_controlled:
            row["download_status"] = "access_required"
            row["access_request_status"] = "none"
            row["retrieved_via"] = "manual"
        else:
            try:
                data = download(res["source_url"])
                local_path = local_dir / f"{attachment_key.replace('/', '_')}"
                local_path.write_bytes(data)
                row["local_path"] = str(local_path)
                row["sha256"] = hashlib.sha256(data).hexdigest()
                row["download_status"] = "downloaded"
                row["retrieved_via"] = "auto"
            except Exception as exc:  # noqa: BLE001 -- one bad file must not stall the rest
                row["download_status"] = "failed"
                row["retrieved_via"] = "auto"
                row["parse_status"] = f"download_error: {exc}"

        conn.execute(
            """INSERT INTO attachments
               (attachment_key, opportunity_id, notice_id, solicitation_number, filename,
                resource_id, mime_type, size, sha256, source_url, access_level,
                explicit_access, retrieved_via, download_status, access_request_status,
                local_path, pulled_at, parse_status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(attachment_key) DO UPDATE SET
                 download_status=excluded.download_status,
                 access_request_status=excluded.access_request_status,
                 local_path=excluded.local_path, sha256=excluded.sha256,
                 pulled_at=excluded.pulled_at""",
            (
                row["attachment_key"], row["opportunity_id"], row["notice_id"],
                row["solicitation_number"], row["filename"], row["resource_id"],
                row["mime_type"], row["size"], row["sha256"], row["source_url"],
                row["access_level"], row["explicit_access"], row["retrieved_via"],
                row["download_status"], row["access_request_status"], row["local_path"],
                row["pulled_at"], row.get("parse_status"),
            ),
        )
        recorded.append(row)

    conn.commit()
    return recorded


def attachment_count_for_notice(conn, notice_id: str) -> int:
    return conn.execute(
        "SELECT COUNT(*) FROM attachments WHERE notice_id = ?", (notice_id,)
    ).fetchone()[0]
