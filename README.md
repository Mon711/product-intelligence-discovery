# Product Intelligence Discovery

Python discovery utilities for Shopify and Google Analytics 4.

## Prerequisite

Install [`uv`](https://docs.astral.sh/uv/getting-started/installation/). The project pins Python 3.12 and declares all Python dependencies in `pyproject.toml`.

## Setup

From the project root, run:

```bash
uv sync
```

This installs the required Python version when needed, creates or updates `.venv`, and installs the exact dependency versions recorded in `uv.lock`. You do not need to activate the virtual environment when using `uv run`.

Keep local credentials in the matching config folder:

- `config/shopify/.env` contains Shopify environment variables.
- `config/ga4/ga4_oauth_client.json` contains the Google OAuth client file.
- `config/ga4/ga4_token.json` is created or refreshed after GA4 sign-in.

## Run scripts

```bash
uv run python -m scripts.shopify.test_shopify_connection
uv run python -m scripts.shopify.discover_shopify_type_fields Product

uv run python -m scripts.ga4.test_ga4_connection
uv run python -m scripts.ga4.list_ga4_properties
uv run python -m scripts.ga4.list_ga4_event_counts
uv run python -m scripts.ga4.list_ga4_metadata
uv run python -m scripts.ga4.list_ga4_item_performance
uv run python -m scripts.ga4.list_ga4_purchase_transactions
uv run python -m scripts.ga4.list_ga4_purchase_events
```

## Manage dependencies

```bash
# Add a runtime dependency and update the lockfile/environment
uv add package-name

# Remove a dependency
uv remove package-name

# Update all locked dependencies within the declared constraints
uv lock --upgrade

# Reproduce the locked environment after pulling changes
uv sync --frozen
```

`pyproject.toml` is the source of truth for direct dependencies. Commit both `pyproject.toml` and `uv.lock` whenever dependencies change.
