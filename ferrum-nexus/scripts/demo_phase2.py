"""Phase 2 gate acceptance command (consensus fix #6): asserts specs -> quote
-> correct Readiness tier for one named, real, seeded solicitation. Exits
non-zero and prints which assertion failed if anything regresses -- this is
a check, not narration.

Usage: uv run python scripts/demo_phase2.py --sol N0010426QNB47
"""
import argparse
import sys
import tempfile
from pathlib import Path

import fitz

from db import connect
from setup import run_noninteractive_for_tests
from id_resolver import resolve_opportunity
from specs_extract import extract_from_pdf
from attest import attest_all
from specs_store import save_extraction
from quote_add import add_quote, get_quotes_for_solicitation
import readiness
import quote_render

DEFAULT_SOL = "N0010426QNB47"  # real seeded solicitation: NUT,SELF-LOCKING,HEXAGON


def _make_demo_spec_pdf(path: Path, sol: str) -> None:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(
        (72, 72),
        f"SOLICITATION {sol}\nNSN: 5310-01-208-2765\nCAGE: 1A2B3\n"
        "P/N: 251T0100-186\nQTY: 100\n",
    )
    doc.save(path)
    doc.close()


def run(sol: str) -> None:
    run_noninteractive_for_tests()
    conn = connect()

    opp = resolve_opportunity(conn, sol)
    assert opp is not None, f"gate failed: {sol!r} not found in seeded opportunities"
    print(f"[1/5] resolved opportunity: {opp['title']}")

    linked = conn.execute(
        "SELECT supplier_id FROM opportunity_supplier_links WHERE opportunity_id = ?",
        (opp["notion_url"],),
    ).fetchall()
    assert linked, f"gate failed: {sol!r} has no linked supplier in the seeded data"
    supplier_id = linked[0][0]
    print(f"[2/5] using linked supplier: {supplier_id}")

    demo_pdf = Path(tempfile.gettempdir()) / f"{sol}_demo.pdf"
    _make_demo_spec_pdf(demo_pdf, sol)
    extraction = extract_from_pdf(demo_pdf)
    assert extraction["status"] == "extracted", "gate failed: demo PDF did not extract text"
    attest_all(extraction)
    save_extraction(conn, sol, extraction)
    print(f"[3/5] specs extracted + attested: {[f['field'] for f in extraction['fields']]}")

    pre_quote = readiness.assess(conn, sol)
    assert pre_quote["tier"] == "BLOCKED", (
        f"gate failed: expected BLOCKED before /fn-quote-add, got {pre_quote['tier']}"
    )
    assert any("no supplier quote" in r for r in pre_quote["reasons"])
    print(f"[4/5] pre-quote tier correctly BLOCKED: {pre_quote['reasons']}")

    add_quote(conn, sol, supplier_id, unit_price=1.25, total_price=125.0,
              ptat="30 days ARO", fob="Origin", adl_on_file=True)
    quotes = get_quotes_for_solicitation(conn, sol)
    assert len(quotes) == 1, "gate failed: /fn-quote-add did not persist the quote"

    package = quote_render.build_quote_package(conn, sol)
    assert package["readiness"]["tier"] == "NOT_YET_REVIEWED", (
        f"gate failed: expected NOT_YET_REVIEWED after quote+ADL, "
        f"got {package['readiness']['tier']} ({package['readiness']['reasons']})"
    )
    rendered = quote_render.render_full_package(package)
    assert "UNVERIFIED" in rendered
    assert "READY" not in rendered.split("TIER:")[1].split("\n")[0]
    print("[5/5] post-quote tier correctly NOT_YET_REVIEWED, banner UNVERIFIED, never READY")

    conn.close()
    demo_pdf.unlink(missing_ok=True)
    print(f"\nPHASE 2 GATE: PASS -- {sol} ran specs -> quote -> correct Readiness tier")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sol", default=DEFAULT_SOL)
    args = parser.parse_args()
    try:
        run(args.sol)
    except AssertionError as exc:
        print(f"\nPHASE 2 GATE: FAIL -- {exc}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
