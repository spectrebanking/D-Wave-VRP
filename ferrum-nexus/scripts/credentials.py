"""Encrypted local secret storage (SAM.gov API key, DB encryption key).

Key-recovery note (surfaced to the user by /fn-doctor and /fn-setup): the DB
encryption key lives at data/.dbkey, file-permission 0600, gitignored. It is
NOT derivable from a password — if data/.dbkey is lost, data/ferrum_nexus.db
cannot be decrypted and must be rebuilt from the seed/ CSVs + re-entered
config. Back up data/.dbkey somewhere outside this repo (a password manager
or offline copy) the same day /fn-setup generates it.
"""
import os
import stat
import secrets
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_KEY_PATH = DATA_DIR / ".dbkey"
SAM_KEY_PATH = DATA_DIR / ".sam_api_key"


def _write_locked(path: Path, content: str) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    path.write_text(content, encoding="utf-8")
    os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)  # 0600


def get_or_create_db_key() -> str:
    """Return the SQLCipher passphrase, generating + persisting one on first run."""
    if DB_KEY_PATH.exists():
        return DB_KEY_PATH.read_text(encoding="utf-8").strip()
    key = secrets.token_hex(32)
    _write_locked(DB_KEY_PATH, key)
    return key


def store_sam_api_key(api_key: str) -> None:
    _write_locked(SAM_KEY_PATH, api_key.strip())


def get_sam_api_key() -> str | None:
    if not SAM_KEY_PATH.exists():
        return None
    return SAM_KEY_PATH.read_text(encoding="utf-8").strip()


def has_sam_api_key() -> bool:
    return SAM_KEY_PATH.exists() and bool(get_sam_api_key())
