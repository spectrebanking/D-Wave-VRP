"""0.2 — /fn-setup guided flow: entity config + SAM.gov API key + encrypted store init."""
import json
import sys
from pathlib import Path

import credentials
from db import connect
from seed import load_all
from blockers import seed_blockers

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CONFIG_PATH = DATA_DIR / "config.json"

DEFAULT_ENTITY = {
    "legal_name": "Apollo Credit Processing LLC",
    "dba": "Ferrum Nexus",
    "naics_codes": ["332722", "423510", "332919"],
    "uei": None,
    "cage_code": None,
}


def load_config() -> dict:
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return dict(DEFAULT_ENTITY)


def save_config(config: dict) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(config, indent=2), encoding="utf-8")


def validate_sam_key_live(api_key: str) -> bool:
    """Make one live call against the SAM.gov Opportunities API to confirm the key works.

    Only invoked when a real key is supplied interactively (see run_interactive).
    Network/API-shape details are intentionally minimal here -- full client
    lands in Phase 3 (scripts/sam_client.py); this is just a yes/no smoke check.
    """
    import urllib.request
    import urllib.parse

    params = urllib.parse.urlencode({
        "api_key": api_key,
        "postedFrom": "01/01/2026",
        "postedTo": "01/02/2026",
        "limit": 1,
    })
    url = f"https://api.sam.gov/opportunities/v2/search?{params}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.status == 200


def validate_notion_token_live(token: str) -> bool:
    """One live call to confirm a Notion integration token works. Same posture
    as validate_sam_key_live: only invoked when a real token is supplied
    interactively."""
    import urllib.request

    req = urllib.request.Request(
        "https://api.notion.com/v1/users/me",
        headers={"Authorization": f"Bearer {token}", "Notion-Version": "2025-09-03"},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.status == 200


def run_interactive() -> None:
    """The real guided flow. Not exercised by automated tests (no human present)."""
    print("Ferrum Nexus setup")
    config = load_config()

    entity_name = input(f"Legal entity name [{config['legal_name']}]: ").strip()
    if entity_name:
        config["legal_name"] = entity_name

    api_key = input("SAM.gov API key (get one free at sam.gov > Account Details > API Key): ").strip()
    if api_key:
        try:
            ok = validate_sam_key_live(api_key)
        except Exception as exc:  # noqa: BLE001 - surface any failure to the user plainly
            print(f"Could not validate key against SAM.gov live API: {exc}")
            ok = False
        if ok:
            credentials.store_sam_api_key(api_key)
            print("SAM.gov API key stored and validated.")
        else:
            print("Key did not validate; not stored. You can re-run /fn-setup once SAM is active.")

    notion_token = input(
        "Notion integration token (optional, for live /fn-sync -- Enter to skip): "
    ).strip()
    if notion_token:
        try:
            ok = validate_notion_token_live(notion_token)
        except Exception as exc:  # noqa: BLE001 - surface any failure to the user plainly
            print(f"Could not validate token against Notion's live API: {exc}")
            ok = False
        if ok:
            credentials.store_notion_token(notion_token)
            print("Notion integration token stored and validated.")
        else:
            print("Token did not validate; not stored.")

    save_config(config)
    conn = connect()
    counts = load_all(conn)
    counts["blockers"] = seed_blockers(conn)
    conn.close()
    print(f"Store seeded: {counts}")
    print("Setup complete. Run /fn-doctor to confirm.")


def run_noninteractive_for_tests(entity: dict | None = None) -> dict:
    """Non-interactive path used by tests: writes config + seeds the store, no network call."""
    config = dict(DEFAULT_ENTITY)
    if entity:
        config.update(entity)
    save_config(config)
    conn = connect()
    counts = load_all(conn)
    counts["blockers"] = seed_blockers(conn)
    conn.close()
    return counts


if __name__ == "__main__":
    if "--for-tests" in sys.argv:
        print(run_noninteractive_for_tests())
    else:
        run_interactive()
