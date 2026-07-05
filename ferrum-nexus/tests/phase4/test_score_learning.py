import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from db import connect  # noqa: E402
from quote_add import add_quote  # noqa: E402
import learning  # noqa: E402
from score import score_opportunity, DEFAULT_WEIGHTS  # noqa: E402


def _seed(conn):
    conn.execute(
        "INSERT INTO opportunities (notion_url, title, naics_code, active, pipeline) "
        "VALUES ('opp://a', 'BOLT,HEX', '332722', 1, 'Inbox')"
    )
    conn.execute("INSERT INTO suppliers (notion_url, supplier_name) VALUES ('sup://good', 'Reliable Co')")
    conn.execute(
        "INSERT INTO opportunity_supplier_links (opportunity_id, supplier_id) "
        "VALUES ('opp://a', 'sup://good')"
    )
    conn.commit()


def test_default_weight_zero_means_no_behavior_change(tmp_path):
    conn = connect(db_path=tmp_path / "s1.db", key="a" * 64)
    _seed(conn)
    add_quote(conn, "SOL-A", "sup://good")
    learning.record_outcome(conn, "SOL-A::sup://good", "lost")  # bad track record

    result = score_opportunity(conn, "opp://a", ["332722"])
    conn.close()

    # supplier_track_record defaults to 0.0 weight -- a losing track record
    # must not change the score unless someone explicitly opts in.
    assert result["score"] == DEFAULT_WEIGHTS["lane_coverage"] + DEFAULT_WEIGHTS["naics_match"]
    assert not any("supplier_track_record" in r for r in result["reasons"])


def test_custom_weights_without_supplier_track_record_key_still_works(tmp_path):
    # A caller passing an old-shaped 2-key weights dict (pre-dating this
    # feature) must not KeyError.
    conn = connect(db_path=tmp_path / "s2.db", key="b" * 64)
    _seed(conn)
    result = score_opportunity(
        conn, "opp://a", ["332722"], weights={"lane_coverage": 0.5, "naics_match": 0.5}
    )
    conn.close()
    assert result["score"] == 1.0


def test_opting_in_raises_score_for_a_reliable_supplier(tmp_path):
    conn = connect(db_path=tmp_path / "s3.db", key="c" * 64)
    _seed(conn)
    add_quote(conn, "SOL-A", "sup://good")
    learning.record_outcome(conn, "SOL-A::sup://good", "won")

    weights = {"lane_coverage": 0.5, "naics_match": 0.3, "supplier_track_record": 0.2}
    result = score_opportunity(conn, "opp://a", ["332722"], weights=weights)
    conn.close()

    assert result["score"] == 1.0  # 0.5 + 0.3 + 0.2 * 1.0
    assert any("supplier_track_record=1.00" in r for r in result["reasons"])


def test_opting_in_with_no_decided_history_uses_neutral_prior(tmp_path):
    conn = connect(db_path=tmp_path / "s4.db", key="d" * 64)
    _seed(conn)  # sup://good has a link but no quote/outcome at all

    weights = {"lane_coverage": 0.5, "naics_match": 0.3, "supplier_track_record": 0.2}
    result = score_opportunity(conn, "opp://a", ["332722"], weights=weights)
    conn.close()

    assert result["score"] == round(0.5 + 0.3 + 0.2 * 0.5, 4)  # neutral prior, not penalized
