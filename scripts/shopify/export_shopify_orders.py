import csv
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from shopify_discovery.config import load_shopify_config
from shopify_discovery.shopify_client import ShopifyApiError, ShopifyClient


START_UTC = "2026-06-30T14:00:00Z"
END_UTC = "2026-07-07T14:00:00Z"
ORDER_SEARCH_QUERY = (
    f"created_at:>='{START_UTC}' created_at:<'{END_UTC}'"
)
MELBOURNE = ZoneInfo("Australia/Melbourne")

ORDER_OUTPUT = REPO_ROOT / "outputs/shopify_orders/orders_2026-07-01_to_2026-07-07.csv"
LINE_OUTPUT = REPO_ROOT / "outputs/shopify_orders/order_lines_2026-07-01_to_2026-07-07.csv"
RECONCILIATION_OUTPUT = (
    REPO_ROOT
    / "outputs/discovery/shopify_ga4_order_reconciliation_2026-07-01_to_2026-07-07.csv"
)
GA4_PURCHASE_EVENTS = (
    REPO_ROOT / "outputs/GA4_metadata/purchase_events_2026-07-01_to_2026-07-07.txt"
)
GA4_PURCHASE_ITEMS = (
    REPO_ROOT / "outputs/GA4_metadata/purchase_items_2026-07-01_to_2026-07-07.txt"
)

MONEY_FIELDS = {
    "currentSubtotalPriceSet": "current_subtotal",
    "currentTotalDiscountsSet": "current_total_discounts",
    "currentTotalTaxSet": "current_total_tax",
    "currentShippingPriceSet": "current_shipping_price",
    "currentTotalPriceSet": "current_total",
    "totalReceivedSet": "total_received",
    "totalRefundedSet": "total_refunded",
}

MONEY_BAG_SELECTION = """
shopMoney { amount currencyCode }
presentmentMoney { amount currencyCode }
"""

ORDER_EXPORT_QUERY = f"""
query ExportOrders($after: String, $query: String!) {{
  orders(first: 100, after: $after, sortKey: CREATED_AT, query: $query) {{
    pageInfo {{ hasNextPage endCursor }}
    nodes {{
      id
      legacyResourceId
      name
      createdAt
      processedAt
      updatedAt
      cancelledAt
      cancelReason
      test
      confirmed
      closed
      edited
      fullyPaid
      sourceName
      registeredSourceUrl
      displayFinancialStatus
      displayFulfillmentStatus
      paymentGatewayNames
      currencyCode
      presentmentCurrencyCode
      subtotalLineItemsQuantity
      currentSubtotalPriceSet {{ {MONEY_BAG_SELECTION} }}
      currentTotalDiscountsSet {{ {MONEY_BAG_SELECTION} }}
      currentTotalTaxSet {{ {MONEY_BAG_SELECTION} }}
      currentShippingPriceSet {{ {MONEY_BAG_SELECTION} }}
      currentTotalPriceSet {{ {MONEY_BAG_SELECTION} }}
      totalReceivedSet {{ {MONEY_BAG_SELECTION} }}
      totalRefundedSet {{ {MONEY_BAG_SELECTION} }}
      returnStatus
      shippingAddress {{ countryCodeV2 }}
      attribution {{ handle displayName }}
      app {{ id name }}
      lineItems(first: 250) {{
        pageInfo {{ hasNextPage endCursor }}
        nodes {{
          id
          name
          title
          variantTitle
          sku
          quantity
          currentQuantity
          originalUnitPriceSet {{ {MONEY_BAG_SELECTION} }}
          discountedTotalSet {{ {MONEY_BAG_SELECTION} }}
          variant {{ id legacyResourceId }}
          product {{ id legacyResourceId title }}
        }}
      }}
    }}
  }}
}}
"""

MORE_LINE_ITEMS_QUERY = f"""
query ExportMoreOrderLines($orderId: ID!, $after: String!) {{
  node(id: $orderId) {{
    ... on Order {{
      lineItems(first: 250, after: $after) {{
        pageInfo {{ hasNextPage endCursor }}
        nodes {{
          id
          name
          title
          variantTitle
          sku
          quantity
          currentQuantity
          originalUnitPriceSet {{ {MONEY_BAG_SELECTION} }}
          discountedTotalSet {{ {MONEY_BAG_SELECTION} }}
          variant {{ id legacyResourceId }}
          product {{ id legacyResourceId title }}
        }}
      }}
    }}
  }}
}}
"""


def melbourne_parts(timestamp: str | None) -> tuple[str, str]:
    if not timestamp:
        return "", ""

    local_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00")).astimezone(
        MELBOURNE
    )
    return local_time.isoformat(), local_time.date().isoformat()


def flatten_money_bag(bag: dict[str, Any] | None, prefix: str) -> dict[str, str]:
    bag = bag or {}
    shop_money = bag.get("shopMoney") or {}
    presentment_money = bag.get("presentmentMoney") or {}
    return {
        f"{prefix}_shop_amount": shop_money.get("amount", ""),
        f"{prefix}_shop_currency": shop_money.get("currencyCode", ""),
        f"{prefix}_presentment_amount": presentment_money.get("amount", ""),
        f"{prefix}_presentment_currency": presentment_money.get("currencyCode", ""),
    }


