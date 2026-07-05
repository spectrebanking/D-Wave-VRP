"""Persist /fn-specs extraction output (post-attestation) keyed by solicitation
number, so /fn-quote -- a separate command invocation -- can read it back."""


def save_extraction(conn, solicitation_number: str, extraction: dict) -> int:
    if extraction["status"] != "extracted":
        return 0
    n = 0
    for f in extraction["fields"]:
        conn.execute(
            """INSERT INTO attested_specs
               (solicitation_number, field, value, page, confidence, attested)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(solicitation_number, field) DO UPDATE SET
                 value=excluded.value, page=excluded.page,
                 confidence=excluded.confidence, attested=excluded.attested""",
            (solicitation_number, f["field"], f["value"], f["page"], f["confidence"],
             1 if f["attested"] else 0),
        )
        n += 1
    conn.commit()
    return n


def load_extraction(conn, solicitation_number: str) -> dict:
    rows = conn.execute(
        "SELECT field, value, page, confidence, attested FROM attested_specs "
        "WHERE solicitation_number = ?",
        (solicitation_number,),
    ).fetchall()
    if not rows:
        return {"status": "not_found", "fields": []}
    fields = [
        {"field": r[0], "value": r[1], "page": r[2], "confidence": r[3], "attested": bool(r[4])}
        for r in rows
    ]
    return {"status": "extracted", "fields": fields}
