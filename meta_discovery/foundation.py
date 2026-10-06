"""Recheck identifiers in the fixed July evidence without contacting any API."""

from collections import Counter
import csv
from datetime import date
import hashlib
from pathlib import Path
import re


FILES = {
    "orders": "shopify/orders/orders_2026-07-01_to_2026-07-07.csv",
    "lines": "shopify/orders/order_lines_2026-07-01_to_2026-07-07.csv",
    "events": "ga4/purchase_events_2026-07-01_to_2026-07-07.txt",
    "items": "ga4/purchase_items_2026-07-01_to_2026-07-07.txt",
}
DATED_ROW = re.compile(r"^\d{4}-\d{2}-\d{2}\s")
EVENT_ROW = re.compile(r"^(\d{4}-\d{2}-\d{2})\s+(\d+)\s+\d+(?:\.\d+)?\s+-?\d+(?:\.\d+)?\s*$")
ITEM_ROW = re.compile(
    r"^(\d{4}-\d{2}-\d{2})\s+(\d+)\s+.+?\s+"
    r"shopify_AU_(\d+)_(\d+)\s+.*?\s+(\d+)\s+-?\d+(?:\.\d+)?\s*$"
)


class EvidenceError(ValueError):
    pass


def _parse_rows(text: str, pattern, label: str) -> list:
    rows = []
    for line in text.splitlines():
        if not DATED_ROW.match(line):
            continue
        match = pattern.fullmatch(line)
        if not match:
            raise EvidenceError(f"Malformed dated row in saved {label}; row contents withheld.")
        day = date.fromisoformat(match[1])
        if not date(2026, 7, 1) <= day <= date(2026, 7, 7):
            raise EvidenceError(f"Saved {label} contains dates outside 1–7 July 2026.")
        rows.append(match.groups())
    if not rows:
        raise EvidenceError(f"No data rows found in saved {label}.")
    return rows


def audit_foundation(root: Path) -> dict:
    paths = {key: root / name for key, name in FILES.items()}
    try:
        contents = {key: path.read_bytes() for key, path in paths.items()}
        orders = list(csv.DictReader(contents["orders"].decode().splitlines()))
        lines = list(csv.DictReader(contents["lines"].decode().splitlines()))
        if not orders or not lines or not {"order_id", "source_name"} <= orders[0].keys():
            raise EvidenceError("Saved Shopify orders/lines are empty or lack required columns.")
        events_text = contents["events"].decode()
        events = _parse_rows(events_text, EVENT_ROW, "GA4 purchase events")
        items = _parse_rows(contents["items"].decode(), ITEM_ROW, "GA4 purchase items")
        order_ids = {row["order_id"] for row in orders}
        original_quantities = Counter()
        for row in lines:
            original_quantities[(row["order_id"], row["product_id"], row["variant_id"])] += int(row["quantity"])
    except (OSError, UnicodeError, KeyError, ValueError) as error:
        if isinstance(error, EvidenceError):
            raise
        raise EvidenceError("Saved evidence is missing, unreadable, or has invalid columns/quantities; details withheld.") from None
    event_ids = {row[1] for row in events}
    item_ids = {row[1] for row in items}
    ga4_quantities = Counter()
    for _, order, product, variant, quantity in items:
        ga4_quantities[(order, product, variant)] += int(quantity)
    matched_rows = sum((r[1], r[2], r[3]) in original_quantities for r in items)
    metadata_count = re.search(r"response\.row_count:\s*(\d+)", events_text)
    checks = {
        "unique_shopify_order_ids": bool(orders) and len(order_ids) == len(orders),
        "ga4_events_match_recorded_row_count": metadata_count is not None and int(metadata_count[1]) == len(events),
        "event_and_item_transaction_sets_agree": event_ids == item_ids,
        "all_ga4_transactions_match_shopify_orders": event_ids <= order_ids,
        "all_ga4_item_rows_match_order_product_variant": matched_rows == len(items),
        "original_quantities_match": all(original_quantities[key] == quantity for key, quantity in ga4_quantities.items()),
    }
    web_ids = {row["order_id"] for row in orders if row.get("source_name") == "web"}
    return {
        "status": "passed" if all(checks.values()) else "failed",
        "evidence_kind": "historical saved files; no live Shopify or GA4 requests",
        "property_id": "268350484", "dates": {"since": "2026-07-01", "until": "2026-07-07"},
        "shopify_date_basis": "orders created in Australia/Melbourne",
        "ga4_timezone": "Australia/Sydney" if "response.metadata.time_zone: Australia/Sydney" in events_text else None,
        "item_id_pattern": "shopify_AU_{product_id}_{variant_id}",
        "counts": {"shopify_orders": len(orders), "shopify_lines": len(lines),
                   "ga4_event_rows": len(events), "ga4_transactions": len(event_ids),
                   "matched_transactions": len(event_ids & order_ids), "ga4_item_rows": len(items),
                   "matched_item_rows": matched_rows, "online_store_orders": len(web_ids),
                   "captured_online_store_orders": len(web_ids & event_ids),
                   "absent_online_store_orders": len(web_ids - event_ids)},
        "checks": checks,
        "inputs": [{"path": str(paths[key].resolve()), "sha256": hashlib.sha256(data).hexdigest()}
                   for key, data in contents.items()],
        "limitations": ["Checks only retained July rows, not current Shopify/GA4 access or complete tracking.",
                        "Missing orders are counted; their causes are not investigated.",
                        "No Meta-to-GA4 or Meta-to-Shopify connection is established by Step 1."],
    }