def fetch_remaining_line_items(
    client: ShopifyClient, order_id: str, line_items: dict[str, Any]
) -> list[dict[str, Any]]:
    rows = list(line_items["nodes"])
    page_info = line_items["pageInfo"]

    while page_info["hasNextPage"]:
        data = client.execute(
            MORE_LINE_ITEMS_QUERY,
            variables={"orderId": order_id, "after": page_info["endCursor"]},
        )
        order_node = data.get("node")
        if not order_node:
            raise RuntimeError(f"Shopify order disappeared during pagination: {order_id}")
        line_items = order_node["lineItems"]
        rows.extend(line_items["nodes"])
        page_info = line_items["pageInfo"]

    return rows


def fetch_orders(client: ShopifyClient) -> tuple[list[dict[str, Any]], int]:
    orders: list[dict[str, Any]] = []
    after = None
    pages_fetched = 0

    while True:
        data = client.execute(
            ORDER_EXPORT_QUERY,
            variables={"after": after, "query": ORDER_SEARCH_QUERY},
        )
        connection = data["orders"]
        pages_fetched += 1

        for order in connection["nodes"]:
            order["lineItemRows"] = fetch_remaining_line_items(
                client, order["id"], order["lineItems"]
            )
            orders.append(order)

        page_info = connection["pageInfo"]
        if not page_info["hasNextPage"]:
            break
        after = page_info["endCursor"]

    return orders, pages_fetched


