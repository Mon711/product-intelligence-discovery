from pi_discovery.config import load_shopify_config
from pi_discovery.queries import SHOP_QUERY
from pi_discovery.shopify_client import ShopifyClient

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