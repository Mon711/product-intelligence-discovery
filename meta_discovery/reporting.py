"""Local evidence files for a bounded Meta discovery run."""

import csv
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import json
from pathlib import Path
from uuid import uuid4

from meta_discovery.reader import INSIGHT_FIELDS, OBJECT_FIELDS, MetaReadError


OUTPUT_ROOT = Path(__file__).resolve().parents[1] / "outputs" / "meta_discovery" / "reports"
ACTION_FIELDS = ("actions", "action_values", "website_purchase_roas")


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_csv(path, rows, fields):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list))
                             else value for key, value in row.items()})


def flatten(pages):
    return [row for page in pages for row in page["data"]]


def windows(since, until):
    """Inclusive seven-day requests avoid background report creation."""
    current, stop = date.fromisoformat(since), date.fromisoformat(until)
    while current <= stop:
        end = min(current + timedelta(days=6), stop)
        yield current.isoformat(), end.isoformat()
        current = end + timedelta(days=1)


def action_rows(rows):
    """Retain every action type and attribution value; never sum purchase variants."""
    result = []
    for row in rows:
        for source in ACTION_FIELDS:
            for action in row.get(source) or []:
                for metric, value in action.items():
                    if metric != "action_type":
                        result.append({"ad_id": row["ad_id"], "date_start": row["date_start"],
                                       "date_stop": row["date_stop"], "source_field": source,
                                       "action_type": action.get("action_type"),
                                       "metric": metric, "value": value})
    return result


def totals(rows):
    # Only additive metrics. Reach is intentionally excluded.
    result = {}
    for metric in ("spend", "impressions", "clicks", "inline_link_clicks"):
        present = [row[metric] for row in rows if row.get(metric) is not None]
        result[metric] = {"sum": str(sum((Decimal(str(v)) for v in present), Decimal(0))) if present else None,
                          "rows_with_value": len(present), "rows_missing_value": len(rows) - len(present)}
    return result


