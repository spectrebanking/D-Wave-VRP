---
description: Pull opportunities + attachments from SAM.gov (needs a real API key + SAM active)
---

Requires a real SAM.gov API key on file (`/fn-setup`) and SAM.gov entity activation --
until then this is fixture-tested only (see `scripts/demo_phase3.py`).

```python
from scripts.credentials import get_sam_api_key
from scripts.sam_client import SamClient
from scripts.pull import pull_page
from scripts.attachments import detect_resources, ingest_attachments

client = SamClient(api_key=get_sam_api_key())
for page in client.search_all_pages(posted_from="07/01/2025", posted_to="07/01/2026"):
    counts = pull_page(conn, page)   # dedups by noticeId, supersedes amended notices
    print(counts)

    for notice in page["opportunitiesData"]:
        resources_resp = client.get_resources(notice["noticeId"])
        resources = detect_resources(notice, resources_resp)
        ingest_attachments(conn, opportunity_id, notice["noticeId"],
                            solicitation_number, resources)
```

Every detected attachment gets recorded regardless of outcome: public files are downloaded +
hashed, controlled/CUI files are routed to `access_required` (never fabricated, never dropped).
One failed download never stalls the rest of the opportunity's attachments.
