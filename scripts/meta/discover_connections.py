"""Run access checks or collect a small July ad sample; later stages are unavailable."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from meta_discovery.auth import CONFIG_FILE
from meta_discovery.foundation import EvidenceError, audit_foundation
from meta_discovery.reader import MetaReadError, MetaReader, ReaderConfig
from meta_discovery.sampling import collect_sample


REPO_ROOT = Path(__file__).resolve().parents[2]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=["access", "sample"], default="access", help="access = Step 1; sample = Step 2.")
    parser.add_argument("--offline", action="store_true", help="Check saved evidence only; do not load credentials or contact APIs.")
    parser.add_argument("--config", type=Path, default=CONFIG_FILE, help="Explicit Meta .env file for live access checks.")
    parser.add_argument("--evidence-root", type=Path, default=REPO_ROOT / "evidence", help="Input evidence folder; useful for testing copies.")
    parser.add_argument("--output-dir", type=Path, help="Parent for a new run folder; defaults to evidence/meta/access-checks or samples.")
    parser.add_argument("--max-ads", type=int, choices=range(1, 16), default=15, help="Step 2 sample size, 1–15; defaults to 15.")
    args = parser.parse_args(argv)
    if args.offline and args.stage != "access":
        parser.error("--offline applies only to access; sample requires live Meta reads.")
    now = datetime.now(timezone.utc)
    parent = args.output_dir or REPO_ROOT / "evidence/meta" / ("samples" if args.stage == "sample" else "access-checks")
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
        try:
            reader = MetaReader(ReaderConfig.from_file(args.config))
            report["meta"] = reader.validate()
            if args.stage == "sample":
                result = collect_sample(reader, folder, args.evidence_root / "meta/list_creatives_of_15_ads.json", args.max_ads)
                report["sample"] = {key: result.get(key) for key in ("status", "dates", "insights_complete", "insight_pages", "candidate_count", "max_ads", "empty_sample", "request_count_including_access", "error")}
                report["sample"]["selected_count"] = len(result["selected"])
                report["sample"]["complete_rows"] = sum(row["status"] == "complete" for row in result["hierarchy"])
                report["sample"]["issue_rows"] = sum(row["status"] != "complete" for row in result["hierarchy"])
        except MetaReadError as error:
            section = "sample" if report["meta"]["status"] == "passed" and args.stage == "sample" else "meta"
            report[section] = {"status": "failed", "error": str(error)}
        except OSError:
            report["sample"] = {"status": "failed", "error": "Could not save sample evidence; any retained files are incomplete."}
    elif not args.offline:
        report["meta"] = {"status": "skipped", "reason": "Fix the saved-evidence check before live requests."}
    passed = report["foundation"]["status"] == "passed" and (args.offline or report["meta"]["status"] == "passed")
    if args.stage == "sample":
        passed = passed and report.get("sample", {}).get("status") == "complete"
    report["status"] = "passed" if passed else "failed"
    try:
        output = folder / "summary.json"
        with output.open("x") as file:
            json.dump(report, file, indent=2)
            file.write("\n")
    except OSError:
        print("FAILED: could not save the summary; no existing report was overwritten.")
        return 1
    print(f"Step {2 if args.stage == 'sample' else 1}: {report['status'].upper()}")
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
    for section in ("foundation", "meta", "sample"):
        if section not in report:
            continue
        if report[section].get("error"):
            print(f"{section}: {report[section]['error']}")
    print(f"Summary: {output.resolve()}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
