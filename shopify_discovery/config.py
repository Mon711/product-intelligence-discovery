from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class ShopifyConfig:
    shop_domain: str
    access_token: str
    api_version: str


def load_shopify_config() -> ShopifyConfig:
    config_file = Path(__file__).resolve().parent.parent / "config" / "shopify" / ".env"
    load_dotenv(config_file)

    shop_domain = os.getenv("SHOPIFY_SHOP_DOMAIN")
    access_token = os.getenv("SHOPIFY_ADMIN_ACCESS_TOKEN")
    api_version = os.getenv("SHOPIFY_API_VERSION")

    if not shop_domain:
        raise ValueError("SHOPIFY_SHOP_DOMAIN is missing")

    if not access_token:
        raise ValueError("SHOPIFY_ADMIN_ACCESS_TOKEN is missing")

    return ShopifyConfig(
        shop_domain=shop_domain,
        access_token=access_token,
        api_version=api_version or "2026-04",
    )
