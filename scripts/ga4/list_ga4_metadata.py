from google.analytics.data_v1beta import BetaAnalyticsDataClient

from ga4_discovery.auth import get_credentials


PROPERTY_ID = "268350484"


def main() -> None:
    client = BetaAnalyticsDataClient(credentials=get_credentials())
    metadata = client.get_metadata(name=f"properties/{PROPERTY_ID}/metadata")

    print("====================")
    print("DIMENSIONS")
    print("====================")
    for dimension in metadata.dimensions:
        print(f"API name: {dimension.api_name}")
        print(f"Display name: {dimension.ui_name}")
        print(f"Description: {dimension.description}")
        print()

    print("====================")
    print("METRICS")
    print("====================")
    for metric in metadata.metrics:
        print(f"API name: {metric.api_name}")
        print(f"Display name: {metric.ui_name}")
        print(f"Description: {metric.description}")
        print()


if __name__ == "__main__":
    main()
