---
description: Health check for the Ferrum Nexus local store (reachability, schema, seed counts, keys)
---

Run:

```
uv run python scripts/doctor.py
```

Reports:
- Whether the encrypted store is reachable (right key, schema intact).
- Whether all 9 schema-v1 tables exist.
- Row counts for `opportunities`, `suppliers`, `co_clusters`.
- Whether the DB encryption key and a SAM.gov API key are on file.
- An overall `green: True/False` verdict — exits 0 when green, 1 otherwise.

If it isn't green, the most common fix is `/fn-setup` (creates the key + seeds the store).
