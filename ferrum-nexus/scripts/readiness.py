"""2.3 -- Readiness Assessment: factual completeness only, never a verdict.

Tiers:
  BLOCKED               -- a hard prerequisite is missing (specs not attested,
                           no supplier quote on file, no ADL for the quoting
                           supplier). Lists what's missing + who provides it.
  NOT_YET_REVIEWED      -- all factual-completeness checks pass, but a forced
                           per-item checklist is returned. This REPLACES any
                           "READY" label -- ticking every box is still a human
                           judgment call, never the tool's.

Every assessment carries the rule set's UNVERIFIED banner and version stamp
(rules/readiness_rules_v0.yaml) -- see plan section 6 + section 11's hard
SME sign-off gate. This module asserts factual presence only, never legal
responsiveness.
"""
from pathlib import Path

import yaml

from specs_store import load_extraction
from attest import is_fully_attested
from quote_add import get_quotes_for_solicitation

RULES_PATH = Path(__file__).resolve().parent.parent / "rules" / "readiness_rules_v0.yaml"


def load_rules() -> dict:
    raw = yaml.safe_load(RULES_PATH.read_text(encoding="utf-8"))
    # forced_checklist is a list of single-key {key: description} dicts in the
    # YAML (readable to a reviewing SME); flatten to (key, description) pairs.
    checklist = [(k, v) for item in raw["forced_checklist"] for k, v in item.items()]
    return {
        "version": raw["version"],
        "verified": raw["verified"],
        "banner": raw["banner"].strip(),
        "forced_checklist": checklist,
    }


def assess(conn, solicitation_number: str) -> dict:
    rules = load_rules()
    reasons = []

    extraction = load_extraction(conn, solicitation_number)
    if extraction["status"] != "extracted" or not is_fully_attested(extraction):
        reasons.append(
            "specs not fully attested -- run /fn-specs then attest every field "
            "before a quote can be assessed"
        )

    quotes = get_quotes_for_solicitation(conn, solicitation_number)
    if not quotes:
        reasons.append("no supplier quote on file -- run /fn-quote-add first")

    if quotes and not any(q["adl_on_file"] for q in quotes):
        reasons.append(
            "no Authorized Distributor Letter on file for any quoting supplier "
            "-- NAVSUP will not accept a reseller quote without one"
        )

    tier = "BLOCKED" if reasons else "NOT_YET_REVIEWED"

    return {
        "solicitation_number": solicitation_number,
        "tier": tier,
        "reasons": reasons,
        "forced_checklist": rules["forced_checklist"] if tier == "NOT_YET_REVIEWED" else [],
        "banner": rules["banner"],
        "rule_version": rules["version"],
        "rule_verified": rules["verified"],
    }


def render(assessment: dict) -> str:
    lines = [
        f"Readiness Assessment -- Sol# {assessment['solicitation_number']}",
        f"[{assessment['banner']}] (rule set {assessment['rule_version']}, "
        f"verified={assessment['rule_verified']})",
        f"TIER: {assessment['tier']}",
    ]
    if assessment["tier"] == "BLOCKED":
        lines.append("Missing:")
        for r in assessment["reasons"]:
            lines.append(f"  - {r}")
    else:
        lines.append("Factual completeness checks passed. You must still verify, by hand:")
        for key, desc in assessment["forced_checklist"]:
            lines.append(f"  [ ] {key}: {desc}")
    lines.append("Decision-support only; the human is responsible; the solicitation controls.")
    return "\n".join(lines)
