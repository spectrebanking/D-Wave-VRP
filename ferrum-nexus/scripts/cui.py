"""3.4 -- CUI handling for manually-imported controlled attachments.

Controlled NAVSUP/DLA drawings (explicit_access=1 / access_level=private)
are typically CUI once obtained -- DFARS 252.204-7012 obligations attach.
This tags the attachment as CUI, logs who imported it and when (the access
trail plan section 7A calls for), and gives the "block accidental share"
check a place to hook into before anything gets emailed/exported.
"""
from datetime import datetime, timezone


class NotControlledError(Exception):
    """Raised if something tries to CUI-tag a public attachment -- only
    controlled/explicit-access files carry CUI obligations."""


def mark_cui_imported(conn, attachment_key: str, actor: str, local_path: str) -> None:
    row = conn.execute(
        "SELECT access_level, explicit_access FROM attachments WHERE attachment_key = ?",
        (attachment_key,),
    ).fetchone()
    if row is None:
        raise ValueError(f"unknown attachment_key: {attachment_key}")
    access_level, explicit_access = row
    if access_level != "private" and not explicit_access:
        raise NotControlledError(
            f"{attachment_key} is not a controlled attachment -- refusing to CUI-tag a "
            "public file"
        )

    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """UPDATE attachments
           SET local_path = ?, download_status = 'downloaded',
               access_request_status = 'imported', parse_status = 'CUI'
           WHERE attachment_key = ?""",
        (local_path, attachment_key),
    )
    conn.execute(
        """INSERT INTO cui_access_log (log_key, attachment_key, action, actor, at, note)
           VALUES (?, ?, 'imported', ?, ?, ?)""",
        (f"{attachment_key}::{now}", attachment_key, actor, now,
         "manually imported controlled file, tagged CUI"),
    )
    conn.commit()


def log_access(conn, attachment_key: str, actor: str, action: str, note: str | None = None) -> None:
    """Append-only access log entry -- call this on every open/export/share
    attempt of a CUI-tagged file, not just the initial import."""
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """INSERT INTO cui_access_log (log_key, attachment_key, action, actor, at, note)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (f"{attachment_key}::{now}", attachment_key, action, actor, now, note),
    )
    conn.commit()


def is_cui_tagged(conn, attachment_key: str) -> bool:
    row = conn.execute(
        "SELECT parse_status FROM attachments WHERE attachment_key = ?", (attachment_key,)
    ).fetchone()
    return row is not None and row[0] == "CUI"


def access_log_for(conn, attachment_key: str) -> list[dict]:
    rows = conn.execute(
        "SELECT action, actor, at, note FROM cui_access_log WHERE attachment_key = ? "
        "ORDER BY at",
        (attachment_key,),
    ).fetchall()
    return [{"action": a, "actor": b, "at": c, "note": d} for a, b, c, d in rows]
