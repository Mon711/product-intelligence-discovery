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

Copy `.env.example` to `.env` and fill in the credentials needed by the script you want to run.

## Run scripts

```bash
uv run python scripts/test_shopify_connection.py
uv run python scripts/discover_shopify_type_fields.py Product
uv run python scripts/test_ga4_connection.py
uv run python scripts/list_ga4_properties.py
uv run python scripts/list_ga4_event_counts.py
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