def export_report(reader, account, since, until, output_root=OUTPUT_ROOT, progress=print):
    started = datetime.now(timezone.utc)
    folder = Path(output_root) / (started.strftime("%Y%m%dT%H%M%SZ") + "_" + uuid4().hex[:8])
    folder.mkdir(parents=True, exist_ok=False)
    manifest = {
        "status": "running", "collection_started_at_utc": started.isoformat(),
        "account": account, "token_validation": reader.token_info,
        "api_version": reader.config.version,
        "reporting_dates_inclusive": {"since": since, "until": until},
        "report_settings": {"level": "ad", "time_increment": 1,
                            "use_unified_attribution_setting": True, "action_report_time": "impression",
                            "breakdowns": [], "explicit_filters": [], "date_window_days": 7},
        "row_meaning": "one ad per account-local calendar day with reported delivery",
        "inventory_meaning": "current API-accessible objects; status filtering uses Meta defaults",
        "warnings": [
            "Inventory is collected now, not a reconstruction of September creative/settings history.",
            "Meta-attributed purchases are not individual Shopify orders or Shopify revenue.",
            "Missing fields remain absent in JSON and blank in CSV; they are not assumed zero.",
            "Reach is not additive across ads or days; no summed reach is produced.",
            "Action types can overlap. Do not sum purchase, omni_purchase, and website purchase types.",
            "Ads Manager comparison remains unverified until its date, filters, and attribution match.",
        ],
        "counts": {}, "page_counts": {}, "inventory_missing_field_counts": {},
        "creative_source": "GET reads of unique creative IDs referenced by collected ads with reported delivery in the requested dates; not the entire library",
    }
    path = folder / "manifest.json"
    write_json(path, manifest)
    try:
        for edge, fields in OBJECT_FIELDS.items():
            if edge == "adcreatives":
                continue
            progress("Reading " + edge + " (all pages)...")
            pages = reader.objects(edge)
            rows = flatten(pages)
            write_json(folder / (edge + ".json"), {"requested_fields": fields, "pages": pages,
                                                 "source": "ads.creative" if edge == "adcreatives" else edge})
            write_csv(folder / (edge + ".csv"), rows, fields)
            manifest["counts"][edge] = len(rows)
            manifest["page_counts"][edge] = 0 if edge == "adcreatives" else len(pages)
            manifest["inventory_missing_field_counts"][edge] = {field: sum(field not in row or row[field] is None for row in rows) for field in fields}
            write_json(path, manifest)
        rows = []
        keys = set()
        manifest["insight_windows"] = []
        for start, end in windows(since, until):
            progress(f"Reading daily ad insights: {start} through {end}...")
            pages = reader.insights(start, end)
            current_rows = flatten(pages)
            for row in current_rows:
                if row.get("account_id") != reader.config.account_id or row.get("account_currency") != account["currency"]:
                    raise MetaReadError("Insights returned an unexpected account or currency.")
                if not row.get("ad_id") or not row.get("date_start") or row.get("date_start") != row.get("date_stop"):
                    raise MetaReadError("Insights did not return one ad per day.")
                if not start <= row["date_start"] <= end:
                    raise MetaReadError("Insights returned dates outside the requested window.")
                key = (row["ad_id"], row["date_start"])
                if key in keys:
                    raise MetaReadError("Duplicate ad/day found; report is incomplete.")
                keys.add(key)
            write_json(folder / f"insights_{start}_to_{end}.json", {"requested_fields": INSIGHT_FIELDS, "pages": pages})
            rows.extend(current_rows)
            manifest["insight_windows"].append({"since": start, "until": end, "pages": len(pages), "rows": len(current_rows)})
            write_json(path, manifest)
        rows.sort(key=lambda row: (row["date_start"], row["ad_id"]))
        progress("Reading creatives referenced by ads with reported delivery...")
        creative_requests_before = reader.request_count
        creative_pages = reader.report_creatives({row["ad_id"] for row in rows})
        creative_rows = flatten(creative_pages)
        write_json(folder / "adcreatives.json", {"requested_fields": OBJECT_FIELDS["adcreatives"],
                                               "source": "individual creative GET reads for reporting ads", "pages": creative_pages})
        write_csv(folder / "adcreatives.csv", creative_rows, OBJECT_FIELDS["adcreatives"])
        manifest["counts"]["adcreatives"] = len(creative_rows)
        manifest["creative_request_count"] = reader.request_count - creative_requests_before
        manifest["creative_limitations"] = reader.creative_limitations
        manifest["inventory_missing_field_counts"]["adcreatives"] = {field: sum(field not in row or row[field] is None for row in creative_rows) for field in OBJECT_FIELDS["adcreatives"]}
        actions = action_rows(rows)
        write_csv(folder / "ad_daily_insights.csv", rows, INSIGHT_FIELDS)
        write_csv(folder / "insight_actions.csv", actions,
                  ("ad_id", "date_start", "date_stop", "source_field", "action_type", "metric", "value"))
        adsets = flatten(json.loads((folder / "adsets.json").read_text())["pages"])
        manifest["adset_attribution_settings"] = [{"adset_id": row["id"], "attribution_spec": row.get("attribution_spec")} for row in adsets]
        manifest["counts"].update({"ad_daily_insights": len(rows), "insight_actions": len(actions)})
        manifest["additive_metric_totals"] = totals(rows)
        manifest["missing_field_counts"] = {field: sum(field not in row or row[field] is None for row in rows) for field in INSIGHT_FIELDS}
        known_ads = {row["id"] for row in flatten(json.loads((folder / "ads.json").read_text())["pages"])}
        manifest["insight_ad_ids_missing_from_current_inventory"] = sorted({row["ad_id"] for row in rows} - known_ads)
        ads = flatten(json.loads((folder / "ads.json").read_text())["pages"])
        ads_with_creative_ids = {row["id"] for row in ads if isinstance(row.get("creative"), dict) and row["creative"].get("id")}
        manifest["reporting_ad_ids_without_collected_creative_ids"] = sorted({row["ad_id"] for row in rows} - ads_with_creative_ids)
        manifest["status"] = "complete"
    except (Exception, KeyboardInterrupt) as error:
        # A partial run must never be presented as a complete result.
        manifest["status"] = "failed"
        manifest["failure"] = str(error) if isinstance(error, MetaReadError) else "Local export failed; sensitive details withheld."
        raise MetaReadError(f"Report failed. Partial evidence is marked failed in {path}. " + manifest["failure"]) from None
    finally:
        manifest["request_count"] = reader.request_count
        manifest["rate_limit_info"] = reader.rate_limit_info
        manifest["collection_finished_at_utc"] = datetime.now(timezone.utc).isoformat()
        write_json(path, reader.scrub(manifest))
    return folder, manifest
