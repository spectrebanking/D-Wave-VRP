import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import docs  # noqa: E402


def test_generate_all_writes_five_docs_with_entity_fields(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    config_path = data_dir / "config.json"
    config_path.write_text(
        '{"legal_name": "Apollo Credit Processing LLC", "dba": "Ferrum Nexus", '
        '"naics_codes": ["332722"], "uei": null, "cage_code": null}',
        encoding="utf-8",
    )

    monkeypatch.setattr(docs, "DATA_DIR", data_dir)
    monkeypatch.setattr(docs, "CONFIG_PATH", config_path)
    monkeypatch.setattr(docs, "OUT_DIR", data_dir / "generated_docs")

    written = docs.generate_all()

    assert set(written.keys()) == {
        "w9-checklist.md", "capabilities-statement.md", "letterhead.md",
        "quote-template.md", "cover-email-template.md",
    }
    for path in written.values():
        assert path.exists()
        content = path.read_text(encoding="utf-8")
        assert "Apollo Credit Processing LLC" in content
        assert "Ferrum Nexus" in content

    # The W-9 output must never claim to be the real signed form.
    w9_content = written["w9-checklist.md"].read_text(encoding="utf-8")
    assert "not a W-9" in w9_content or "not generated here" in w9_content


def test_generate_all_requires_setup_first(tmp_path, monkeypatch):
    data_dir = tmp_path / "empty_data"
    data_dir.mkdir()
    monkeypatch.setattr(docs, "DATA_DIR", data_dir)
    monkeypatch.setattr(docs, "CONFIG_PATH", data_dir / "config.json")
    monkeypatch.setattr(docs, "OUT_DIR", data_dir / "generated_docs")

    try:
        docs.generate_all()
        assert False, "expected FileNotFoundError when config.json is missing"
    except FileNotFoundError:
        pass
