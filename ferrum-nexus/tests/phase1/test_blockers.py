import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from db import connect  # noqa: E402
from blockers import (  # noqa: E402
    seed_blockers, list_blockers, critical_path_order, next_action_now,
)


def test_every_blocker_has_owner_next_action_due_date(tmp_path):
    conn = connect(db_path=tmp_path / "b.db", key="1" * 64)
    seed_blockers(conn)
    blockers = list_blockers(conn)
    conn.close()

    assert len(blockers) > 0
    for b in blockers:
        assert b["owner"], f"{b['blocker_key']} has no owner"
        assert b["next_action"], f"{b['blocker_key']} has no next_action"
        assert b["due_date"], f"{b['blocker_key']} has no due_date"


def test_sam_activation_is_root_of_critical_path(tmp_path):
    conn = connect(db_path=tmp_path / "b2.db", key="2" * 64)
    seed_blockers(conn)
    blockers = list_blockers(conn)
    conn.close()

    ordered = critical_path_order(blockers)
    assert ordered[0]["blocker_key"] == "sam_activation"


def test_next_action_is_sam_activation_when_all_open(tmp_path):
    conn = connect(db_path=tmp_path / "b3.db", key="3" * 64)
    seed_blockers(conn)
    blockers = list_blockers(conn)
    conn.close()

    nxt = next_action_now(blockers)
    assert nxt["blocker_key"] == "sam_activation"


def test_next_action_advances_once_sam_activation_closed(tmp_path):
    conn = connect(db_path=tmp_path / "b4.db", key="4" * 64)
    seed_blockers(conn)
    conn.execute("UPDATE blockers SET status='done' WHERE blocker_key='sam_activation'")
    conn.commit()
    blockers = list_blockers(conn)
    conn.close()

    nxt = next_action_now(blockers)
    assert nxt["blocker_key"] != "sam_activation"
    assert nxt["depends_on"] == "sam_activation"
