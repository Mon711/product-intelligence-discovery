"""Run only Step 1 and save a new credential-free access/foundation summary."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from meta_discovery.auth import CONFIG_FILE
from meta_discovery.foundation import EvidenceError, audit_foundation
from meta_discovery.reader import MetaReadError, MetaReader, ReaderConfig


REPO_ROOT = Path(__file__).resolve().parents[2]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=["access"], default="access", help="Only Step 1 is implemented.")
    parser.add_argument("--offline", action="store_true", help="Check saved evidence only; do not load credentials or contact APIs.")
    parser.add_argument("--config", type=Path, default=CONFIG_FILE, help="Explicit Meta .env file for live access checks.")
    parser.add_argument("--evidence-root", type=Path, default=REPO_ROOT / "evidence", help="Input evidence folder; useful for testing copies.")
    parser.add_argument("--output-dir", type=Path, default=REPO_ROOT / "evidence/meta/access-checks", help="Parent directory for a new run folder.")
    args = parser.parse_args(argv)
    now = datetime.now(timezone.utc)
    report = {"stage": "access", "collected_at_utc": now.isoformat(),
              "offline": args.offline, "meta": {"status": "not_requested"}}
    try:
        report["foundation"] = audit_foundation(args.evidence_root)
    except EvidenceError as error:
        report["foundation"] = {"status": "failed", "error": str(error)}
    if not args.offline and report["foundation"]["status"] == "passed":
        try:
            report["meta"] = MetaReader(ReaderConfig.from_file(args.config)).validate()
        except MetaReadError as error:
            report["meta"] = {"status": "failed", "error": str(error)}
    elif not args.offline:
        report["meta"] = {"status": "skipped", "reason": "Fix the saved-evidence check before live requests."}
    passed = report["foundation"]["status"] == "passed" and (args.offline or report["meta"]["status"] == "passed")
    report["status"] = "passed" if passed else "failed"
    folder = args.output_dir / now.strftime("%Y%m%dT%H%M%S%fZ")
    try:
        folder.mkdir(parents=True, exist_ok=False)
        output = folder / "summary.json"
        with output.open("x") as file:
            json.dump(report, file, indent=2)
            file.write("\n")
    except OSError:
        print("FAILED: could not save the summary; no existing report was overwritten.")
        return 1
    print(f"Step 1: {report['status'].upper()}")
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
    for section in ("foundation", "meta"):
        if "error" in report[section]:
            print(f"{section}: {report[section]['error']}")
    print(f"Summary: {output.resolve()}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
