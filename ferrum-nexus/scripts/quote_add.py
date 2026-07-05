"""[2.2a consensus fix] /fn-quote-add <sol#> -- supplier-quote intake.

/fn-quote (2.2) is blocked without a quote row on file for the solicitation;
this is how one gets there.
"""
from datetime import datetime, timezone


def add_quote(
    conn,
    solicitation_number: str,
    supplier_key: str,
    unit_price: float | None = None,
    total_price: float | None = None,
    ptat: str | None = None,
    fob: str | None = None,
    cage_code: str | None = None,
    coc_on_file: bool = False,
    mtr_on_file: bool = False,
    adl_on_file: bool = False,
) -> str:
    supplier_row = conn.execute(
        "SELECT notion_url FROM suppliers WHERE notion_url = ?", (supplier_key,)
    ).fetchone()
    if supplier_row is None:
        raise ValueError(f"unknown supplier_key: {supplier_key}")

    quote_key = f"{solicitation_number}::{supplier_key}"
    conn.execute(
        """INSERT INTO quotes
           (quote_key, solicitation_number, supplier_key, unit_price, total_price,
            ptat, fob, cage_code, coc_on_file, mtr_on_file, adl_on_file, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(quote_key) DO UPDATE SET
             unit_price=excluded.unit_price, total_price=excluded.total_price,
             ptat=excluded.ptat, fob=excluded.fob, cage_code=excluded.cage_code,
             coc_on_file=excluded.coc_on_file, mtr_on_file=excluded.mtr_on_file,
             adl_on_file=excluded.adl_on_file""",
        (
            quote_key, solicitation_number, supplier_key, unit_price, total_price,
            ptat, fob, cage_code, int(coc_on_file), int(mtr_on_file), int(adl_on_file),
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    conn.commit()
    return quote_key


def get_quotes_for_solicitation(conn, solicitation_number: str) -> list[dict]:
    rows = conn.execute(
        """SELECT quote_key, supplier_key, unit_price, total_price, ptat, fob,
                  cage_code, coc_on_file, mtr_on_file, adl_on_file, created_at
           FROM quotes WHERE solicitation_number = ?""",
        (solicitation_number,),
    ).fetchall()
    cols = ["quote_key", "supplier_key", "unit_price", "total_price", "ptat", "fob",
            "cage_code", "coc_on_file", "mtr_on_file", "adl_on_file", "created_at"]
    return [dict(zip(cols, r)) for r in rows]
