import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from db import connect  # noqa: E402
from specs_store import save_extraction  # noqa: E402
from attest import attest_all  # noqa: E402
from quote_add import add_quote  # noqa: E402
import readiness  # noqa: E402

SOL = "N0010426QNB47"


def _fully_attested_extraction():
    return {
        "status": "extracted",
        "fields": [
            {"field": "nsn", "value": "5310-01-208-2765", "page": 1, "confidence": "high",
             "attested": False},
            {"field": "cage", "value": "1A2B3", "page": 1, "confidence": "high",
             "attested": False},
        ],
    }


def _seed_supplier(conn, supplier_id="sup://1"):
    conn.execute(
        "INSERT INTO suppliers (notion_url, supplier_name) VALUES (?, 'Test Supplier')",
        (supplier_id,),
    )
    conn.commit()


def test_missing_adl_is_blocked(tmp_path):
    conn = connect(db_path=tmp_path / "ra1.db", key="q1" * 32)
    _seed_supplier(conn)
    extraction = _fully_attested_extraction()
    attest_all(extraction)
    save_extraction(conn, SOL, extraction)
    add_quote(conn, SOL, "sup://1", unit_price=1.0, total_price=25.0, adl_on_file=False)

    result = readiness.assess(conn, SOL)
    conn.close()

    assert result["tier"] == "BLOCKED"
    assert any("Authorized Distributor Letter" in r for r in result["reasons"])


def test_no_quote_on_file_is_blocked(tmp_path):
    conn = connect(db_path=tmp_path / "ra2.db", key="q2" * 32)
    extraction = _fully_attested_extraction()
    attest_all(extraction)
    save_extraction(conn, SOL, extraction)
    # no add_quote call at all

    result = readiness.assess(conn, SOL)
    conn.close()

    assert result["tier"] == "BLOCKED"
    assert any("no supplier quote on file" in r for r in result["reasons"])


def test_unattested_specs_is_blocked(tmp_path):
    conn = connect(db_path=tmp_path / "ra3.db", key="q3" * 32)
    _seed_supplier(conn)
    extraction = _fully_attested_extraction()  # NOT attested
    save_extraction(conn, SOL, extraction)
    add_quote(conn, SOL, "sup://1", adl_on_file=True)

    result = readiness.assess(conn, SOL)
    conn.close()

    assert result["tier"] == "BLOCKED"
    assert any("not fully attested" in r for r in result["reasons"])


def test_all_facts_present_yields_forced_checklist_never_ready(tmp_path):
    conn = connect(db_path=tmp_path / "ra4.db", key="q4" * 32)
    _seed_supplier(conn)
    extraction = _fully_attested_extraction()
    attest_all(extraction)
    save_extraction(conn, SOL, extraction)
    add_quote(conn, SOL, "sup://1", unit_price=1.0, total_price=25.0, adl_on_file=True)

    result = readiness.assess(conn, SOL)
    conn.close()

    assert result["tier"] == "NOT_YET_REVIEWED"
    assert result["reasons"] == []
    assert len(result["forced_checklist"]) > 0
    assert "READY" not in result["tier"]


def test_rule_set_is_flagged_unverified(tmp_path):
    conn = connect(db_path=tmp_path / "ra5.db", key="q5" * 32)
    result = readiness.assess(conn, "NONEXISTENT")
    conn.close()

    assert result["rule_verified"] is False
    assert "UNVERIFIED" in result["banner"]


def test_render_never_prints_the_word_ready_as_a_verdict():
    conn_free_result = {
        "solicitation_number": SOL, "tier": "NOT_YET_REVIEWED", "reasons": [],
        "forced_checklist": [("x", "check x")], "banner": "UNVERIFIED (awaiting SME)",
        "rule_version": "v0", "rule_verified": False,
    }
    text = readiness.render(conn_free_result)
    assert "TIER: NOT_YET_REVIEWED" in text
    assert "must still verify" in text
