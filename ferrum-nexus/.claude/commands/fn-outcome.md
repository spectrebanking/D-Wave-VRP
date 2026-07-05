---
description: Record a quote's real-world outcome (won/lost/no_response) -- feeds the recursive-learning loop that /fn-score can optionally weigh
---

```python
from scripts.db import connect
from scripts.learning import record_outcome, supplier_scorecard

conn = connect()
record_outcome(conn, quote_key="N0010426QNB47::https://app.notion.com/...", outcome="won",
                notes="optional")

for row in supplier_scorecard(conn):
    print(row)  # {"supplier_key": ..., "reliability": 0.0-1.0, "decided_quotes": n}
```

`outcome` must be one of `pending` / `won` / `lost` / `no_response`. Only `won`/`lost` count
toward a supplier's reliability figure -- `no_response` is excluded from that denominator since
it isn't evidence the supplier under-performed on a bid they actually made.

This is the feedback half of "recursive learning": as real outcomes accumulate,
`scripts/score.py`'s `supplier_track_record` weight (0.0 by default -- there's no closed-deal
history yet) can be raised so `/fn-score` starts favoring suppliers with a proven win rate,
without any code change.
