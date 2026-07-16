import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from shopify_discovery.config import load_shopify_config
from shopify_discovery.queries import SHOP_QUERY
from shopify_discovery.shopify_client import ShopifyClient

def main() -> None:
    config = load_shopify_config()
    client = ShopifyClient(config)
    
    data = client.execute(SHOP_QUERY)
    
    shop = data["shop"]
    
    print("Connected to Shopify successfully.")
    print(f"Shop name: {shop['name']}")
    print(f"MyShopify domain: {shop['myshopifyDomain']}")
    print(f"Primary domain: {shop['primaryDomain']['url']}")
    
if __name__ == "__main__":
    main()
