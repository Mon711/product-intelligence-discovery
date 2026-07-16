import argparse
from pathlib import Path
import sys
from typing import Any

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from shopify_discovery.config import load_shopify_config
from shopify_discovery.queries import TYPE_FIELDS_QUERY
from shopify_discovery.shopify_client import ShopifyClient


def type_ref_to_string(type_ref: dict[str, Any] | None) -> str:
    if not type_ref:
        return ""

    kind = type_ref.get("kind")
    name = type_ref.get("name")
    nested_type = type_ref_to_string(type_ref.get("ofType"))

    if kind == "NON_NULL":
        return f"{nested_type}!"

    if kind == "LIST":
        return f"[{nested_type}]"

    return name or kind or ""


def is_required(type_ref: dict[str, Any] | None) -> bool:
    if not type_ref:
        return False

    return type_ref.get("kind") == "NON_NULL"

def format_arg(arg: dict[str, Any]) -> str:
    arg_name = arg["name"]
    arg_type = type_ref_to_string(arg.get("type"))
    default_value = arg.get("defaultValue")
    
    if default_value is not None:
        return f"{arg_name}: {arg_type} = {default_value}"
    
    return f"{arg_name}: {arg_type}"
    

def format_args(args: list[dict[str, Any]]) -> str:
    return ", ".join(format_arg(arg) for arg in args)

def build_field_rows(type_info: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []

    for field in type_info.get("fields") or []:
        args = field.get("args") or []

        rows.append(
            {
                "type_name": type_info["name"],
                "type_kind": type_info["kind"],
                "field_name": field["name"],
                "field_type": type_ref_to_string(field.get("type")),
                "is_required": is_required(field.get("type")),
                "description": field.get("description"),
                "args": format_args(args),
            }
        )

    return rows


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Discover available fields for a Shopify GraphQL type."
    )

    parser.add_argument(
        "type_name",
        help="Shopify GraphQL type name, for example Product or ProductVariant.",
    )

    parser.add_argument(
        "--output-dir",
        default="outputs/schema_fields",
        help="Directory where the CSV file should be saved.",
    )

    args = parser.parse_args()

    config = load_shopify_config()
    client = ShopifyClient(config)

    data = client.execute(TYPE_FIELDS_QUERY, variables={"typeName": args.type_name})

    type_info = data["__type"]

    if type_info is None:
        raise ValueError(f"Shopify type not found: {args.type_name}")

    rows = build_field_rows(type_info)
    fields_df = pd.DataFrame(rows)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / f"{args.type_name}_fields.csv"
    fields_df.to_csv(output_path, index=False)

    print(f"Discovered {len(fields_df)} fields for {args.type_name}.")
    print(f"Saved CSV to: {output_path}")


if __name__ == "__main__":
    main()
