---
description: Record a supplier's quote for a solicitation (required before /fn-quote will run)
---

```python
from scripts.db import connect
from scripts.quote_add import add_quote

conn = connect()
add_quote(
    conn,
    solicitation_number="N0010426QNB47",
    supplier_key=supplier_notion_url,   # must already exist in the suppliers table
    unit_price=1.25,
    total_price=125.0,
    ptat="30 days ARO",
    fob="Origin",
    cage_code=None,
    coc_on_file=False,
    mtr_on_file=False,
    adl_on_file=False,   # /fn-quote's Readiness Assessment will flag BLOCKED without this
)
```

Idempotent per (solicitation, supplier) pair -- re-running updates the existing quote row.
