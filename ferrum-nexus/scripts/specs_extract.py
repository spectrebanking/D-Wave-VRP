"""2.1 -- /fn-specs: manual-drop-in spec extraction (text PDFs only).

Per the packet's consensus fix #4, Phase 2 tests the MANUAL path only: a
human downloads/obtains a solicitation PDF (drawing, IRPOD, spec sheet) and
drops it in; this reads it if it's a text PDF and suggests fields with a
source-page citation + confidence. Scanned/image-only PDFs get
'needs_manual_entry' -- OCR is explicitly out of the critical path (plan
section 8). Once Phase 3 lands, auto-ingested attachments feed the same
extractor; this module doesn't care which path handed it a PDF.

Nothing here is usable in a quote until scripts/attest.py marks it attested.
"""
import re
from pathlib import Path

import pdfplumber

# Field patterns, roughly in the NAVSUP RFQ protocol's Phase-1 extraction list.
FIELD_PATTERNS = {
    "nsn": re.compile(r"\bNSN[:\s]+([0-9]{4}-[0-9]{2}-[0-9]{3}-[0-9]{4})\b", re.IGNORECASE),
    "cage": re.compile(r"\bCAGE(?:\s*(?:CODE|CD))?[:\s]+([A-Z0-9]{5})\b", re.IGNORECASE),
    "part_number": re.compile(r"\b(?:P/N|PART\s*NO\.?|PART\s*NUMBER)[:\s]+([A-Z0-9\-]{4,})\b",
                               re.IGNORECASE),
    "quantity": re.compile(r"\bQTY(?:\.|:)?\s*([0-9]+)\b", re.IGNORECASE),
    "material": re.compile(r"\bMATERIAL[:\s]+([A-Za-z0-9 \-/]{3,40})", re.IGNORECASE),
}


def extract_fields_from_text(text: str, page_number: int) -> list[dict]:
    found = []
    for field, pattern in FIELD_PATTERNS.items():
        m = pattern.search(text)
        if m:
            found.append({
                "field": field,
                "value": m.group(1).strip(),
                "page": page_number,
                "confidence": "high",
                "attested": False,
            })
    return found


def extract_from_pdf(pdf_path: str | Path) -> dict:
    """Returns {'status': 'extracted', 'fields': [...]} or
    {'status': 'needs_manual_entry', 'reason': ...} for scanned/unreadable PDFs.
    """
    pdf_path = Path(pdf_path)
    fields: list[dict] = []
    any_text = False

    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            if text.strip():
                any_text = True
                fields.extend(extract_fields_from_text(text, i))

    if not any_text:
        return {
            "status": "needs_manual_entry",
            "reason": "no extractable text layer (scanned/image-only PDF); "
                      "OCR is optional/assistive only, not on the critical path",
            "fields": [],
        }

    return {"status": "extracted", "fields": fields}
