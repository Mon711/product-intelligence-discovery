"""Run one Meta discovery stage: access, July sample, or creative connection fields."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from meta_discovery.auth import CONFIG_FILE
from meta_discovery.foundation import EvidenceError, audit_foundation
from meta_discovery.reader import MetaReadError, MetaReader, ReaderConfig
from meta_discovery.sampling import collect_sample
from meta_discovery.creatives import collect_creatives, load_sample


REPO_ROOT = Path(__file__).resolve().parents[2]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=["access", "sample", "creatives"], default="access", help="access = Step 1; sample = Step 2; creatives = Step 3.")
    parser.add_argument("--offline", action="store_true", help="Check saved evidence only; do not load credentials or contact APIs.")
    parser.add_argument("--config", type=Path, default=CONFIG_FILE, help="Explicit Meta .env file for live access checks.")
    parser.add_argument("--evidence-root", type=Path, default=REPO_ROOT / "evidence", help="Input evidence folder; useful for testing copies.")
    parser.add_argument("--output-dir", type=Path, help="Parent for a new run folder; defaults to the stage folder under evidence/meta/.")
    parser.add_argument("--max-ads", type=int, choices=range(1, 16), default=15, help="Step 2 sample size, 1–15; defaults to 15.")
    parser.add_argument("--sample-dir", type=Path, help="Step 3 input: a completed Step 2 run folder; required for creatives.")
    parser.add_argument("--max-creatives", type=int, choices=range(1, 16), default=15, help="Step 3 unique creative limit, 1–15; defaults to 15.")
    args = parser.parse_args(argv)
    if args.offline and args.stage != "access":
        parser.error("--offline applies only to access; later stages require live Meta reads.")
    if args.stage == "creatives" and args.sample_dir is None:
        parser.error("--stage creatives requires --sample-dir from a completed Step 2 run.")
    if args.stage != "creatives" and (args.sample_dir is not None or args.max_creatives != 15):
        parser.error("--sample-dir and --max-creatives apply only to creatives.")
    if args.stage != "sample" and args.max_ads != 15:
        parser.error("--max-ads applies only to sample; use --max-creatives for Step 3.")
    now = datetime.now(timezone.utc)
    parent = args.output_dir or REPO_ROOT / "evidence/meta" / {"access": "access-checks", "sample": "samples", "creatives": "creatives"}[args.stage]
    folder = parent / now.strftime("%Y%m%dT%H%M%S%fZ")
    try:
        folder.mkdir(parents=True, exist_ok=False)
    except OSError:
        print("FAILED: could not create a new report folder; no existing report was overwritten.")
        return 1
    report = {"stage": args.stage, "collected_at_utc": now.isoformat(),
              "offline": args.offline, "meta": {"status": "not_requested"}}
    try:
        report["foundation"] = audit_foundation(args.evidence_root)
    except EvidenceError as error:
        report["foundation"] = {"status": "failed", "error": str(error)}
    if not args.offline and report["foundation"]["status"] == "passed":
        loading_sample = args.stage == "creatives"
        try:
            # Check the saved sample before loading credentials or making any network request.
            saved = load_sample(args.sample_dir) if args.stage == "creatives" else None
            loading_sample = False
            reader = MetaReader(ReaderConfig.from_file(args.config))
            report["meta"] = reader.validate()
            if args.stage == "sample":
                result = collect_sample(reader, folder, args.evidence_root / "meta/list_creatives_of_15_ads.json", args.max_ads)
                report["sample"] = {key: result.get(key) for key in ("status", "dates", "insights_complete", "insight_pages", "candidate_count", "max_ads", "empty_sample", "request_count_including_access", "error")}
                report["sample"]["selected_count"] = len(result["selected"])
                report["sample"]["complete_rows"] = sum(row["status"] == "complete" for row in result["hierarchy"])
                report["sample"]["issue_rows"] = sum(row["status"] != "complete" for row in result["hierarchy"])
            elif args.stage == "creatives":
                report["creatives"] = collect_creatives(reader, folder, saved, args.max_creatives)
        except MetaReadError as error:
            section = args.stage if loading_sample or (args.stage != "access" and report["meta"]["status"] == "passed") else "meta"
            report[section] = {"status": "failed", "error": str(error)}
        except OSError:
            report[args.stage] = {"status": "failed", "error": "Could not save stage evidence; any retained files are incomplete."}
    elif not args.offline:
        report["meta"] = {"status": "skipped", "reason": "Fix the saved-evidence check before live requests."}
    passed = report["foundation"]["status"] == "passed" and (args.offline or report["meta"]["status"] == "passed")
    if args.stage == "sample":
        passed = passed and report.get("sample", {}).get("status") == "complete"
    elif args.stage == "creatives":
        passed = passed and report.get("creatives", {}).get("status") in ("complete", "complete_with_gaps")
    report["status"] = "passed" if passed else "failed"
    try:
        output = folder / "summary.json"
        with output.open("x") as file:
            json.dump(report, file, indent=2)
            file.write("\n")
    except OSError:
        print("FAILED: could not save the summary; no existing report was overwritten.")
        return 1
    step_number = {"access": 1, "sample": 2, "creatives": 3}[args.stage]
    print(f"Step {step_number}: {report['status'].upper()}")
    print(f"Saved foundation: {report['foundation']['status']}")
    if "counts" in report["foundation"]:
        counts = report["foundation"]["counts"]
        print(f"Transactions matched: {counts['matched_transactions']}/{counts['ga4_transactions']}")
        print(f"Item rows matched: {counts['matched_item_rows']}/{counts['ga4_item_rows']}")
        print(f"Absent Online Store orders: {counts['absent_online_store_orders']} (not investigated)")
    print(f"Meta access: {report['meta']['status']}")
    if report["meta"]["status"] == "passed":
        account = report["meta"]["account"]
        print(f"Account: {account['account_id']} | {account['currency']} | {account['timezone_name']}")
        print(f"API: {report['meta']['api_version']} | permissions: {', '.join(report['meta']['token']['scopes'])}")
    if "sample" in report:
        sample = report["sample"]
        print(f"Sample: {sample['status']} | selected: {sample.get('selected_count', 0)}/{args.max_ads}")
        print(f"Insights pages: {sample.get('insight_pages', 0)} | candidates: {sample.get('candidate_count', 0)} | complete: {sample.get('insights_complete', False)}")
        print(f"Hierarchy rows with gaps: {sample.get('issue_rows', 0)}")
        if sample.get("empty_sample"):
            print("No ads had positive reported impressions in the selected window; sample is empty.")
        print(f"Sample folder: {folder.resolve()}")
    if "creatives" in report:
        creative = report["creatives"]
        print(f"Creatives: {creative['status']} | selected: {creative.get('creative_count', 0)}/{args.max_creatives}")
        print(f"Catalogue: {creative.get('catalogue_status', 'not_requested')} | items: {creative.get('catalogue_item_count', 0)}")
        print(f"Field availability: {creative.get('availability_counts', {})}")
        print(f"Creative folder: {folder.resolve()}")
    for section in ("foundation", "meta", "sample", "creatives"):
        if section not in report:
            continue
        if report[section].get("error"):
            print(f"{section}: {report[section]['error']}")
    print(f"Summary: {output.resolve()}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
