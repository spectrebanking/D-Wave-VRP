"""2.2 -- /fn-quote <sol#>: merge attested specs + supplier quote + entity
config into a quote sheet + cover email + attachment checklist + Readiness
Assessment. Draft only -- there is no send path in this module or anywhere
in this package.

Blocked (per [2.2a] consensus fix) if no quote has been added via
/fn-quote-add for this solicitation yet.
"""
import json
from pathlib import Path

from id_resolver import resolve_opportunity
from specs_store import load_extraction
from quote_add import get_quotes_for_solicitation
import readiness

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CONFIG_PATH = DATA_DIR / "config.json"


class QuoteBlocked(Exception):
    """Raised when /fn-quote is asked to render before /fn-quote-add has run."""


def _load_config() -> dict:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError("data/config.json not found -- run /fn-setup first")
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def build_quote_package(conn, solicitation_number: str) -> dict:
    opp = resolve_opportunity(conn, solicitation_number)
    if opp is None:
        raise ValueError(f"no opportunity found for {solicitation_number!r}")

    quotes = get_quotes_for_solicitation(conn, solicitation_number)
    if not quotes:
        raise QuoteBlocked(
            f"no supplier quote on file for {solicitation_number!r} -- "
            "run /fn-quote-add before /fn-quote"
        )

    cfg = _load_config()
    extraction = load_extraction(conn, solicitation_number)
    specs = {f["field"]: f["value"] for f in extraction["fields"] if f["attested"]}
    quote = quotes[0]  # first quote on file; multiple quotes -> human picks in a later pass

    assessment = readiness.assess(conn, solicitation_number)

    attachment_checklist = [
        "Authorized Distributor Letter (required)",
        "Certificate of Conformance",
        "Supplier quote",
        "W-9",
    ]

    return {
        "opportunity": opp,
        "specs": specs,
        "quote": quote,
        "entity": cfg,
        "readiness": assessment,
        "attachment_checklist": attachment_checklist,
    }


def render_quote_sheet(package: dict) -> str:
    cfg = package["entity"]
    specs = package["specs"]
    quote = package["quote"]
    return "\n".join([
        f"# NAVSUP Quote Sheet -- {cfg.get('legal_name', '')} (DBA {cfg.get('dba', '')})",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Sol# | {package['opportunity']['solicitation_number'] or ''} |",
        f"| NSN | {specs.get('nsn', '')} |",
        f"| Nomenclature | {package['opportunity']['title']} |",
        f"| Mfr CAGE | {specs.get('cage', '')} |",
        f"| Mfr P/N | {specs.get('part_number', '')} |",
        f"| Unit Price FIRM | {quote.get('unit_price', '')} |",
        f"| Total Price FIRM | {quote.get('total_price', '')} |",
        f"| PTAT | {quote.get('ptat', '')} |",
        f"| FOB | {quote.get('fob', '')} |",
        f"| Awardee CAGE | {cfg.get('cage_code') or 'PENDING'} |",
        "| Business size | Small |",
        f"| NAICS | {', '.join(cfg.get('naics_codes', []))} |",
        f"| SAM active / UEI | {cfg.get('uei') or 'PENDING'} |",
        "| Payment preference | GCPC or WAWF |",
    ])


def render_cover_email(package: dict) -> str:
    cfg = package["entity"]
    quote = package["quote"]
    opp = package["opportunity"]
    return "\n".join([
        f"Subject: Quote Submission -- Sol# {opp['solicitation_number']}",
        "",
        f"Attached is our quote for Sol# {opp['solicitation_number']}, {opp['title']}.",
        "",
        f"- Unit Price FIRM: {quote.get('unit_price', '')}",
        f"- Total Price FIRM: {quote.get('total_price', '')}",
        f"- PTAT: {quote.get('ptat', '')}",
        f"- FOB: {quote.get('fob', '')}",
        "",
        "Attachments: quote sheet, Authorized Distributor Letter, "
        "Certificate of Conformance, W-9.",
        "",
        f"{cfg.get('legal_name', '')} (DBA {cfg.get('dba', '')})",
        f"CAGE: {cfg.get('cage_code') or 'PENDING'} | UEI: {cfg.get('uei') or 'PENDING'}",
    ])


def render_full_package(package: dict) -> str:
    parts = [
        render_quote_sheet(package),
        "",
        "---",
        "",
        render_cover_email(package),
        "",
        "---",
        "",
        "## Attachment checklist",
        *[f"- [ ] {item}" for item in package["attachment_checklist"]],
        "",
        "---",
        "",
        readiness.render(package["readiness"]),
    ]
    return "\n".join(parts)
