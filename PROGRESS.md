# Product Intelligence Discovery - Progress Log

**Project**: Product Intelligence Discovery for Shopify Integration  
**Date Started**: 2026-06-20  
**Current Status**: Foundation & Testing Phase

---

## What's Implemented

### Core Infrastructure
- ✅ Python package structure (`pi_discovery/`)
- ✅ Environment variable configuration (.env support)
- ✅ Git setup with proper .gitignore

### Configuration Management (`pi_discovery/config.py`)
- ✅ `ShopifyConfig` dataclass for storing Shopify credentials
  - Immutable (frozen=True) for security
  - Fields: `shop_domain`, `access_token`, `api_version`
- ✅ `load_shopify_config()` function that:
  - Loads from environment variables
  - Validates required fields (shop_domain, access_token)
  - Sets default API version (2026-04)
  - Raises clear errors if credentials missing

### Shopify GraphQL Client (`pi_discovery/shopify_client.py`)
- ✅ `ShopifyClient` class for API communication
  - Accepts ShopifyConfig and constructs Admin API endpoint URL
  - `execute()` method for running GraphQL queries and mutations
  - Handles variables for dynamic queries
  - Comprehensive error handling:
    - HTTP status code validation
    - GraphQL error detection
    - Clear error messages
  - 30-second timeout on all requests
  - Proper authentication headers

### GraphQL Queries (`pi_discovery/queries.py`)
- ✅ `SHOP_QUERY` - Fetches basic shop information
  - Shop name
  - MyShopify domain
  - Primary domain URL
- ✅ `TYPE_FIELDS_QUERY` - GraphQL introspection query
  - Dynamically queries any Shopify GraphQL type schema
  - Retrieves field names, types, descriptions, and arguments
  - Supports nested type inspection (up to 4 levels deep)

### Connection Testing (`scripts/test_shopify_connection.py`)
- ✅ Standalone test script to validate setup
  - Loads configuration
  - Executes a test query
  - Displays shop information on success
  - Usage: `python scripts/test_shopify_connection.py`

### Field Discovery Tool (`scripts/discover_shopify_type_fields.py`)
- ✅ CLI tool to explore Shopify GraphQL schema
  - Accepts type name as command-line argument (e.g., `Product`, `ProductVariant`, `Customer`)
  - Queries Shopify's introspection API to get all fields for a type
  - Outputs results to CSV file with columns:
    - `type_name` - Name of the Shopify type
    - `type_kind` - Kind of type (OBJECT, INTERFACE, etc.)
    - `field_name` - Name of each field
    - `field_type` - Type signature (with ! for required, [] for lists)
    - `is_required` - Boolean indicating if field is required
    - `description` - Field description from Shopify docs
    - `args` - Field arguments (if any)
  - Saves CSV to `outputs/schema_fields/{type_name}_fields.csv`
  - Usage: `python scripts/discover_shopify_type_fields.py Product`
  - Features:
    - Handles complex nested types
    - Creates output directory automatically
    - Provides feedback on number of fields discovered

---

## Current Architecture

```
product-intelligence-discovery/
├── pi_discovery/
│   ├── __init__.py
│   ├── config.py                # Configuration management
│   ├── shopify_client.py        # Shopify GraphQL client
│   └── queries.py               # GraphQL query definitions
├── scripts/
│   ├── test_shopify_connection.py      # Connection test script
│   └── discover_shopify_type_fields.py # Field discovery tool
├── outputs/
│   └── schema_fields/           # Generated CSV files
├── .gitignore
├── requirements.txt             # Python dependencies
└── PROGRESS.md                  # This file
```

---

## Technical Stack

- **Language**: Python 3.12+
- **API**: Shopify Admin GraphQL API (v2026-04)
- **HTTP Client**: requests library
- **Data Processing**: pandas (for CSV export)
- **Configuration**: python-dotenv for environment variables
- **Code Style**: Dataclasses, type hints

---

## How to Use

### Setup Environment Variables
Create a `.env` file in the project root:
```
SHOPIFY_SHOP_DOMAIN=your-store.myshopify.com
SHOPIFY_ADMIN_ACCESS_TOKEN=your-access-token-here
SHOPIFY_API_VERSION=2026-04
```

### Test Connection
Verify that your Shopify credentials are working:
```bash
python scripts/test_shopify_connection.py
```

Expected output:
```
Connected to Shopify successfully.
Shop name: Your Store Name
MyShopify domain: your-store.myshopify.com
Primary domain: https://your-store.com
```

### Discover Type Fields
Explore available fields for any Shopify GraphQL type and export to CSV:
```bash
python scripts/discover_shopify_type_fields.py Product
python scripts/discover_shopify_type_fields.py ProductVariant
python scripts/discover_shopify_type_fields.py Customer
```

The CSV files will be saved in `outputs/schema_fields/`. Each file contains all available fields for that type with their types, requirements, and descriptions.

Custom output directory:
```bash
python scripts/discover_shopify_type_fields.py Product --output-dir custom_output/
```

---

## Dependencies

The project uses the following Python packages (see `requirements.txt`):
- `requests` - HTTP client for Shopify API
- `python-dotenv` - Environment variable loading
- `pandas` - Data processing and CSV export

---

## Notes

- All credentials are loaded from environment variables (never hardcoded)
- The ShopifyConfig is immutable (frozen dataclass) for security
- Error handling covers both HTTP and GraphQL-level failures
- Field discovery tool uses GraphQL introspection for dynamic schema exploration
- CSV exports can be used for documentation and planning
