from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import DateRange, Dimension, Metric, RunReportRequest

from ga4_discovery.auth import get_credentials


PROPERTY_ID = "268350484"


def main() -> None:
    client = BetaAnalyticsDataClient(credentials=get_credentials())
    request = RunReportRequest(
        property=f"properties/{PROPERTY_ID}",
        dimensions=[Dimension(name="eventName")],
        metrics=[Metric(name="eventCount")],
        date_ranges=[DateRange(start_date="7daysAgo", end_date="today")],
    )
    response = client.run_report(request)

    for row in response.rows:
        event_name = row.dimension_values[0].value
        event_count = row.metric_values[0].value
        print(f"{event_name}: {event_count}")


if __name__ == "__main__":
    main()
