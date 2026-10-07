"""Step 2: collect July delivery candidates, choose a bounded sample, save hierarchy."""

import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from meta_discovery.reader import INSIGHT_FIELDS, JULY_WINDOW, OBJECT_FIELDS, MetaReadError, MetaObjectUnavailable


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def select_ads(rows, preferred_names, max_ads):
    eligible = [row for row in rows if int(row["impressions"]) > 0]
    return sorted(eligible, key=lambda row: (row.get("ad_name") not in preferred_names, int(row["ad_id"])))[:max_ads]


def collect_sample(reader, folder: Path, examples: Path, max_ads: int) -> dict:
    if not 1 <= max_ads <= 15:
        raise MetaReadError("Sample size must be between 1 and 15.")
    try:
        example_bytes = examples.read_bytes()
        saved = json.loads(example_bytes)
        if not isinstance(saved, list) or any(not isinstance(row, dict) or not isinstance(row.get("ad_name"), str) for row in saved):
            raise ValueError()
        preferred = {row["ad_name"] for row in saved}
    except (OSError, ValueError):
        raise MetaReadError("Saved creative examples are missing or malformed; selection has not started.") from None
    result = {
        "status": "running", "dates": JULY_WINDOW, "row_meaning": "one ad across the entire seven-day window",
        "insights_complete": False, "insight_pages": 0, "candidate_count": 0, "max_ads": max_ads,
        "selection_rule": "positive impressions; exact saved-example ad names first; numeric ad ID ascending within each group",
        "selection_reference": {"path": str(examples.resolve()), "sha256": hashlib.sha256(example_bytes).hexdigest()},
        "requested_fields": {"insights": INSIGHT_FIELDS, **OBJECT_FIELDS},
        "report_settings": {"level": "ad", "time_increment": "entire window", "breakdowns": [],
                            "attribution": "no conversion metrics requested; no attribution override"},
        "selected": [], "objects": {"ad": {}, "adset": {}, "campaign": {}}, "hierarchy": [],
        "limitations": ["Small deliberately chosen sample; not full account or creative-format coverage.",
                        "Insights describe July delivery; object names/status/creative references are current snapshots.",
                        "Name-based priority is a sampling hint, not a cross-source identity match.",
                        "No creative content, destinations, catalogue items or Shopify/GA4 attribution is read."],
    }
    candidates = []
    try:
        for page in reader.insight_pages():
            candidates.extend(page)
            result["insight_pages"] += 1
            result["candidate_count"] = len(candidates)
            write_json(folder / "insights.json", {"dates": JULY_WINDOW, "complete": False, "rows": candidates})
        result["insights_complete"] = True
        write_json(folder / "insights.json", {"dates": JULY_WINDOW, "complete": True, "rows": candidates})
        result["selected"] = select_ads(candidates, preferred, max_ads)
        reader.register_sample(result["selected"])
        for source in result["selected"]:
            row = {key: source.get(key) for key in ("campaign_id", "campaign_name", "adset_id", "adset_name", "ad_id", "ad_name", "impressions")}
            row.update({"selection_reason": "saved_example_name" if source.get("ad_name") in preferred else "ad_id_fill",
                        "creative_id": None, "status": "reading", "issues": []})
            result["hierarchy"].append(row)
            for kind, key in (("ad", "ad_id"), ("adset", "adset_id"), ("campaign", "campaign_id")):
                object_id = source[key]
                if object_id not in result["objects"][kind]:
                    try:
                        data = reader.object(kind, object_id)
                        data["collected_at_utc"] = datetime.now(timezone.utc).isoformat()
                        result["objects"][kind][object_id] = {"status": "available", "data": data}
                    except MetaObjectUnavailable as error:
                        result["objects"][kind][object_id] = {"status": "unavailable", "error": str(error)}
                obj = result["objects"][kind][object_id]
                row[f"{kind}_read_status"] = obj["status"]
                if obj["status"] != "available":
                    row["issues"].append(f"{kind} unavailable")
                    continue
                data = obj["data"]
                if kind == "ad":
                    creative = data.get("creative") or {}
                    row["creative_id"] = creative.get("id")
                    if not row["creative_id"]:
                        row["issues"].append("creative reference unavailable")
                    if data.get("campaign_id") != source["campaign_id"] or data.get("adset_id") != source["adset_id"]:
                        row["issues"].append("current ad parent references differ from July Insights")
                elif kind == "adset" and data.get("campaign_id") != source["campaign_id"]:
                    row["issues"].append("current ad-set campaign differs from July Insights")
            row["status"] = "complete" if not row["issues"] else "partial"
            write_json(folder / "sample.json", result)
        result["status"] = "complete" if all(row["status"] == "complete" for row in result["hierarchy"]) else "partial"
        result["empty_sample"] = not result["selected"]
    except MetaReadError as error:
        result["status"] = "failed"
        result["error"] = str(error)
    finally:
        result["request_count_including_access"] = reader.request_count
        write_json(folder / "sample.json", result)
        columns = ["campaign_id", "campaign_name", "adset_id", "adset_name", "ad_id", "ad_name", "creative_id", "impressions", "selection_reason", "status", "ad_read_status", "adset_read_status", "campaign_read_status", "issues"]
        with (folder / "hierarchy.csv").open("w", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=columns)
            writer.writeheader()
            for row in result["hierarchy"]:
                writer.writerow({**row, "issues": "; ".join(row["issues"])})
    return result
