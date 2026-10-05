"""Validate Steele access and export read-only advertising discovery evidence."""

import argparse
from datetime import date

from meta_discovery.reader import MetaReadError, MetaReader, ReaderConfig
from meta_discovery.reporting import export_report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--since", default="2026-09-01", help="First account-local date, inclusive (YYYY-MM-DD).")
    parser.add_argument("--until", default="2026-09-30", help="Last account-local date, inclusive (YYYY-MM-DD).")
    parser.add_argument("--check-only", action="store_true", help="Validate token and account without creating report files.")
    args = parser.parse_args()
    try:
        start, end = date.fromisoformat(args.since), date.fromisoformat(args.until)
    except ValueError:
        parser.error("Dates must use YYYY-MM-DD.")
    if start > end or (end - start).days >= 31:
        parser.error("Choose an inclusive report window of 1 to 31 days.")
    try:
        config = ReaderConfig.from_file()
        reader = MetaReader(config)
        account = reader.validate()
        print(f"Confirmed {account['name']} ({account['id']}); {account['currency']}, {account['timezone_name']}.")
        print("Permissions: " + ", ".join(reader.token_info["scopes"]))
        if args.check_only:
            print("Read-only token and account checks passed. No report files written.")
            return 0
        folder, manifest = export_report(reader, account, args.since, args.until)
        print("Complete local report: " + str(folder))
        for name, count in manifest["counts"].items():
            print(f"{name}: {count} rows")
        print("Ads Manager comparison has not yet been verified. Reach has not been summed.")
        return 0
    except MetaReadError as error:
        print("Read-only discovery stopped: " + str(error))
        return 1
    except (Exception, KeyboardInterrupt):
        print("Read-only discovery stopped unexpectedly; sensitive exception details withheld.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
