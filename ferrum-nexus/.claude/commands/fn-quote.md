---
description: Assemble a quote sheet + cover email + attachment checklist + Readiness Assessment for a solicitation
---

Blocked until a supplier quote is on file (`/fn-quote-add` first) and specs are attested
(`/fn-specs` first). Draft only -- there is no send path anywhere in this package.

```python
from scripts.db import connect
from scripts.quote_add import add_quote
from scripts.quote_render import build_quote_package, render_full_package, QuoteBlocked

conn = connect()
add_quote(conn, "N0010426QNB47", supplier_notion_url,
          unit_price=1.25, total_price=125.0, ptat="30 days ARO", fob="Origin",
          adl_on_file=True)  # [2.2a] /fn-quote-add -- must run before /fn-quote

try:
    package = build_quote_package(conn, "N0010426QNB47")
except QuoteBlocked as exc:
    print(exc)  # no quote on file yet
else:
    print(render_full_package(package))
```

The Readiness Assessment embedded in the package is **never** a "READY" verdict -- see
`/fn-status`'s sibling doc and `rules/readiness_rules_v0.yaml` (ships `UNVERIFIED`, awaiting
GovCon SME sign-off).
