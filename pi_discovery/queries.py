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

TYPE_FIELDS_QUERY = """
query TypeFields($typeName: String!) {
  __type(name: $typeName) {
    name
    kind
    description
    fields {
      name
      description
      args {
        name
        description
        defaultValue
        type {
          kind
          name
          ofType {
            kind
            name
            ofType {
              kind
              name
              ofType {
                kind
                name
                ofType {
                  kind
                  name
                }
              }
            }
          }
        }
      }
      type {
        kind
        name
        ofType {
          kind
          name
          ofType {
            kind
            name
            ofType {
              kind
              name
              ofType {
                kind
                name
              }
            }
          }
        }
      }
    }
  }
}
"""