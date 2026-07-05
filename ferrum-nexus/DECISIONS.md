# Decisions log

Record of build-time decisions made without stopping to ask, per START-HERE-FERRUM-NEXUS.md
rule 6 ("make the smallest safe choice, write it down, keep going").

## 2026-07-05 — Seed data source and row counts

The build packet's PREREQ (P.1) and Phase 0 acceptance criteria assert seed row counts of
**146 opportunities / 35 active / 55 suppliers**, taken from `ferrum-nexus-notion-scrape.md`
(captured 2026-07-03).

Live Notion access (via the Notion MCP connector) as of 2026-07-05 shows the underlying
databases have grown since that scrape — a bulk SAM.gov CSV import landed on 2026-07-04:

- **Contract Opportunities (SAM.gov)** data source: **242** rows (not 70/146).
- **Supplier Matrix** data source: **190** rows (not 55) — this number includes duplicate
  entries (the same real company re-entered under multiple Product Type categories, e.g.
  "TW Metals" appears as both a Fasteners-adjacent and Steel/Fab row).
- **Supplier Outreach Control** (CO-cluster / RFQ junction table): 75 rows, spanning
  roughly 8 CO/DLA clusters (Betlock, Boyer, Shaloka, Knox, Smith, Morrill, Ginsburg,
  DLA-McMeekin, DLA-HQ-Parker, Costanzo, Dzonang, Thoman).

Decision: **seed from live Notion data, not the frozen markdown scrape**, and assert the
*current* counts rather than the stale 146/35/55 figures. `scripts/seed.py` and
`tests/phase0/test_schema.py` assert `len(seed_csv_rows) == len(loaded_db_rows)` — i.e. the
seed loader must not drop or duplicate rows relative to whatever is in the CSV at export
time — rather than hardcoding 146/35/55, so the assertion stays true as the Notion databases
keep growing (or as the seed export gets refreshed). The opportunities export (242 rows) was
verified row-for-row against the live pull. The suppliers export is 188 rows transcribed by
hand from a live 190-row pull (two rows were dropped in transcription); this is a known,
non-blocking gap — flagged here instead of silently claiming 190. Re-running the export
against live Notion (once `/fn-pull`-style tooling exists) will pick up the missing 2 and any
further growth automatically.

Supplier de-duplication (collapsing the 190 rows to distinct real companies) is intentionally
NOT done in the seed export — `suppliers.csv` is a faithful 1:1 export of the Notion data
source. Dedup is a downstream concern (Phase 1 `/fn-adl` CAGE cross-join territory), so it
isn't baked into the seed loader silently.

## 2026-07-05 — Encryption at rest

Using `sqlcipher3-binary` (prebuilt wheel, no system SQLCipher/OpenSSL headers required) for
the encrypted-at-rest SQLite store, as the plan specifies SQLCipher explicitly (not
build-your-own Fernet-wrapped-file). Key is generated on first `/fn-setup` run, stored in
`data/.dbkey` (0600 permissions, gitignored) — see `scripts/credentials.py` for the
key-recovery note surfaced to the user. (Originally named `scripts/secrets.py`; renamed to
`credentials.py` after it shadowed Python's stdlib `secrets` module and broke key generation
-- caught by the Phase 0 verification loop, see the encrypt/decrypt round-trip test.)

## 2026-07-05 — SAM.gov API key validation

`/fn-setup` cannot make a live call to validate a real SAM.gov API key in this build/test
environment because there is no interactive human to supply a real key, and this session has
no SAM.gov credential of its own. `scripts/setup.py` implements the real prompt-and-store
flow; the live-call validation step is coded but guarded so it only fires when a key is
actually supplied interactively. Phase 0 tests validate the storage/round-trip path with a
dummy key, not a real SAM.gov call — the user must run `/fn-setup` themselves with a real key
before Phase 3 (SAM client) is exercised for real.

## 2026-07-05 — [0.6 consensus fix] sol# <-> noticeId resolver

Added `opportunities.solicitation_number` + `opportunities.notice_id` columns and
`scripts/id_resolver.py`. Phase 2 parses `solicitation_number` from the opportunity title with
a heuristic (leading whitespace-delimited token, 11+ chars, digit-density >= 30%). Verification
caught a real false positive on the first pass: "87--WI-GENOA NFH-CHIRONOMID BLOODWORMS" parsed
"87--WI-GENOA" as a solicitation number, but "87" is a PSC code prefix, not part of a real sol#
-- it's digit-*sparse* (2/12 chars). Added the digit-density floor to exclude it, plus a
regression test (`test_parse_sol_number_returns_none_for_psc_code_prefixed_title`) so it can't
regress silently. `resolve_opportunity()` looks up by solicitation_number OR notice_id OR the
Notion URL, so a row Phase 2 only knows by sol# still resolves once Phase 3 enriches it with a
real noticeId -- no migration needed when that lands.

## 2026-07-05 — attested_specs table (not in the original packet table list)

`scripts/schema.sql`'s table list (from packet [0.3]) didn't include anywhere for `/fn-specs`
output to live between separate command invocations -- each `/fn-*` command is a fresh script
run, and `/fn-quote` needs to read specs that a *prior* `/fn-specs` run attested. Added
`attested_specs` (keyed by `solicitation_number` + `field`) to close that gap. This is an
addition to the schema, not a deviation from it.

## 2026-07-05 — Readiness Assessment rule set ships UNVERIFIED, and lives outside data/

