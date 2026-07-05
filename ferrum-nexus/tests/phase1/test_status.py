import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from db import connect  # noqa: E402
from blockers import seed_blockers  # noqa: E402
from seed import load_all  # noqa: E402
import status  # noqa: E402


def test_status_renders_critical_path_with_sam_at_node_zero(tmp_path):
    conn = connect(db_path=tmp_path / "s.db", key="9" * 64)
    load_all(conn)
    seed_blockers(conn)

    output = status.render(conn)
    conn.close()

    lines = output.splitlines()
    critical_path_idx = next(i for i, line in enumerate(lines) if line.startswith("Critical path"))
    assert "sam_activation" in lines[critical_path_idx + 1]
    assert "NEXT ACTION:" in output
    assert "Opportunity pipeline:" in output
