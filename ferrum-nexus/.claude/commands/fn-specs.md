---
description: Extract NSN/CAGE/P-N/material/qty from a manually-obtained solicitation PDF, cited + confidence-scored, pending attestation
---

Manual-drop-in mode only (Phase 3 auto-ingestion lands later and feeds this same extractor).

```python
from scripts.specs_extract import extract_from_pdf
from scripts.attest import attest_field, attest_all, is_fully_attested
from scripts.specs_store import save_extraction

result = extract_from_pdf("/path/to/solicitation.pdf")
# result["status"] == "needs_manual_entry" for scanned/image-only PDFs -- OCR
# is optional/assistive only, never on the critical path.

# Every field must be attested by a human before it's usable in a quote.
# attest_all() refuses to batch-attest low-confidence fields until they've
# been shown (pass shown_low_confidence=True once you've displayed them).
attest_all(result)
assert is_fully_attested(result)

save_extraction(conn, "N0010426QNB47", result)  # persist for /fn-quote to read
```
