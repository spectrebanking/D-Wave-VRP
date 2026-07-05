"""1.4 — /fn-docs: one-time generator for the 5 standing documents.

Note on the W-9: a real W-9 is a signed IRS tax form, not something this tool
can legally fabricate. What it generates is a filled *checklist* of the exact
fields the human needs to drop into the real IRS W-9 PDF -- not a substitute
for it. The other 4 (capabilities statement, letterhead, quote template,
cover-email template) are genuine drafts ready to use/edit.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
CONFIG_PATH = DATA_DIR / "config.json"
OUT_DIR = DATA_DIR / "generated_docs"


def _load_config() -> dict:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError("data/config.json not found -- run /fn-setup first")
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def _w9_checklist(cfg: dict) -> str:
    return f"""# W-9 checklist (fill the REAL IRS W-9 PDF with these -- this is not a W-9)

- Name: {cfg.get('legal_name', '')}
- Business name/disregarded entity name: {cfg.get('dba', '')}
- Federal tax classification: LLC (confirm election, e.g. disregarded/S-corp/C-corp)
- Address: [fill from entity registration]
- EIN: [from IRS CP 575]
- Signature + date: [Brocque signs the actual PDF -- not generated here]

Download the current W-9 from irs.gov/forms-pubs/about-form-w-9, fill by hand,
sign, save as PDF, keep on file per the NAVSUP RFQ protocol.
"""


def _capabilities_statement(cfg: dict) -> str:
    naics = ", ".join(cfg.get("naics_codes", []))
    return f"""# Capabilities Statement -- {cfg.get('dba', '')}

**Legal name:** {cfg.get('legal_name', '')} (DBA {cfg.get('dba', '')})
**UEI:** {cfg.get('uei') or 'PENDING'}
**CAGE code:** {cfg.get('cage_code') or 'PENDING'}
**NAICS codes:** {naics}
**Business size:** Small business
**Set-aside status:** Veteran-owned small business (confirm SDVOSB/VOSB certification status)

## Core competencies
Federal defense-parts broker/reseller -- fasteners, valves, pipe/fittings, steel/alloys,
copper/bronze, doors/hardware, and MRO items sourced from authorized distributors and
manufacturers for DLA and NAVSUP simplified acquisitions and GPC micro-purchases.

## Differentiators
Fast quote turnaround; NAVSUP-format quote packages; direct supplier relationships
across 6+ product lanes.

## Contact
[fill: POC name, phone, email]
"""


def _letterhead(cfg: dict) -> str:
    return f"""{cfg.get('legal_name', '')}
DBA {cfg.get('dba', '')}
[Address line 1]
[City, State ZIP]
[Phone] | [Email]
UEI: {cfg.get('uei') or 'PENDING'} | CAGE: {cfg.get('cage_code') or 'PENDING'}

---
"""


def _quote_template(cfg: dict) -> str:
    return f"""# NAVSUP Quote Sheet -- {cfg.get('legal_name', '')} (DBA {cfg.get('dba', '')})

| Field | Value |
|---|---|
| Sol# | |
| NSN | |
| Nomenclature | |
| Mfr CAGE | |
| Mfr P/N | |
| Unit Price FIRM | |
| Total Price FIRM | |
| PTAT (lead time ARO) | |
| FOB point | |
| Awardee CAGE | {cfg.get('cage_code') or 'PENDING'} |
| Business size | Small |
| NAICS | {', '.join(cfg.get('naics_codes', []))} |
| SAM active / UEI | {cfg.get('uei') or 'PENDING'} |
| Payment preference | GCPC or WAWF |

Attachments required: Authorized Distributor Letter (required), Certificate of
Conformance, supplier quote, W-9.
"""


def _cover_email_template(cfg: dict) -> str:
    return f"""Subject: Quote Submission -- Sol# [SOL_NUMBER]

Attached is our quote for Sol# [SOL_NUMBER], NSN [NSN], Nomenclature [NOMENCLATURE].

- Unit Price FIRM: [PRICE]
- Total Price FIRM: [PRICE]
- PTAT: [LEAD TIME] ARO
- FOB: [POINT]

Attachments: quote sheet, Authorized Distributor Letter, Certificate of Conformance, W-9.

{cfg.get('legal_name', '')} (DBA {cfg.get('dba', '')})
CAGE: {cfg.get('cage_code') or 'PENDING'} | UEI: {cfg.get('uei') or 'PENDING'}
"""


GENERATORS = {
    "w9-checklist.md": _w9_checklist,
    "capabilities-statement.md": _capabilities_statement,
    "letterhead.md": _letterhead,
    "quote-template.md": _quote_template,
    "cover-email-template.md": _cover_email_template,
}


def generate_all() -> dict[str, Path]:
    cfg = _load_config()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    written = {}
    for filename, generator in GENERATORS.items():
        path = OUT_DIR / filename
        path.write_text(generator(cfg), encoding="utf-8")
        written[filename] = path
    return written


def main() -> None:
    written = generate_all()
    for name, path in written.items():
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
