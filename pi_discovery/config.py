from dataclasses import dataclass
import os

from dotenv import load_dotenv


@dataclass(frozen=True)
class ShopifyConfig:
    shop_domain: str
    access_token: str
    api_version: str


def load_shopify_config() -> ShopifyConfig:
    load_dotenv()

    shop_domain = os.getenv("SHOPIFY_SHOP_DOMAIN")
    access_token = os.getenv("SHOPIFY_ADMIN_ACCESS_TOKEN")
    api_version = os.getenv("SHOPIFY_API_VERSION")

    if not shop_domain:
        raise ValueError("SHOPIFY_SHOP_DOMAIN is missing")

    if not access_token:
        raise ValueError("SHOPIFY_ADMIN_ACCESS_TOKEN is missing")
