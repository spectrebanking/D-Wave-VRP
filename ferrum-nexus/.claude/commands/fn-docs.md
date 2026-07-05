---
description: Generate the 5 standing documents (capabilities statement, letterhead, quote/cover-email templates, W-9 checklist)
---

Requires `/fn-setup` to have run first (needs `data/config.json`).

Run:

```
uv run python scripts/docs.py
```

Writes to `data/generated_docs/`:
- `capabilities-statement.md`
- `letterhead.md`
- `quote-template.md` (NAVSUP fields pre-filled from entity config)
- `cover-email-template.md`
- `w9-checklist.md` -- **not a real W-9.** A real W-9 is a signed IRS tax form;
  this tool cannot legally fabricate one. This file lists exactly which fields
  to drop into the actual IRS W-9 PDF.