def build_order_rows(orders: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for order in orders:
        created_at_melbourne, created_date_melbourne = melbourne_parts(order["createdAt"])
        processed_at_melbourne, processed_date_melbourne = melbourne_parts(
            order.get("processedAt")
        )
        attribution = order.get("attribution") or {}
        app = order.get("app") or {}
        shipping_address = order.get("shippingAddress") or {}
        row: dict[str, Any] = {
            "order_graphql_id": order["id"],
            "order_id": str(order["legacyResourceId"]),
            "order_name": order["name"],
            "created_at": order["createdAt"],
            "created_at_melbourne": created_at_melbourne,
            "created_date_melbourne": created_date_melbourne,
            "processed_at": order.get("processedAt") or "",
            "processed_at_melbourne": processed_at_melbourne,
            "processed_date_melbourne": processed_date_melbourne,
            "updated_at": order["updatedAt"],
            "cancelled_at": order.get("cancelledAt") or "",
            "cancel_reason": order.get("cancelReason") or "",
            "test": order["test"],
            "confirmed": order["confirmed"],
            "closed": order["closed"],
            "edited": order["edited"],
            "fully_paid": order["fullyPaid"],
            "source_name": order.get("sourceName") or "",
            "registered_source_url": order.get("registeredSourceUrl") or "",
            "attribution_handle": attribution.get("handle", ""),
            "attribution_display_name": attribution.get("displayName", ""),
            "app_id": app.get("id", ""),
            "app_name": app.get("name", ""),
            "financial_status": order.get("displayFinancialStatus") or "",
            "fulfillment_status": order["displayFulfillmentStatus"],
            "payment_gateway_names": "|".join(order["paymentGatewayNames"]),
            "currency": order["currencyCode"],
            "presentment_currency": order["presentmentCurrencyCode"],
            "subtotal_line_items_quantity": order["subtotalLineItemsQuantity"],
            "return_status": order["returnStatus"],
            "shipping_country_code": shipping_address.get("countryCodeV2", ""),
            "line_item_count": len(order["lineItemRows"]),
        }
        for graphql_name, column_prefix in MONEY_FIELDS.items():
            row.update(flatten_money_bag(order.get(graphql_name), column_prefix))
        rows.append(row)
    return rows


def build_line_rows(orders: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for order in orders:
        order_id = str(order["legacyResourceId"])
        for line in order["lineItemRows"]:
            variant = line.get("variant") or {}
            product = line.get("product") or {}
            row: dict[str, Any] = {
                "order_id": order_id,
                "order_name": order["name"],
                "line_item_graphql_id": line["id"],
                "name": line["name"],
                "title": line["title"],
                "variant_title": line.get("variantTitle") or "",
                "sku": line.get("sku") or "",
                "quantity": line["quantity"],
                "current_quantity": line["currentQuantity"],
                "variant_graphql_id": variant.get("id", ""),
                "variant_id": str(variant.get("legacyResourceId", "")),
                "product_graphql_id": product.get("id", ""),
                "product_id": str(product.get("legacyResourceId", "")),
                "product_title": product.get("title", ""),
            }
            row.update(flatten_money_bag(line.get("originalUnitPriceSet"), "original_unit_price"))
            row.update(flatten_money_bag(line.get("discountedTotalSet"), "discounted_total"))
            rows.append(row)
    return rows


def read_transaction_ids(path: Path) -> set[str]:
    transaction_ids = set()
    row_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}\s+(.+?)\s{2,}")

    with path.open(encoding="utf-8") as input_file:
        for line in input_file:
            match = row_pattern.match(line)
            if match:
                transaction_ids.add(match.group(1).strip())

    return transaction_ids


def build_reconciliation_rows(
    order_rows: list[dict[str, Any]],
    ga4_event_ids: set[str],
    ga4_item_ids: set[str],
) -> list[dict[str, Any]]:
    rows = []
    for order in order_rows:
        order_id = order["order_id"]
        found_in_events = order_id in ga4_event_ids
        found_in_items = order_id in ga4_item_ids
        if found_in_events and found_in_items:
            classification = "complete_ga4_purchase"
        elif found_in_events:
            classification = "event_without_items"
        elif found_in_items:
            classification = "items_without_event"
        else:
            classification = "absent_from_ga4"

        rows.append(
            {
                "order_id": order_id,
                "order_name": order["order_name"],
                "created_at": order["created_at"],
                "created_at_melbourne": order["created_at_melbourne"],
                "created_date_melbourne": order["created_date_melbourne"],
                "processed_at": order["processed_at"],
                "processed_at_melbourne": order["processed_at_melbourne"],
                "source_name": order["source_name"],
                "attribution_handle": order["attribution_handle"],
                "app_id": order["app_id"],
                "app_name": order["app_name"],
                "financial_status": order["financial_status"],
                "fulfillment_status": order["fulfillment_status"],
                "cancelled_at": order["cancelled_at"],
                "cancel_reason": order["cancel_reason"],
                "test": order["test"],
                "edited": order["edited"],
                "fully_paid": order["fully_paid"],
                "payment_gateway_names": order["payment_gateway_names"],
                "presentment_currency": order["presentment_currency"],
                "shipping_country_code": order["shipping_country_code"],
                "line_item_count": order["line_item_count"],
                "current_total_amount": order["current_total_shop_amount"],
                "total_refunded_amount": order["total_refunded_shop_amount"],
                "found_in_ga4_purchase_events": found_in_events,
                "found_in_ga4_purchase_items": found_in_items,
                "classification": classification,
            }
        )
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise RuntimeError(f"Refusing to write a headerless empty CSV: {path}")

    with path.open("w", encoding="utf-8", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def print_summary(
    order_rows: list[dict[str, Any]],
    line_rows: list[dict[str, Any]],
    reconciliation_rows: list[dict[str, Any]],
    pages_fetched: int,
) -> None:
    sources = Counter(row["source_name"] or "(blank)" for row in order_rows)
    classifications = Counter(row["classification"] for row in reconciliation_rows)
    found_in_events = sum(row["found_in_ga4_purchase_events"] for row in reconciliation_rows)

    print(f"Total GraphQL orders created in the period: {len(order_rows)}")
    print(f"Total test orders: {sum(row['test'] for row in order_rows)}")
    print(f"Total cancelled orders: {sum(bool(row['cancelled_at']) for row in order_rows)}")
    print("Total orders by sourceName:")
    for source_name, count in sorted(sources.items()):
        print(f"  {source_name}: {count}")
    print(f"Total orders found in GA4 purchase events: {found_in_events}")
    print(f"Total orders absent from GA4 purchase events: {len(order_rows) - found_in_events}")
    print(f"Total event_without_items: {classifications['event_without_items']}")
    print(f"Total items_without_event: {classifications['items_without_event']}")
    print(f"Total line-item rows: {len(line_rows)}")
    print(f"Number of GraphQL pages fetched: {pages_fetched}")


def main() -> None:
    config = load_shopify_config()
    client = ShopifyClient(config)

    orders, pages_fetched = fetch_orders(client)
    if not orders:
        raise RuntimeError("Shopify returned no orders for the requested date range")

    order_rows = build_order_rows(orders)
    line_rows = build_line_rows(orders)
    ga4_event_ids = read_transaction_ids(GA4_PURCHASE_EVENTS)
    ga4_item_ids = read_transaction_ids(GA4_PURCHASE_ITEMS)
    reconciliation_rows = build_reconciliation_rows(order_rows, ga4_event_ids, ga4_item_ids)

    write_csv(ORDER_OUTPUT, order_rows)
    write_csv(LINE_OUTPUT, line_rows)
    write_csv(RECONCILIATION_OUTPUT, reconciliation_rows)
    print_summary(order_rows, line_rows, reconciliation_rows, pages_fetched)
    print(f"Saved order CSV: {ORDER_OUTPUT}")
    print(f"Saved line-item CSV: {LINE_OUTPUT}")
    print(f"Saved reconciliation CSV: {RECONCILIATION_OUTPUT}")


if __name__ == "__main__":
    try:
        main()
    except (ShopifyApiError, OSError, ValueError, RuntimeError) as error:
        raise SystemExit(f"Shopify order export failed: {error}") from error
