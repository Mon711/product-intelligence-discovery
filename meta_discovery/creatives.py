"""Step 3: inspect connection fields from a saved Step 2 sample, without parsing links."""

import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

from meta_discovery.reader import (
    ACCOUNT_ID, CONNECTION_FIELDS, ITEM_FIELDS, JULY_WINDOW,
    MetaFieldUnavailable, MetaObjectUnavailable, MetaReadError,
)
from meta_discovery.sampling import write_json


FIELD_DICTIONARY = {
    "name": ("Current creative name", "Context only; names are not unique identifiers."),
    "status": ("Current creative status", "Current configuration context, not July delivery."),
    "link_url": ("Top-level destination URL", "Possible Shopify product, collection or homepage link."),
    "object_url": ("URL associated with the advertised object", "Another possible destination; inspect its context."),
    "object_story_spec": ("Nested creative story configuration", "May contain links, carousel cards or a call-to-action destination."),
    "asset_feed_spec": ("Nested alternative creative assets", "May contain several possible destination URLs."),
    "url_tags": ("Tracking parameters attached to destination links", "Possible GA4 campaign/source labels; placeholders are preserved."),
    "product_set_id": ("Meta catalogue product-set identifier", "Group reference only; not a Shopify product/variant ID."),
    "template_url": ("Catalogue destination template", "May contain placeholders rather than a delivered product URL."),
    "template_url_spec": ("Nested catalogue URL-template settings", "Possible dynamic destinations; actual delivery is unproven."),
    "campaign_id": ("Current parent campaign identifier", "Checks the saved ad-set relationship."),
    "created_time": ("Object creation timestamp, when returned", "Snapshot context; does not reconstruct July configuration."),
    "updated_time": ("Object update timestamp, when returned", "Signals possible changes since historical delivery."),
    "promoted_object": ("Nested object promoted by the ad set", "May reference a catalogue/product set; a pixel reference is not a product."),
    "id": ("Meta catalogue item identifier", "Not automatically a Shopify identifier."),
    "retailer_id": ("Merchant-supplied catalogue item identifier", "Candidate Shopify product/variant encoding; requires later verification."),
    "retailer_product_group_id": ("Merchant-supplied product group identifier", "Possible product-level connection; requires later verification."),
    "url": ("Catalogue item's destination URL", "Possible explicit product/variant destination."),
    "products": ("Bounded read of the referenced product set", "At most 20 members; membership does not prove what someone saw."),
}


def load_sample(folder: Path) -> dict:
    """Validate saved provenance before loading credentials or making requests."""
    try:
        raw = {name: (folder / name).read_bytes() for name in ("sample.json", "summary.json")}
        sample, summary = (json.loads(raw[name]) for name in ("sample.json", "summary.json"))
        if (summary["stage"] != "sample" or summary["status"] != "passed"
                or summary["meta"]["status"] != "passed"
                or summary["meta"]["account"]["account_id"] != ACCOUNT_ID
                or sample["status"] != "complete" or sample["insights_complete"] is not True
                or sample["dates"] != JULY_WINDOW):
            raise ValueError()
        selected, hierarchy, objects = sample["selected"], sample["hierarchy"], sample["objects"]
        if not isinstance(selected, list) or not isinstance(hierarchy, list) or len(selected) > 15 or len(selected) != len(hierarchy):
            raise ValueError()
        ids = set()
        for row, link in zip(selected, hierarchy):
            if row["account_id"] != ACCOUNT_ID or row["ad_id"] in ids or int(row["impressions"]) <= 0:
                raise ValueError()
            ids.add(row["ad_id"])
            if row["date_start"] != JULY_WINDOW["since"] or row["date_stop"] != JULY_WINDOW["until"] or link["status"] != "complete":
                raise ValueError()
            for key in ("ad_id", "adset_id", "campaign_id"):
                if not isinstance(row[key], str) or not re.fullmatch(r"[0-9]+", row[key]) or row[key] != link[key]:
                    raise ValueError()
            if not isinstance(link["creative_id"], str) or not re.fullmatch(r"[0-9]+", link["creative_id"]):
                raise ValueError()
            for kind, key in (("ad", "ad_id"), ("adset", "adset_id"), ("campaign", "campaign_id")):
                obj = objects[kind][row[key]]
                if obj["status"] != "available" or obj["data"]["id"] != row[key] or obj["data"]["account_id"] != ACCOUNT_ID:
                    raise ValueError()
            ad = objects["ad"][row["ad_id"]]["data"]
            if (ad["creative"]["id"] != link["creative_id"] or ad["adset_id"] != row["adset_id"]
                    or ad["campaign_id"] != row["campaign_id"]
                    or objects["adset"][row["adset_id"]]["data"]["campaign_id"] != row["campaign_id"]):
                raise ValueError()
        return {"hierarchy": hierarchy, "source": {
            "folder": str(folder.resolve()), "api_version": summary["meta"]["api_version"],
            "files": {name: hashlib.sha256(value).hexdigest() for name, value in raw.items()},
            "selected_ads": len(selected), "unique_creatives": len({r["creative_id"] for r in hierarchy}),
        }}
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        raise MetaReadError("Saved Step 2 sample is missing, incomplete, inconsistent or not for Steele's July window.") from None


