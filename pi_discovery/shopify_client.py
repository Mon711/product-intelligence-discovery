import requests

from config import ShopifyConfig

class ShopifyApiError(Exception):
    pass

class ShopifyClient:
    def __init__(self, config: ShopifyConfig):
        self.config = config
        self.url = (
            f"https://{config.shop_domain}/admin/api/"
            f"{config.api_version}/graphql.json"
        )
        
    def execute(self, query: str, variables: dict | None = None) -> dict:
        response = requests.post(
            self.url,
            headers={
                "X-Shopify-Access-Token": self.config.access_token,
                "Content-type" : "application/json"
            },
            json={
                "query": query,
                "variables": variables or {}
            },
            timeout=30
        )
        
        if response.status_code != 200:
            raise ShopifyApiError(
                f"Shopify API request failed with status "
                f"{response.status_code}: {response.text}"
            )
            
        payload = response.json()
        
        if "errors" in payload:
            raise ShopifyApiError(f"Shopify GraphQL error: {payload['errors']}")
        
        return payload["data"]