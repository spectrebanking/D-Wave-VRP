---
description: Show FPDS award/market intelligence and which live opportunities share NAICS codes with already-won contracts
---

Run:

```
uv run python scripts/awards.py
```

Prints the curated market-intelligence notes (lane/agency/vendor patterns
pulled from the FPDS award data), then cross-references every seeded award
against live, current opportunities that share its NAICS code -- a signal
that the government has actually bought in that lane before, not just posted
a solicitation.

Awards are **already-awarded contracts** -- this is competitor/market intel,
not something to bid on directly.

Note: the seeded award set is small (10 rows) by design -- see
`scripts/_seed_awards.py`'s module docstring for why the underlying
~1.1M-row FPDS pull never fully landed in Notion.
