---
description: Guided one-time setup for Ferrum Nexus (entity config, SAM.gov API key, encrypted store)
---

Run the guided setup flow:

```
uv run python scripts/setup.py
```

This will:
1. Confirm/collect entity details (legal name, DBA, NAICS codes; UEI/CAGE once SAM.gov is active).
2. Prompt for a SAM.gov API key (get one free at sam.gov -> Account Details -> API Key) and
   validate it with one live call before storing it (encrypted, 0600, gitignored).
3. Initialize the encrypted local store (SQLCipher) and load the seed data
   (`seed/opportunities.csv`, `seed/suppliers.csv`, `seed/co_clusters.csv`).

Safe to re-run at any time — it is idempotent (upserts config + seed rows, never duplicates).

If you don't have a SAM.gov API key yet, you can still run this: entity config and the seed
data load without one. The key is only required before Phase 3 (live SAM.gov pulls).

After running, use `/fn-doctor` to confirm everything is healthy.
