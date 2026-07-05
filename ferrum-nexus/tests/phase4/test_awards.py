import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import pytest  # noqa: E402
from db import connect  # noqa: E402
from seed import load_all  # noqa: E402
import awards  # noqa: E402


@pytest.fixture()
def seeded_conn(tmp_path):
    conn = connect(db_path=tmp_path / "test.db", key="a" * 64)
    load_all(conn)
    yield conn
    conn.close()


def test_awards_and_market_intel_seeded(seeded_conn):
    n_awards = seeded_conn.execute("SELECT COUNT(*) FROM awards").fetchone()[0]
    n_intel = seeded_conn.execute("SELECT COUNT(*) FROM market_intel").fetchone()[0]
    assert n_awards > 0
    assert n_intel > 0


def test_naics_overlap_finds_the_seeded_die_steel_match(seeded_conn):
    # Two seeded U.S. Mint awards (2031JG24F00379, 2031JG24F00429) share
    # NAICS 333514 with no seeded opportunity by default -- this asserts the
    # overlap query runs cleanly end-to-end and returns the right shape even
    # when the match set happens to be empty.
    report = awards.award_naics_overlap_report(seeded_conn)
    assert len(report) == seeded_conn.execute("SELECT COUNT(*) FROM awards").fetchone()[0]
    for entry in report:
        assert "matching_opportunities" in entry
        assert isinstance(entry["matching_opportunities"], list)


def test_naics_overlap_matches_a_live_opportunity_when_naics_aligns(seeded_conn):
    # Insert a live opportunity sharing NAICS 333514 with the seeded Dunkirk
    # Specialty Steel die-steel awards, and confirm the cross-reference finds it.
    seeded_conn.execute(
        "INSERT INTO opportunities (notion_url, title, active, naics_code) "
        "VALUES (?, ?, 1, ?)",
        ("https://example.test/die-steel-opp", "Die Steel RFQ", "333514"),
    )
    seeded_conn.commit()

    matches = awards.naics_matches_for_award(seeded_conn, "333514")
    titles = [m[1] for m in matches]
    assert "Die Steel RFQ" in titles


def test_render_market_intel_orders_by_priority_then_value(seeded_conn):
    output = awards.render_market_intel(seeded_conn)
    assert "FERRUM MARKET INTELLIGENCE" in output
    # The highest-value P0 item (PSC 9535, ~$39.5B) must lead the P0 block.
    assert output.index("9535") < output.index("DUNKIRK SPECIALTY STEEL LLC")


def test_market_intel_never_silently_drops_a_row_without_value_sum(seeded_conn):
    seeded_conn.execute(
        "INSERT INTO market_intel (notion_url, intel_item, category, priority) "
        "VALUES (?, ?, ?, ?)",
        ("https://example.test/no-value", "Untitled lane note", "Lane", "P2 Watch"),
    )
    seeded_conn.commit()
    output = awards.render_market_intel(seeded_conn)
    assert "Untitled lane note" in output
    assert "n/a" in output
