# Ferrum Nexus -- one-page runbook

## Install (once, or on a new machine)

```
cd ferrum-nexus
uv venv .venv
uv pip install --python .venv/bin/python -e ".[dev]"
```

## First run

```
.venv/bin/python scripts/setup.py
```

Prompts for your entity name and SAM.gov API key (skip the key if SAM.gov isn't active yet --
everything except live `/fn-pull` works without it). Seeds the encrypted local store from
`seed/*.csv`. Safe to re-run any time.

Then confirm everything's healthy:

```
.venv/bin/python scripts/doctor.py
```

Should print `green: True` and exit 0. If not, it tells you exactly what's missing.

## Daily commands

| Command | What it does |
|---|---|
| `scripts/status.py` | Critical path + single next action + pipeline counts |
| `scripts/blockers.py` | Full blocker chain with owner/next-action/follow-up |
| `scripts/adl.py` | Which live opportunities lack an Authorized Distributor Letter |
| `scripts/docs.py` | Generate capabilities statement, letterhead, quote/cover-email templates |
| `scripts/specs_extract.py` (via Python) | Extract NSN/CAGE/P-N from a manually-obtained PDF |
| `scripts/quote_add.py` (via Python) | Record a supplier's quote for a solicitation |
| `scripts/quote_render.py` (via Python) | Assemble the full quote package + Readiness Assessment |
| `scripts/pull.py` + `scripts/sam_client.py` | Pull live opportunities/attachments from SAM.gov (needs real API key + SAM active) |
| `scripts/score.py` | Rank current opportunities by lane coverage + NAICS match |
| `scripts/awards.py` | FPDS award/market intel + NAICS overlap against live opportunities (already-won contracts, not bids) |
| `scripts/notion_sync.py` (via `scripts/fn_sync.py`) | Live re-pull of opportunities/suppliers/links straight from Notion (needs a Notion integration token) |
| `scripts/fn_sync.py` | Refreshes from every live source with credentials on file (Notion + SAM.gov); safe to run on a schedule |
| `scripts/learning.py` | Record a quote's real outcome (won/lost/no_response); feeds `/fn-score`'s optional `supplier_track_record` weight |

See `.claude/commands/*.md` for the full usage of each.

## Troubleshooting

- **`doctor.py` says red / a key error:** you likely have a stale or missing `data/.dbkey`.
  If you still have the original key (back it up somewhere outside this repo the day
  `/fn-setup` first generates it), restoring it fixes everything. If it's genuinely lost,
  `data/ferrum_nexus.db` cannot be decrypted -- delete `data/` and re-run `/fn-setup` to
  rebuild from `seed/*.csv` (you lose anything entered after the initial seed: quotes, ADL
  status, attested specs).
- **A test fails after you change something:** run `pytest tests/ -q` and `ruff check .`
  before doing anything else -- the verification loop is the whole point of this build.
- **SAM.gov API changes a URL or field name:** update the pinned constants in
  `scripts/sam_client.py`; `tests/phase3/test_endpoints.py` will fail loudly if you forget.
- **Named owner for "when SAM API or a PDF format changes":** Brocque (this is a solo-operator
  tool -- there is no separate support org). Paste the error into Claude Code and say "fix
  this"; that's the whole troubleshooting loop per START-HERE-FERRUM-NEXUS.md.

## What this tool will never do (by design)

Auto-send or auto-submit anything (every draft is draft-only); fabricate a signed W-9 or an
Authorized Distributor Letter; force-download a CUI/controlled attachment; emit a green
"READY" verdict on a bid (only `BLOCKED` or `NOT_YET_REVIEWED` with a forced checklist,
and the Readiness rule set stays `UNVERIFIED` until a GovCon SME signs off against the golden
test set in `ferrum-nexus-BUILD-PLAN-v2.md` section 13).

## Definition of complete (this build)

All four phase gates GREEN on fresh output (`pytest tests/ -q`, `ruff check .`,
`scripts/demo_phase2.py`, `scripts/demo_phase3.py`), `/fn-doctor` green on a clean install
(verified by installing into a brand-new venv with zero reused state), and one real seeded
solicitation (`N0010426QNB47`) carried specs -> quote -> correct Readiness tier end to end.
