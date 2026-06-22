SHOP_QUERY = """
query ShopInfo {
  shop {
    name
    myshopifyDomain
    primaryDomain {
      url
    }
  }
}
"""