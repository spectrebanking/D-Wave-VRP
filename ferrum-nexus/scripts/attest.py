"""2.1 -- per-field human attestation. No extracted field is usable in a quote
until a human has attested to it. Batch-attest is only allowed after the
low-confidence fields have been surfaced to the human (attest_all takes an
explicit `shown_low_confidence` flag so callers can't skip that step)."""


def is_fully_attested(extraction: dict) -> bool:
    return extraction["status"] == "extracted" and all(
        f["attested"] for f in extraction["fields"]
    )


def attest_field(extraction: dict, field_name: str, value: str | None = None) -> dict:
    """Attest a single field, optionally overriding its value (human correction)."""
    for f in extraction["fields"]:
        if f["field"] == field_name:
            f["attested"] = True
            if value is not None:
                f["value"] = value
                f["confidence"] = "human-corrected"
            return extraction
    raise KeyError(f"no such field: {field_name}")


def attest_all(extraction: dict, shown_low_confidence: bool = False) -> dict:
    """Batch-attest every field. Requires shown_low_confidence=True as proof the
    low-confidence fields were displayed to the human first (packet 2.1: 'batch
    attest only after low-confidence fields shown')."""
    low_conf = [f for f in extraction["fields"] if f["confidence"] != "high"]
    if low_conf and not shown_low_confidence:
        raise ValueError(
            f"{len(low_conf)} low-confidence field(s) must be shown to the human "
            "before batch-attesting; pass shown_low_confidence=True once displayed"
        )
    for f in extraction["fields"]:
        f["attested"] = True
    return extraction


def get_quote_ready_fields(extraction: dict) -> list[dict]:
    """Only attested fields are usable downstream (/fn-quote)."""
    if extraction["status"] != "extracted":
        return []
    return [f for f in extraction["fields"] if f["attested"]]
