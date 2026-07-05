---
description: Transparent weighted ranking of current opportunities (weights are yours to tweak)
---

```python
from scripts.db import connect
from scripts.score import score_all

conn = connect()
ranked = score_all(conn, entity_naics_codes=["332722", "423510", "332919"])
for r in ranked[:20]:
    print(r)
```

Sole-source opportunities are auto no-bid regardless of score. Weights (`lane_coverage`,
`naics_match`) are plain numbers you can pass in -- no hidden logic. Known gap: the seed data
doesn't currently carry a response-deadline or set-aside field, so those aren't scored yet
(see DECISIONS.md) -- add them to the seed export and this module picks them up without
changing shape.
