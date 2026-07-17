from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Filter,
    FilterExpression,
    Metric,
    OrderBy,
    RunReportRequest,
)
from google.api_core.exceptions import GoogleAPICallError

from ga4_discovery.auth import get_credentials

PROPERTY_ID = "268350484"


def main() -> None:
    client = BetaAnalyticsDataClient(credentials=get_credentials())
    request = RunReportRequest(
        property=f"properties/{PROPERTY_ID}",
        dimensions=[
            Dimension(name="date"),
            Dimension(name="transactionId"),
            Dimension(name="itemName"),
            Dimension(name="itemId"),
            Dimension(name="itemVariant"),
        ],
        metrics=[Metric(name="itemsPurchased"), Metric(name="itemRevenue")],
        date_ranges=[
            DateRange(
                start_date="2026-07-01",
                end_date="2026-07-07",
            )
        ],
        dimension_filter=FilterExpression(
            filter=Filter(
                field_name="eventName",
                string_filter=Filter.StringFilter(value="purchase"),
            )
        ),
        order_bys=[
            OrderBy(
                dimension=OrderBy.DimensionOrderBy(dimension_name="date"),
                desc=True,
            )
        ],
    )

    try:
        response = client.run_report(request)
    except GoogleAPICallError as error:
        print(f"GA4 Data API request failed: {error}")
        return

    # 1. Header Row (Adjusted widths and right-aligned headers for numbers)
    print(
        f"{'Date':<12} {'Transaction ID':<18} {'Item Name':<40} {'Item ID':<46} "
        f"{'Variant':<8} {'Purchases':>10} {'Revenue':>12}"
    )
    print("-" * 152)

    for row in response.rows:
        date, transaction_id, item_name, item_id, item_variant = [
            value.value for value in row.dimension_values
        ]
        purchases, item_revenue = [value.value for value in row.metric_values]

        # Format date nicely
        formatted_date = f"{date[:4]}-{date[4:6]}-{date[6:]}"

        # Convert revenue string to a float so we can format it to 2 decimal places
        rev_float = float(item_revenue)

        # 2. Data Row (Matching widths, right-aligned numbers with ':>')
        print(
            f"{formatted_date:<12} {transaction_id:<18} {item_name:<40} {item_id:<46} "
            f"{item_variant:<8} {purchases:>10} {rev_float:>12.2f}"
        )


if __name__ == "__main__":
    main()
