"""0.5 — /fn-doctor: health check (store reachable, key present, seed counts, deps)."""
import sys

from db import connect, table_names
import credentials

REQUIRED_TABLES = {
    "opportunities", "suppliers", "co_clusters", "opportunity_supplier_links",
    "blockers", "adls", "onboarding_docs", "past_performance", "attachments",
    "attested_specs", "quotes", "cui_access_log",
}


def check() -> dict:
    results = {}

    try:
        conn = connect()
        results["store_reachable"] = True
    except Exception as exc:  # noqa: BLE001
        results["store_reachable"] = False
        results["store_error"] = str(exc)
        return results

    present = table_names(conn)
    results["schema_ok"] = REQUIRED_TABLES.issubset(present)
    results["missing_tables"] = sorted(REQUIRED_TABLES - present)

    results["counts"] = {
        "opportunities": conn.execute("SELECT COUNT(*) FROM opportunities").fetchone()[0],
        "suppliers": conn.execute("SELECT COUNT(*) FROM suppliers").fetchone()[0],
        "co_clusters": conn.execute("SELECT COUNT(*) FROM co_clusters").fetchone()[0],
        "opportunity_supplier_links": conn.execute(
            "SELECT COUNT(*) FROM opportunity_supplier_links").fetchone()[0],
    }
    conn.close()

    results["db_key_present"] = credentials.DB_KEY_PATH.exists()
    results["sam_api_key_present"] = credentials.has_sam_api_key()

    results["green"] = (
        results["store_reachable"]
        and results["schema_ok"]
        and results["db_key_present"]
        and all(v > 0 for v in results["counts"].values())
    )
    return results


def main() -> int:
    results = check()
    for k, v in results.items():
        print(f"{k}: {v}")
    if not results.get("sam_api_key_present"):
        print("NOTE: no SAM.gov API key on file yet -- run /fn-setup with a real key "
              "before Phase 3 (live SAM pulls). Not required for Phase 0/1.")
    return 0 if results.get("green") else 1


if __name__ == "__main__":
    sys.exit(main())
