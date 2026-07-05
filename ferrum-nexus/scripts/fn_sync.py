"""/fn-sync -- the "recursive" re-pull half of recursive learning: one
command that refreshes from every live source that has credentials on file
(Notion opportunities/suppliers/links, SAM.gov opportunities over a rolling
date window). Designed to run unattended on a schedule (cron, launchd, Task
Scheduler, or a Claude Code Remote trigger) -- each source is independently
skipped with a clear message if its credential isn't on file, so a partial
credential set never blocks the other source, and re-running is always safe
(every upsert path underneath is idempotent).

See RUNBOOK.md for a sample cron line.
"""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import credentials  # noqa: E402
from db import connect  # noqa: E402


def sync_notion(conn) -> dict | None:
    token = credentials.get_notion_token()
    if not token:
        print("skip: no Notion integration token on file (see /fn-setup)")
        return None
    from notion_client import NotionClient
    from notion_sync import sync_all

    return sync_all(conn, NotionClient(token=token))


def sync_sam(conn, window_days: int = 30) -> dict | None:
    api_key = credentials.get_sam_api_key()
    if not api_key:
        print("skip: no SAM.gov API key on file (see /fn-setup)")
        return None
    from sam_client import SamClient
    import pull

    today = datetime.now(timezone.utc).date()
    posted_from = (today - timedelta(days=window_days)).strftime("%m/%d/%Y")
    posted_to = today.strftime("%m/%d/%Y")

    client = SamClient(api_key=api_key)
    totals = {"inserted": 0, "unchanged": 0, "superseded": 0}
    for page in client.search_all_pages(posted_from, posted_to):
        page_counts = pull.pull_page(conn, page)
        for k, v in page_counts.items():
            totals[k] += v
    return totals


def main() -> int:
    conn = connect()
    notion_counts = sync_notion(conn)
    if notion_counts is not None:
        print(f"Notion sync: {notion_counts}")

    sam_counts = sync_sam(conn)
    if sam_counts is not None:
        print(f"SAM.gov pull: {sam_counts}")
    conn.close()

    if notion_counts is None and sam_counts is None:
        print("Nothing synced -- no live credentials on file yet. Run /fn-setup.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
