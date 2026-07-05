---
description: Re-pull live Notion + SAM.gov data into the local store -- the recurring half of recursive learning
---

Run:

```
uv run python scripts/fn_sync.py
```

Refreshes from every live source that has credentials on file:

- **Notion** (opportunities, suppliers, supplier links) via `scripts/notion_sync.py` --
  needs a Notion integration token (`credentials.store_notion_token()`, or supply one at
  `/fn-setup`).
- **SAM.gov** (opportunities over a rolling 30-day posted-date window) via `scripts/pull.py` --
  needs a real SAM.gov API key.

Either credential missing just skips that source with a clear message -- it never blocks the
other. Every upsert underneath is idempotent, so this is safe to run on a schedule. To run it
automatically, add a cron entry (adjust the path):

```
0 6 * * * cd /path/to/ferrum-nexus && .venv/bin/python scripts/fn_sync.py >> data/sync.log 2>&1
```
