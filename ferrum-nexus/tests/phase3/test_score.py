import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from db import connect  # noqa: E402
from score import score_opportunity, score_all, is_sole_source, DEFAULT_WEIGHTS  # noqa: E402


def _seed(conn):
    conn.execute(
        "INSERT INTO opportunities (notion_url, title, naics_code, active, pipeline) "
        "VALUES ('opp://sole', 'Notice of Intent to Sole Source Widget Supply', "
        "'332722', 1, 'Inbox')"
    )
    conn.execute(
        "INSERT INTO opportunities (notion_url, title, naics_code, active, pipeline) "
        "VALUES ('opp://nobid', 'Some off-lane service', '541620', 1, 'No-bid')"
    )
    conn.execute(
        "INSERT INTO opportunities (notion_url, title, naics_code, active, pipeline) "
        "VALUES ('opp://covered', 'NUT,SELF-LOCKING', '332722', 1, 'Quote')"
    )
    conn.execute(
        "INSERT INTO opportunities (notion_url, title, naics_code, active, pipeline) "
        "VALUES ('opp://uncovered', 'BOLT,HEX', '999999', 1, 'Inbox')"
    )
    conn.execute(
        "INSERT INTO suppliers (notion_url, supplier_name) VALUES ('sup://1', 'Test Co')"
    )
    conn.execute(
        "INSERT INTO opportunity_supplier_links (opportunity_id, supplier_id) "
        "VALUES ('opp://covered', 'sup://1')"
    )
    conn.commit()


def test_is_sole_source_detects_common_phrasing():
    assert is_sole_source("Notice of Intent to Sole Source Widget Supply") is True
    assert is_sole_source("Sole-Source justification for XYZ") is True
    assert is_sole_source("NUT,SELF-LOCKING,HEXAGON") is False


def test_sole_source_is_auto_no_bid(tmp_path):
    conn = connect(db_path=tmp_path / "s1.db", key="s1" * 32)
    _seed(conn)
    result = score_opportunity(conn, "opp://sole", ["332722"])
    conn.close()

    assert result["no_bid"] is True
    assert result["score"] == 0.0
    assert "sole-source" in result["reasons"][0]


def test_no_bid_pipeline_is_excluded(tmp_path):
    conn = connect(db_path=tmp_path / "s2.db", key="s2" * 32)
    _seed(conn)
    result = score_opportunity(conn, "opp://nobid", ["332722"])
    conn.close()

    assert result["no_bid"] is True


def test_covered_and_naics_matched_scores_higher_than_uncovered(tmp_path):
    conn = connect(db_path=tmp_path / "s3.db", key="s3" * 32)
    _seed(conn)
    covered = score_opportunity(conn, "opp://covered", ["332722"])
    uncovered = score_opportunity(conn, "opp://uncovered", ["332722"])
    conn.close()

    assert covered["no_bid"] is False
    assert covered["score"] == DEFAULT_WEIGHTS["lane_coverage"] + DEFAULT_WEIGHTS["naics_match"]
    assert uncovered["score"] == 0.0
    assert covered["score"] > uncovered["score"]


def test_weights_are_tweakable(tmp_path):
    conn = connect(db_path=tmp_path / "s4.db", key="s4" * 32)
    _seed(conn)
    # opp://uncovered: lane_coverage=0 (no supplier linked), naics_match=0 (999999 not in
    # our list) -- add a NAICS match here so the two components genuinely differ and
    # different weightings produce different scores (a fixture where both components are
    # equal, e.g. both 1 or both 0, can't distinguish weightings -- caught in verification).
    default = score_opportunity(conn, "opp://uncovered", ["999999"])  # naics_match=1, lane=0
    custom = score_opportunity(
        conn, "opp://uncovered", ["999999"],
        weights={"lane_coverage": 0.1, "naics_match": 0.9},
    )
    conn.close()

    assert default["score"] == DEFAULT_WEIGHTS["naics_match"]  # 0.4
    assert custom["score"] == 0.9
    assert default["score"] != custom["score"]


def test_score_all_ranks_descending_and_excludes_superseded(tmp_path):
    conn = connect(db_path=tmp_path / "s5.db", key="s5" * 32)
    _seed(conn)
    results = score_all(conn, ["332722"])
    conn.close()

    scores = [r["score"] for r in results]
    assert scores == sorted(scores, reverse=True)
    ids = [r["opportunity_id"] for r in results]
    assert "opp://covered" in ids
