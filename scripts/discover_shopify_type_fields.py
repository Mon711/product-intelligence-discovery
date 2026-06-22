import argparse
import json

from pi_discovery.config import load_shopify_config
from pi_discovery.queries import TYPE_FIELDS_QUERY
from pi_discovery.shopify_client import ShopifyClient

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Discover available fields for a Shopify GraphQL type."
    )
    
    parser.add_argument(
        "type_name",
        help="Shopify GraphQL type name, for example Product or ProductVariant.",
    )
    
    args = parser.parse_args()
    
    config = load_shopify_config()
    client = ShopifyClient(config)
    
    data = client.execute(
        TYPE_FIELDS_QUERY,
        variables={"typeName": args.type_name},
    )
    
    type_info = data["__type"]
    
    if type_info is None:
        raise ValueError(f"Shopify type not found: {args.type_name}")
    
    print(json.dumps(type_info, indent=2))


if __name__ == "__main__":
    main()