-- Ferrum Nexus schema v1 (Phase 0). SQLCipher-encrypted at rest.

CREATE TABLE IF NOT EXISTS opportunities (
    notion_url TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    product_type TEXT,
    pipeline TEXT,
    active INTEGER NOT NULL DEFAULT 1,
    supplier_coverage_status TEXT,
    naics_code TEXT,
    -- [0.6 resolver] Phase 2 (/fn-specs) keys work by solicitation_number
    -- (parsed from title today); Phase 3 (/fn-pull) will upsert by notice_id.
    -- Both are stored so either lookup path resolves to the same row.
    solicitation_number TEXT,
    notice_id TEXT,
    -- [3.2 amendment churn] SAM.gov's search endpoint always returns only the
    -- latest active version of a notice under a given noticeId. To "keep
    -- history" (packet 3.2) rather than silently overwriting an amended
    -- notice, /fn-pull inserts amendments as NEW rows and points the prior
    -- row's superseded_by at the new one instead of mutating it in place.
    -- The "current" row for a noticeId is the one with superseded_by IS NULL.
    notice_updated_at TEXT,
    superseded_by TEXT REFERENCES opportunities (notion_url)
);

CREATE TABLE IF NOT EXISTS suppliers (
    notion_url TEXT PRIMARY KEY,
    supplier_name TEXT NOT NULL,
    categories TEXT,
    status TEXT,
    email TEXT,
    keywords TEXT,
    naics TEXT,
    supplier_type TEXT
);

CREATE TABLE IF NOT EXISTS co_clusters (
    cluster_name TEXT PRIMARY KEY,
    agency TEXT,
    item_count INTEGER,
    deadline_window TEXT,
    notes TEXT
);

-- Opportunity <-> Supplier links. Seeded from the Notion "Supplier Outreach
-- Control" junction table (see seed/links.csv); real linkage will later come
-- from /fn-pull + attachment parsing (Phase 3) resolving manufacturer CAGE
-- per line item. Until then, a supplier link stands in for "we have a
-- sourcing path to this opportunity through this company."
CREATE TABLE IF NOT EXISTS opportunity_supplier_links (
    opportunity_id TEXT NOT NULL,
    supplier_id TEXT NOT NULL,
    PRIMARY KEY (opportunity_id, supplier_id),
    FOREIGN KEY (opportunity_id) REFERENCES opportunities (notion_url),
    FOREIGN KEY (supplier_id) REFERENCES suppliers (notion_url)
);

CREATE TABLE IF NOT EXISTS blockers (
    blocker_key TEXT PRIMARY KEY,
    description TEXT NOT NULL,
    owner TEXT NOT NULL,
    next_action TEXT NOT NULL,
    due_date TEXT,
    status TEXT NOT NULL DEFAULT 'open',
    depends_on TEXT
);

CREATE TABLE IF NOT EXISTS adls (
    adl_key TEXT PRIMARY KEY,
    oem_or_manufacturer TEXT NOT NULL,
    cage_code TEXT,
    status TEXT NOT NULL DEFAULT 'requested',
    requested_at TEXT,
    received_at TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS onboarding_docs (
    doc_key TEXT PRIMARY KEY,
    counterparty TEXT NOT NULL,
    doc_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'missing',
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS past_performance (
    ppq_key TEXT PRIMARY KEY,
    customer_or_reference TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'not_requested',
    notes TEXT
);

CREATE TABLE IF NOT EXISTS attachments (
    attachment_key TEXT PRIMARY KEY,
    opportunity_id TEXT,
    notice_id TEXT,
    notice_version TEXT,
    notice_updated_at TEXT,
    solicitation_number TEXT,
    filename TEXT,
    resource_id TEXT,
    mime_type TEXT,
    size INTEGER,
    sha256 TEXT,
    etag TEXT,
    source_url TEXT,
    access_level TEXT,
    explicit_access INTEGER,
    retrieved_via TEXT,
    download_status TEXT,
    access_request_status TEXT,
    superseded_by TEXT,
    line_item_ref TEXT,
    local_path TEXT,
    parse_status TEXT,
    pulled_at TEXT,
    parsed_at TEXT,
    FOREIGN KEY (opportunity_id) REFERENCES opportunities (notion_url)
);

-- [Phase 2] Persists the attested output of /fn-specs across command
-- invocations, keyed by solicitation_number (the id_resolver's Phase-2 key),
-- so /fn-quote can load it without re-parsing the PDF. Not in the original
-- packet's table list -- added because /fn-quote genuinely needs somewhere
-- to read attested specs from between separate script runs.
CREATE TABLE IF NOT EXISTS attested_specs (
    solicitation_number TEXT NOT NULL,
    field TEXT NOT NULL,
    value TEXT,
    page INTEGER,
    confidence TEXT,
    attested INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (solicitation_number, field)
);

-- [3.4] Access log for controlled/CUI attachments once manually imported.
-- DFARS 252.204-7012 obligations attach to controlled NAVSUP/DLA drawings;
-- this is the "who imported what, and when" trail plan section 7A calls for.
CREATE TABLE IF NOT EXISTS cui_access_log (
    log_key TEXT PRIMARY KEY,
    attachment_key TEXT NOT NULL,
    action TEXT NOT NULL,
    actor TEXT NOT NULL,
    at TEXT NOT NULL,
    note TEXT,
    FOREIGN KEY (attachment_key) REFERENCES attachments (attachment_key)
);

-- [Market intel] FPDS historical contract-award records -- these are
-- ALREADY-AWARDED contracts pulled as competitor/market intelligence, not
-- opportunities to bid on. Seeded from the live "FPDS Ferrum Relevant Awards
-- -- Fast Intel" Notion data source.
CREATE TABLE IF NOT EXISTS awards (
    notion_url TEXT PRIMARY KEY,
    award_id TEXT,
    vendor TEXT,
    cage_code TEXT,
    uei TEXT,
    agency TEXT,
    office TEXT,
    psc TEXT,
    psc_description TEXT,
    naics_code TEXT,
    naics_description TEXT,
    set_aside TEXT,
    value_used REAL,
    fiscal_year INTEGER,
    action_date TEXT,
    description TEXT,
    ferrum_score REAL
);

-- Curated lane/agency/vendor intelligence notes derived from the FPDS award
-- pull -- patterns worth tracking, not 1:1 award records (see `awards`).
CREATE TABLE IF NOT EXISTS market_intel (
    notion_url TEXT PRIMARY KEY,
    intel_item TEXT NOT NULL,
    category TEXT,
    priority TEXT,
    value_sum REAL,
    why_it_matters TEXT,
    next_step TEXT
);

CREATE TABLE IF NOT EXISTS quotes (
    quote_key TEXT PRIMARY KEY,
    solicitation_number TEXT NOT NULL,
    supplier_key TEXT,
    unit_price REAL,
    total_price REAL,
    ptat TEXT,
    fob TEXT,
    cage_code TEXT,
    coc_on_file INTEGER DEFAULT 0,
    mtr_on_file INTEGER DEFAULT 0,
    adl_on_file INTEGER DEFAULT 0,
    created_at TEXT,
    FOREIGN KEY (supplier_key) REFERENCES suppliers (notion_url)
);
