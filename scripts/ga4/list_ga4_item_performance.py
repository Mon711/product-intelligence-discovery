from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Metric,
    OrderBy,
    RunReportRequest,
)
from ga4_discovery.auth import get_credentials


PROPERTY_ID = "268350484"


def main() -> None:
    client = BetaAnalyticsDataClient(credentials=get_credentials())
    request = RunReportRequest(
        property=f"properties/{PROPERTY_ID}",
        dimensions=[
            Dimension(name="itemId"),
            Dimension(name="itemName"),
            Dimension(name="itemVariant"),
        ],
        metrics=[
            Metric(name="itemsViewed"),
            Metric(name="itemsAddedToCart"),
            Metric(name="itemsPurchased"),
            Metric(name="itemRevenue"),
        ],
        date_ranges=[DateRange(start_date="7daysAgo", end_date="today")],
        order_bys=[
            OrderBy(
                metric=OrderBy.MetricOrderBy(metric_name="itemsViewed"),
                desc=True,
            )
        ],
        limit=50,
    )
    response = client.run_report(request)

    print("ITEM PERFORMANCE (LAST 7 DAYS)")
    print("=" * 80)
    for row in response.rows:
        item_id, item_name, item_variant = [value.value for value in row.dimension_values]
        items_viewed, items_added_to_cart, items_purchased, item_revenue = [
            value.value for value in row.metric_values
        ]
        print(
            f"ID: {item_id} | Name: {item_name} | Variant: {item_variant} | "
            f"Viewed: {items_viewed} | Added to cart: {items_added_to_cart} | "
            f"Purchased: {items_purchased} | Revenue: {item_revenue}"
        )


if __name__ == "__main__":
    main()