def availability(data, field):
    if field not in data:
        return "omitted"
    return "empty" if data[field] is None or data[field] == "" or data[field] == [] or data[field] == {} else "populated"


def read_group(reader, object_id, group):
    fields = CONNECTION_FIELDS[group]
    result = {"status": "complete", "data": {}, "diagnostics": {}, "collected_at_utc": datetime.now(timezone.utc).isoformat()}
    try:
        result["data"] = reader.connection(object_id, fields)
    except MetaFieldUnavailable as error:
        if error.availability != "unsupported" or group == "promoted":
            result["status"] = "complete_with_gaps"
            result["diagnostics"] = {key: {"status": error.availability, "error": str(error)} for key in fields.split(",")[2:]}
            return result
        # Only a confirmed unsupported-field rejection triggers bounded single-field reads.
        # Permission/network/rate-limit failures never trigger retries or broader access.
        for key in fields.split(",")[2:]:
            try:
                data = reader.connection(object_id, f"id,account_id,{key}")
                result["data"].update(data)
                if key not in data:
                    result["diagnostics"][key] = {"status": "omitted"}
            except MetaFieldUnavailable as field_error:
                result["diagnostics"][key] = {"status": field_error.availability, "error": str(field_error)}
            except MetaReadError as fatal:
                # Preserve successful fallback fields before stopping on a fatal failure.
                result["status"], result["error"] = "failed", str(fatal)
                for remaining in fields.split(",")[2:]:
                    if remaining not in result["data"] and remaining not in result["diagnostics"]:
                        result["diagnostics"][remaining] = {"status": "not_requested"}
                return result
        result["status"] = "complete_with_gaps" if result["diagnostics"] else "complete"
    return result


def dictionary_rows(result, catalogue):
    rows = []
    def add(kind, object_id, group, field, state, value=None, error=""):
        meaning, use = FIELD_DICTIONARY[field]
        rows.append({"entity_type": kind, "object_id": object_id, "group": group, "field": field,
                     "availability": state, "sample_value_json": json.dumps(value, ensure_ascii=False) if state in ("populated", "empty") else "",
                     "meaning": meaning, "possible_connection_use": use, "error": error})
    for kind, objects in (("creative", result["creatives"]), ("adset", result["adsets"])):
        for object_id, groups in objects.items():
            for group, obj in groups.items():
                for field in CONNECTION_FIELDS[group].split(",")[2:]:
                    diagnostic = obj.get("diagnostics", {}).get(field, {})
                    state = diagnostic.get("status") or ("not_requested" if obj["status"] == "not_requested" else availability(obj.get("data", {}), field))
                    add(kind, object_id, group, field, state, obj.get("data", {}).get(field), diagnostic.get("error", obj.get("error", "")))
    for attempt in catalogue["attempts"]:
        add("product_set", attempt["product_set_id"], "catalogue_items", "products", attempt["availability"], error=attempt.get("error", ""))
    for item in catalogue["items"]:
        for field in ITEM_FIELDS.split(","):
            add("catalogue_item", item["id"], "catalogue_items", field, availability(item, field), item.get(field))
    return rows