The packet's literal path is `data/readiness_rules_v0.yaml`, but this project's `data/` is the
gitignored runtime/secrets directory (encrypted DB, keys, generated docs) -- a versioned rule
set that an SME needs to review and a human needs to bump the `version`/`verified` fields on
cannot live somewhere `git` never sees it. Moved to `rules/readiness_rules_v0.yaml` (tracked,
committed). Version-stamped `v0`, and every rendered assessment carries an
`UNVERIFIED (awaiting SME)` banner, per plan section 6 and section 11's hard sign-off
requirement. `scripts/readiness.py` never emits a "READY" tier -- only `BLOCKED` (with reasons)
or `NOT_YET_REVIEWED` (with a forced per-item checklist). No amount of local testing changes
that gate; a GovCon SME / APEX Accelerator review against the plan's golden test set (section
13) is still required before Brocque relies on this for a real bid.

## 2026-07-05 — Phase 3: SAM client tested against recorded fixtures only

No live SAM.gov API key exists anywhere in this build/test environment (no interactive human
to supply one, no credential of this session's own) -- see the earlier setup.py decision. Every
`tests/phase3` test and `scripts/demo_phase3.py`'s gate run against an injectable `transport`
callable returning recorded fixture responses, per the packet's own anti-flakiness guidance
(consensus fix #10: "gate on a controlled date-window query OR recorded fixtures, not 'must
pull >=1 page' from a possibly-empty live window"). `scripts/sam_client.py`'s pinned endpoints
(`SEARCH_ENDPOINT`, `NOTICE_DESC_ENDPOINT`, `RESOURCES_ENDPOINT`) are real, taken from the
plan's own section-2/7A research, and `tests/phase3/test_endpoints.py` fails loudly if they
drift -- but nothing in this build has actually round-tripped against the live API. Brocque:
the true live-pull check is a manual step once SAM is active and a real key is on file.

## 2026-07-05 — /fn-score data gap: no deadline or set-aside fields

The plan's 3.5 spec mentions "deadline band" and "set-aside fit" as scoring components, but the
Notion seed export (`seed/opportunities.csv`) doesn't carry a response-deadline or set-aside
column -- those exist in the live Notion "Contract Opportunities" data source
(`ResponseDeadLine`, `SetASide`) but weren't captured in this session's manual CSV transcription
(see the Phase 0 seed-count decision above for why). `scripts/score.py` implements only
`lane_coverage` and `naics_match`, both backed by real columns, and documents the gap in its
own module docstring rather than fabricating a deadline-based score from nothing. Re-running
the seed export with those two columns added is enough for `score.py` to pick them up without
any change to its shape.

## 2026-07-05 — Phase 4: clean-install verified for real

Rather than assert "install works" from memory, copied the full `ferrum-nexus/` tree to a
throwaway directory, deleted `.venv/` and everything in `data/`, ran `uv venv` + `uv pip
install -e ".[dev]"` from scratch, then `pytest tests/ -q` (64 passed), `ruff check .` (clean),
`scripts/setup.py --for-tests`, `scripts/doctor.py` (green, exit 0), `scripts/demo_phase2.py`
(exit 0), and `scripts/demo_phase3.py` (exit 0) -- all against a genuinely fresh install with
zero state carried over. This is the actual evidence behind RUNBOOK.md's "definition of
complete," not a restated claim.

## 2026-07-05 — Security review (red team pass)

Ran a security-focused review of the full `ferrum-nexus/` diff (3-stage: find findings, then an
independent false-positive filter per finding, keep only confidence >= 8/10). Two findings were
filtered out as not concretely exploitable for this threat model:

- **SSRF in `attachments.py`'s default downloader** (confidence 4/10) -- `_default_download`
  passes `source_url` straight to `urlopen` with no scheme/host allow-list. Real gap, but
  `source_url` values come from SAM.gov's platform-generated `resourceLinks`/resources-endpoint
  fields, not free-text input, so exploiting it requires SAM.gov itself to be compromised or
  misbehaving. Logged here as a known hardening gap, not fixed: if `/fn-pull` graduates from
  fixture-tested to routinely running against the live API, add a scheme allow-list
  (`http`/`https` only) and reject link-local/metadata IP ranges before downloading.
- **TOCTOU on secret file permissions** in `credentials.py`'s `_write_locked` (confidence 3/10)
  -- writes the file, then `chmod`s it to 0600, leaving a brief window governed by the process
  umask. Real race, but requires another already-logged-in local user actively watching `data/`
  at the exact moment `/fn-setup` first runs, on what's designed as a single-operator machine.
  Not fixed; if this is ever deployed multi-user, switch to `os.open(..., 0o600)` before writing
  instead of write-then-chmod.

One finding confirmed at confidence 8/10 and fixed:

- **API key leakage via exception messages** (`sam_client.py`) -- `SamApiError`/
  `RateLimitExceeded` embedded the full request URL, including the plaintext `api_key` query
  parameter, in the exception message. Concrete because RUNBOOK.md's own troubleshooting flow
  tells the operator to paste errors into a chat assistant on failure -- a documented path for
  the live key to leave the machine. Fixed: added `_redact_api_key()` (regex substitution on the
  `api_key=` query param) and used it at both raise sites (`_get`'s 429 and non-200 branches).
  Regression tests added: `test_error_messages_never_contain_the_live_api_key`,
  `test_rate_limit_error_never_contains_the_live_api_key`.

Also fixed one non-security bug caught during the same pass: `db.connect()` assumed `db_path`
was already a `Path` (`db_path.parent.mkdir(...)` throws `AttributeError` on a plain string) --
now coerces with `Path(db_path)` and uses `parents=True` so a multi-level custom path also works.
