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

from list_ga4_item_performance import get_credentials


PROPERTY_ID = "268350484"


def main() -> None:
    client = BetaAnalyticsDataClient(credentials=get_credentials())
    request = RunReportRequest(
        property=f"properties/{PROPERTY_ID}",
        dimensions=[Dimension(name="date"), Dimension(name="transactionId")],
        metrics=[Metric(name="ecommercePurchases"), Metric(name="purchaseRevenue")],
        date_ranges=[DateRange(start_date="2026-07-01", end_date="2026-07-07")],
        dimension_filter=FilterExpression(
            filter=Filter(
                field_name="eventName",
                string_filter=Filter.StringFilter(
                    match_type=Filter.StringFilter.MatchType.EXACT,
                    value="purchase",
                ),
            )
        ),
        order_bys=[
            OrderBy(
                dimension=OrderBy.DimensionOrderBy(dimension_name="date"),
                desc=True,
            ),
            OrderBy(
                dimension=OrderBy.DimensionOrderBy(
                    dimension_name="transactionId"
                ),
            ),
        ],
    )

    try:
        response = client.run_report(request)
    except GoogleAPICallError as error:
        print(f"GA4 Data API request failed: {error}")
        return

    print("PURCHASE EVENTS: 2026-07-01 to 2026-07-07")
    print(
        f"{'Date':<12} {'Transaction ID':<20} {'Ecommerce Purchases':>20} "
        f"{'Purchase Revenue':>18}"
    )
    print("-" * 76)

    total_purchases = 0.0
    total_revenue = 0.0
    transaction_ids = set()

    for row in response.rows:
        date, transaction_id = [value.value for value in row.dimension_values]
        ecommerce_purchases, purchase_revenue = [
            value.value for value in row.metric_values
        ]
        formatted_date = f"{date[:4]}-{date[4:6]}-{date[6:]}"
        total_purchases += float(ecommerce_purchases)
        total_revenue += float(purchase_revenue)
        transaction_ids.add(transaction_id)
        print(
            f"{formatted_date:<12} {transaction_id:<20} "
            f"{ecommerce_purchases:>20} {float(purchase_revenue):>18.2f}"
        )

    print()
    print("SUMMARY")
    print(f"Total rows returned: {len(response.rows)}")
    print(f"Unique transaction IDs: {len(transaction_ids)}")
    print(f"Total ecommerce purchases: {total_purchases:g}")
    print(f"Total purchase revenue: {total_revenue:.2f}")

    metadata = getattr(response, "metadata", None)
    print()
    print("RESPONSE METADATA")
    print(f"response.row_count: {getattr(response, 'row_count', 'Unavailable')}")
    if metadata is None:
        print("response.metadata: Unavailable")
        return

    print(f"response.metadata.time_zone: {getattr(metadata, 'time_zone', 'Unavailable')}")
    print(
        "response.metadata.data_loss_from_other_row: "
        f"{getattr(metadata, 'data_loss_from_other_row', 'Unavailable')}"
    )
    print(
        "response.metadata.subject_to_thresholding: "
        f"{getattr(metadata, 'subject_to_thresholding', 'Unavailable')}"
    )

    sampling_metadatas = getattr(metadata, "sampling_metadatas", [])
    for index, sampling_metadata in enumerate(sampling_metadatas, start=1):
        print(
            f"Sampling metadata {index}: "
            f"samples read={getattr(sampling_metadata, 'samples_read_count', 'Unavailable')}, "
            f"sampling space={getattr(sampling_metadata, 'sampling_space_size', 'Unavailable')}"
        )


if __name__ == "__main__":
    main()
