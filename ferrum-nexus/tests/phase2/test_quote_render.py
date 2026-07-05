import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from db import connect  # noqa: E402
from seed import load_all  # noqa: E402
from specs_extract import extract_from_pdf  # noqa: E402
from attest import attest_all  # noqa: E402
from specs_store import save_extraction  # noqa: E402
from quote_add import add_quote  # noqa: E402
import quote_render  # noqa: E402

import fitz  # noqa: E402

SOL = "N0010426QNB47"
SUPPLIER = "https://app.notion.com/382ed5bb5bca818186decc59ade1fdd7"  # MSC Industrial (Federal)


def _make_text_pdf(path: Path) -> None:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(
        (72, 72),
        "NSN: 5310-01-208-2765\nCAGE: 1A2B3\nP/N: 251T0100-186\nQTY: 25\n",
    )
    doc.save(path)
    doc.close()


def _setup(conn, tmp_path, monkeypatch):
    load_all(conn)
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    config_path = data_dir / "config.json"
    config_path.write_text(json.dumps({
        "legal_name": "Apollo Credit Processing LLC", "dba": "Ferrum Nexus",
        "naics_codes": ["332722"], "uei": None, "cage_code": None,
    }), encoding="utf-8")
    monkeypatch.setattr(quote_render, "DATA_DIR", data_dir)
    monkeypatch.setattr(quote_render, "CONFIG_PATH", config_path)


def test_quote_blocked_without_quote_add(tmp_path, monkeypatch):
    conn = connect(db_path=tmp_path / "qr1.db", key="qr1" * 21 + "q")
    _setup(conn, tmp_path, monkeypatch)

    pdf_path = tmp_path / "spec.pdf"
    _make_text_pdf(pdf_path)
    extraction = extract_from_pdf(pdf_path)
    attest_all(extraction)
    save_extraction(conn, SOL, extraction)

    try:
        quote_render.build_quote_package(conn, SOL)
        assert False, "expected QuoteBlocked without a prior /fn-quote-add"
    except quote_render.QuoteBlocked:
        pass
    conn.close()


def test_full_quote_package_after_specs_attested_and_quote_added(tmp_path, monkeypatch):
    conn = connect(db_path=tmp_path / "qr2.db", key="qr2" * 21 + "q")
    _setup(conn, tmp_path, monkeypatch)

    pdf_path = tmp_path / "spec2.pdf"
    _make_text_pdf(pdf_path)
    extraction = extract_from_pdf(pdf_path)
    attest_all(extraction)
    save_extraction(conn, SOL, extraction)

    add_quote(conn, SOL, SUPPLIER, unit_price=2.15, total_price=53.75, ptat="30 days ARO",
              fob="Origin", adl_on_file=True)

    package = quote_render.build_quote_package(conn, SOL)
    conn.close()

    assert package["opportunity"]["solicitation_number"] == SOL
    assert package["specs"]["nsn"] == "5310-01-208-2765"
    assert package["quote"]["unit_price"] == 2.15
    assert package["readiness"]["tier"] == "NOT_YET_REVIEWED"

    rendered = quote_render.render_full_package(package)
    assert "5310-01-208-2765" in rendered
    assert "2.15" in rendered
    assert "Authorized Distributor Letter" in rendered
    assert "UNVERIFIED" in rendered
    assert "READY" not in rendered.split("TIER:")[1].split("\n")[0]