def collect_creatives(reader, folder: Path, saved: dict, max_creatives: int) -> dict:
    if not 1 <= max_creatives <= 15:
        raise MetaReadError("Creative limit must be between 1 and 15.")
    ids = sorted({row["creative_id"] for row in saved["hierarchy"]}, key=int)[:max_creatives]
    links = [row for row in saved["hierarchy"] if row["creative_id"] in ids]
    adset_ids = sorted({row["adset_id"] for row in links}, key=int)
    pending = lambda: {"status": "not_requested", "data": {}}
    result = {"status": "running", "source_sample": saved["source"],
              "ad_creative_references": links, "verified_ads": {},
              "creatives": {key: {group: pending() for group in ("destination", "catalogue")} for key in ids},
              "adsets": {key: {"promoted": pending()} for key in adset_ids}}
    catalogue = {"status": "not_requested", "item_limit": 20, "attempts": [], "items": [],
                 "selected_product_set_id": None, "all_set_items_collected": False, "limit_reached": False}
    manifest = {"stage": "creatives", "status": "running", "account_id": ACCOUNT_ID,
                "api_version": reader.config.version, "dates": JULY_WINDOW,
                "collected_at_utc": datetime.now(timezone.utc).isoformat(), "source_sample": saved["source"],
                "max_creatives": max_creatives, "creative_ids": ids, "adset_ids": adset_ids,
                "requested_fields": {**CONNECTION_FIELDS, "catalogue_items": ITEM_FIELDS, "ad_verification": "Step 2 ad fields"},
                "limits": {"selected_ads": 15, "unique_creatives": 15, "catalogue_items": 20,
                           "catalogue_scope": "first accessible referenced set; no catalogue inventory"},
                "availability_states": ["populated", "omitted", "empty", "unsupported", "permission_blocked", "unavailable", "not_requested"],
                "limitations": ["July dates select the source sample; these reads are current configuration snapshots.",
                                "Omitted does not prove unsupported or absent during July.",
                                "Product-set membership does not establish which item was shown or purchased.",
                                "Tracking placeholders are not delivered values; no Shopify/GA4 matching or link parsing.",
                                "Small sample does not guarantee coverage of all creative formats.",
                                "Page/post content is not requested; nested creative settings are preserved."]}
    def save():
        write_json(folder / "creatives.json", result)
        write_json(folder / "catalogue.json", catalogue)
        write_json(folder / "manifest.json", manifest)
    try:
        for row in links:
            result["verified_ads"][row["ad_id"]] = reader.bind_connection_ad(row)
            save()
        for creative_id in ids:
            for group in ("destination", "catalogue"):
                obj = read_group(reader, creative_id, group)
                result["creatives"][creative_id][group] = obj
                save()
                if obj["status"] == "failed":
                    raise MetaReadError(obj["error"])
        for adset_id in adset_ids:
            obj = read_group(reader, adset_id, "promoted")
            result["adsets"][adset_id]["promoted"] = obj
            if obj.get("data", {}).get("campaign_id") not in {r["campaign_id"] for r in links if r["adset_id"] == adset_id} and obj["status"] == "complete":
                raise MetaReadError("Current ad-set campaign differs from the source sample.")
            save()
        references = set()
        for groups in result["creatives"].values():
            value = groups["catalogue"].get("data", {}).get("product_set_id")
            if value:
                references.add(value)
        for groups in result["adsets"].values():
            promoted = groups["promoted"].get("data", {}).get("promoted_object")
            if isinstance(promoted, dict) and promoted.get("product_set_id"):
                references.add(promoted["product_set_id"])
        catalogue["referenced_product_set_ids"] = sorted(references, key=int)
        catalogue["status"] = "no_references" if not references else "unavailable"
        for product_set_id in sorted(references, key=int):
            attempt = {"product_set_id": product_set_id, "availability": "not_requested",
                       "collected_at_utc": datetime.now(timezone.utc).isoformat()}
            catalogue["attempts"].append(attempt)
            try:
                for page, has_more in reader.product_pages(product_set_id):
                    catalogue["items"].extend(page)
                    attempt["availability"] = "populated" if catalogue["items"] else "empty"
                    catalogue["selected_product_set_id"] = product_set_id
                    catalogue["all_set_items_collected"] = not has_more
                    catalogue["limit_reached"] = len(catalogue["items"]) == 20 and has_more
                    save()
                catalogue["status"] = "complete"
                break
            except MetaFieldUnavailable as error:
                attempt.update({"availability": error.availability, "error": str(error)})
                # Once a page was accessible, stop rather than mixing two sets' members.
                if catalogue["selected_product_set_id"]:
                    catalogue["status"] = "partial"
                    break
                save()
        has_gaps = any(obj["status"] == "complete_with_gaps" for objects in (result["creatives"], result["adsets"])
                       for groups in objects.values() for obj in groups.values())
        result["status"] = "complete_with_gaps" if has_gaps or catalogue["status"] in ("unavailable", "partial") else "complete"
    except (MetaReadError, MetaObjectUnavailable) as error:
        result.update({"status": "failed", "error": str(error)})
        if catalogue["status"] not in ("not_requested", "no_references", "complete"):
            catalogue["status"] = "failed"
    finally:
        rows = dictionary_rows(result, catalogue)
        manifest.update({"status": result["status"], "finished_at_utc": datetime.now(timezone.utc).isoformat(),
                         "request_count_including_access": reader.request_count,
                         "creative_count": len(ids), "verified_ad_count": len(result["verified_ads"]),
                         "catalogue_status": catalogue["status"], "catalogue_item_count": len(catalogue["items"]),
                         "availability_counts": {state: sum(r["availability"] == state for r in rows) for state in manifest["availability_states"]}})
        if result.get("error"):
            manifest["error"] = result["error"]
        with (folder / "field_dictionary.csv").open("w", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=["entity_type", "object_id", "group", "field", "availability", "sample_value_json", "meaning", "possible_connection_use", "error"])
            writer.writeheader()
            writer.writerows(rows)
        save()
    return manifest
