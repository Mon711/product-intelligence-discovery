from google.analytics.admin import AnalyticsAdminServiceClient

from ga4_discovery.auth import get_credentials


def main() -> None:
    client = AnalyticsAdminServiceClient(credentials=get_credentials())

    for account_summary in client.list_account_summaries():
        print(f"Account: {account_summary.display_name}")
        print(f"Account resource: {account_summary.account}")
        
        for property_summary in account_summary.property_summaries:
            print(f"Property: {property_summary.display_name}")
            print(f"Property resource: {property_summary.property}")
            print()


if __name__ == "__main__":
    main()
