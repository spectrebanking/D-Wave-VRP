# Curated lane/agency/vendor intelligence notes, pulled from the live "FPDS
# Ferrum Intelligence Summary" Notion data source
# (collection://e9c2ab43-bfb3-4623-a551-b64209bcbd6c), 2026-07-05. Each row is
# an analyst note about a pattern in the FPDS award pull (see
# scripts/_seed_awards.py for the raw award rows it was derived from), not a
# 1:1 award record.
# Columns: notion_url, intel_item, category, priority, value_sum,
#          why_it_matters, next_step
MARKET_INTEL = [
    ("https://app.notion.com/394ed5bb5bca810ab979e9310469c162", "9535 — Plate, Sheet, Strip, and Foil; Nonferrous Base Metal", "PSC", "P0 Review Now", 39500460000, "Clean metals lane. Fits Ferrum sourcing better than broad services. Use for supplier matching with Ryerson, TW Metals, Continental Steel, Aalco-style suppliers.", "Pull top vendors and offices under PSC 9535, then match against live SAM opportunities and supplier quote sources."),
    ("https://app.notion.com/394ed5bb5bca8112853cd04511b138b8", "2031JG24F00379 — U.S. Mint Die Steel Contract", "Lane", "P0 Review Now", 246600, "Second U.S. Mint steel signal. Repetition means this office/lane deserves monitoring.", "Add U.S. Mint steel purchases to pursuit watchlist."),
    ("https://app.notion.com/394ed5bb5bca811b9ffff91b7be25cc8", "J047 — Maint/Repair/Rebuild: Pipe, Tubing, Hose, and Fittings", "PSC", "P0 Review Now", 247292, "Direct pipe/fittings lane. This is closer to Ferrum's supplier matrix than broad facilities work.", "Pull buying office, vendor, and item description; match pipe/fitting suppliers."),
    ("https://app.notion.com/394ed5bb5bca81218467e6a613ef0de8", "140L1225C0001 — Pipe/Tubing/Hose/Fittings Water System", "Lane", "P0 Review Now", 247292, "Pipe/fittings lane with Interior/BLM. May include service work, but item category is aligned enough to review.", "Separate supply component from construction/service component before pursuing."),
    ("https://app.notion.com/394ed5bb5bca8174a356dfe20d209e7b", "J059 — Maint/Repair/Rebuild: Electrical and Electronic Equipment Components", "PSC", "P0 Review Now", 1361721000, "Hardware-adjacent repair/component lane. Can become RFQ targeting if line items are parts/equipment instead of labor-heavy service.", "Filter records for parts/product descriptions and remove service-only maintenance."),
    ("https://app.notion.com/394ed5bb5bca81abadd2e315ba829768", "Department of the Treasury | US MINT HEADQUARTERS", "Buying Office", "P0 Review Now", 493200, "Concrete buying office with repeated steel/material award signal. Better than generic mega-agency data.", "Create office watch query for Mint + steel + bars + rods + die steel + PSC 9510/9640."),
    ("https://app.notion.com/394ed5bb5bca81b4a290d9424dd4ee63", "DUNKIRK SPECIALTY STEEL LLC", "Vendor", "P1 Good", 493200, "Known winner in steel/die product awards. Useful as competitor/supplier intelligence.", "Research whether they sell through distributor channels or if Ferrum should avoid competing on source-controlled material."),
    ("https://app.notion.com/394ed5bb5bca81cb8a04f70f90554a5b", "2031JG24F00429 — U.S. Mint L6 Die Steel", "Lane", "P0 Review Now", 246600, "Clean product example: steel bars/rods, known buyer, known vendor, clear material lane.", "Find recurring U.S. Mint steel/die/tooling buys and match supplier quotes."),
    ("https://app.notion.com/394ed5bb5bca81df8ceef479135bfa3e", "9640 — Iron and Steel Primary and Semifinished Products", "PSC", "P0 Review Now", 246600, "Direct steel product lane. Clean Ferrum fit when specs, grade, dimensions, and delivery are clear.", "Build repeat-buy watchlist for U.S. Mint and similar offices."),
    ("https://app.notion.com/394ed5bb5bca81ec82ffcc410bcebfe9", "9510 — Bars and Rods", "PSC", "P0 Review Now", 246600, "Direct metals lane. Example surfaced: U.S. Mint L6 die steel. This is a clean product/material sourcing target.", "Use metals supplier matrix and search live opportunities for 9510/BARS/RODS/DIE STEEL."),
]
