import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import fitz  # PyMuPDF, used only to build synthetic test PDFs  # noqa: E402
from specs_extract import extract_from_pdf  # noqa: E402
from attest import (  # noqa: E402
    is_fully_attested, attest_field, attest_all, get_quote_ready_fields,
)


def _make_text_pdf(path: Path) -> None:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(
        (72, 72),
        "SOLICITATION N0010426QNB47\n"
        "NSN: 5310-01-208-2765\n"
        "CAGE: 1A2B3\n"
        "P/N: 251T0100-186\n"
        "MATERIAL: STAINLESS STEEL 17-4PH\n"
        "QTY: 25\n",
    )
    doc.save(path)
    doc.close()


def _make_blank_pdf(path: Path) -> None:
    doc = fitz.open()
    doc.new_page()  # no insert_text -> no extractable text layer
    doc.save(path)
    doc.close()


def test_text_pdf_yields_cited_fields_with_confidence(tmp_path):
    pdf_path = tmp_path / "text.pdf"
    _make_text_pdf(pdf_path)

    result = extract_from_pdf(pdf_path)

    assert result["status"] == "extracted"
    by_field = {f["field"]: f for f in result["fields"]}
    assert by_field["nsn"]["value"] == "5310-01-208-2765"
    assert by_field["nsn"]["page"] == 1
    assert by_field["nsn"]["confidence"] == "high"
    assert by_field["cage"]["value"] == "1A2B3"
    assert by_field["part_number"]["value"] == "251T0100-186"
    assert by_field["quantity"]["value"] == "25"
    # nothing is attested yet just because it was extracted
    assert all(f["attested"] is False for f in result["fields"])


def test_scanned_pdf_yields_needs_manual_entry(tmp_path):
    pdf_path = tmp_path / "blank.pdf"
    _make_blank_pdf(pdf_path)

    result = extract_from_pdf(pdf_path)

    assert result["status"] == "needs_manual_entry"
    assert result["fields"] == []


def test_no_field_usable_before_attestation(tmp_path):
    pdf_path = tmp_path / "text2.pdf"
    _make_text_pdf(pdf_path)
    result = extract_from_pdf(pdf_path)

    assert is_fully_attested(result) is False
    assert get_quote_ready_fields(result) == []

    attest_field(result, "nsn")
    assert get_quote_ready_fields(result) == [f for f in result["fields"] if f["field"] == "nsn"]
    assert is_fully_attested(result) is False  # other fields still unattested


def test_batch_attest_requires_low_confidence_shown_first(tmp_path):
    pdf_path = tmp_path / "text3.pdf"
    _make_text_pdf(pdf_path)
    result = extract_from_pdf(pdf_path)

    # All fields here are "high" confidence (regex-matched exactly), so batch
    # attest without the flag is fine in this fixture...
    attest_all(result)
    assert is_fully_attested(result) is True

    # ...but if any field is low-confidence, batch attest must refuse silently
    # skipping the human review step.
    result2 = extract_from_pdf(pdf_path)
    result2["fields"][0]["confidence"] = "low"
    try:
        attest_all(result2)
        assert False, "expected ValueError when low-confidence fields aren't shown first"
    except ValueError:
        pass
    attest_all(result2, shown_low_confidence=True)
    assert is_fully_attested(result2) is True
