---
description: List every tracked blocker with owner, next action, and follow-up cadence
---

Run:

```
uv run python scripts/blockers.py
```

Seeds (idempotently) and prints the blocker chain in critical-path order: SAM
activation -> API role tier / JCP-DD2345 / distributor onboarding -> ADL
acquisition -> past-performance/PPQ. Each blocker always has an owner, a next
action, and a follow-up cadence -- this tool tracks and reminds, it does not
close blockers for you.
