---
description: Track Authorized Distributor Letter requests and surface which live opportunities lack one
---

Run:

```
uv run python scripts/adl.py
```

The cross-join Notion can't do: for every active, non-No-bid opportunity linked
to at least one supplier, checks whether any linked supplier has an ADL on
file. Reports opportunities with an ADL gap separately from opportunities that
have no supplier linked at all (a coverage gap, not an ADL gap).

To request/record an ADL programmatically:

```python
from scripts.adl import request_adl, mark_adl_received
request_adl(conn, supplier_notion_url)
mark_adl_received(conn, supplier_notion_url)   # once the OEM's letter arrives
```
