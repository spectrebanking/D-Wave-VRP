import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))


def test_doctor_green_after_setup(tmp_path, monkeypatch):
    # Point every module at an isolated data/ dir so this test never touches
    # the real local store.
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    import credentials
    import db
    import doctor

    monkeypatch.setattr(credentials, "DATA_DIR", data_dir)
    monkeypatch.setattr(credentials, "DB_KEY_PATH", data_dir / ".dbkey")
    monkeypatch.setattr(credentials, "SAM_KEY_PATH", data_dir / ".sam_api_key")
    monkeypatch.setattr(credentials, "NOTION_TOKEN_PATH", data_dir / ".notion_token")
    monkeypatch.setattr(db, "DATA_DIR", data_dir)
    monkeypatch.setattr(db, "DB_PATH", data_dir / "ferrum_nexus.db")

    import setup as setup_mod
    monkeypatch.setattr(setup_mod, "DATA_DIR", data_dir)
    monkeypatch.setattr(setup_mod, "CONFIG_PATH", data_dir / "config.json")

    setup_mod.run_noninteractive_for_tests()
    results = doctor.check()

    assert results["store_reachable"] is True
    assert results["schema_ok"] is True
    assert results["db_key_present"] is True
    assert all(v > 0 for v in results["counts"].values())
    assert results["green"] is True


def test_doctor_red_when_no_data_dir(tmp_path, monkeypatch):
    data_dir = tmp_path / "never_seeded"

    import credentials
    import db
    import doctor

    monkeypatch.setattr(credentials, "DATA_DIR", data_dir)
    monkeypatch.setattr(credentials, "DB_KEY_PATH", data_dir / ".dbkey")
    monkeypatch.setattr(credentials, "SAM_KEY_PATH", data_dir / ".sam_api_key")
    monkeypatch.setattr(credentials, "NOTION_TOKEN_PATH", data_dir / ".notion_token")
    monkeypatch.setattr(db, "DATA_DIR", data_dir)
    monkeypatch.setattr(db, "DB_PATH", data_dir / "ferrum_nexus.db")

    results = doctor.check()
    # store gets created on first connect() even with no prior seed, so it's
    # reachable + schema_ok, but counts must be zero -> not green.
    assert results["counts"] == {
        "opportunities": 0, "suppliers": 0, "co_clusters": 0, "opportunity_supplier_links": 0,
    }
    assert results["green"] is False
