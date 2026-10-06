# Product Intelligence Discovery

Small Python experiments and saved research for Steele's Shopify, Google
Analytics 4 (GA4), and Meta Ads data. An API is an interface that lets these
scripts request data from another system.

This is a **discovery repository**: it checks access, available fields, data
relationships, and quality. Dalgo is the chosen aggregation and database
direction. Production connectors belong in the Dalgo repository; dashboards,
scheduled ingestion, deployment, and production infrastructure are outside this
repository. See [project state](docs/project-state.md) for the current direction
and what is actually supported by evidence.

## Start here: what each document is for

| Document | Read it to understand | Update it when |
| --- | --- | --- |
| [Project state](docs/project-state.md) | Source connections, discoveries, limitations, archived work, and open questions | Meaningful knowledge or project status changes |
| [README](README.md) | Setup, code responsibilities, commands, and folder structure | Setup, layout, or usage changes |
| [AGENTS.md](AGENTS.md) | Working rules, safety boundaries, and context maintenance | Durable instructions change |
| [Change history](docs/change-history.md) | Significant changes, reasons, related commits, and verification | Meaningful work is completed |
| [GA4 findings](docs/research/ga4-findings.md) | Detailed July GA4 and Shopify–GA4 investigation | That research gains supported findings or maintenance corrections |
| [Reference documents](docs/reference/) | Original product brief and dated Word snapshots | Preserve as references; edit canonical Markdown instead |

A new human reader can start with project state and this README. An agent should
read `AGENTS.md`, project state, and only the detailed material needed for its
task. This avoids making every new session reread every export. Summaries are
starting points: check relevant source before changing behavior.

`AGENTS.md` is a shared Markdown instruction format supported by many agent
tools. Automatic loading depends on the tool/version and its settings; another
tool can be told explicitly: “Read AGENTS.md and docs/project-state.md first.”
Keep one set of project facts instead of copying them into each tool's private
memory. [Format guidance](https://agents.md/) and
[Claude instruction-loading documentation](https://code.claude.com/docs/en/memory)
explain the distinction between shared files and tool-managed memory.

## Folder structure and code responsibilities

```text
product-intelligence-discovery/
├── docs/
│   ├── project-state.md       Current knowledge and source/evidence register
│   ├── change-history.md      Meaningful milestones and reasons
│   ├── research/              Detailed investigation (currently GA4)
│   └── reference/             Original brief and dated Word snapshots
├── evidence/
│   ├── shopify/
│   │   ├── orders/            Saved order and order-line CSVs
│   │   └── schema-fields/     Available API fields for Shopify objects
│   ├── ga4/                   Saved metadata and report text
│   ├── meta/                  Early listings, creatives, and story attempts
│   └── reconciliation/        Comparisons between sources
├── shopify_discovery/         Shared Shopify configuration/client/queries
├── ga4_discovery/             Shared Google authentication
├── meta_discovery/            Shared Meta token loading
├── scripts/{shopify,ga4,meta}/ Runnable, one-purpose experiments
├── config/                   Local configuration and ignored credentials
├── .python-version            Selected Python version
├── pyproject.toml             Direct dependencies and package configuration
└── uv.lock                    Exact resolved dependency versions
```

A Python **package** is a folder whose modules can be imported by other code.
The `*_discovery` packages hold reusable helpers; `scripts/` holds the specific
experiments a person runs. Their names and run commands are unchanged.

| Code | Responsibility |
| --- | --- |
| `shopify_discovery/config.py` | Load and validate shop/token configuration |
| `shopify_discovery/shopify_client.py` | Send GraphQL requests with a timeout and report request errors |
| `shopify_discovery/queries.py` | Shared shop-information and field-discovery queries |
| `ga4_discovery/auth.py` | Load/refresh Google credentials or start browser sign-in |
| `meta_discovery/auth.py` | Load user/Page tokens; loading alone does not verify access |
| `scripts/shopify/` | Connection check, field inventory, fixed order export and GA4 comparison |
| `scripts/ga4/` | Connection/property checks, field metadata, event/item/purchase reports |
| `scripts/meta/` | Early connection/listing/creative checks and unfinished Page/story experiments |

Execution generally flows **local configuration → shared helper → script →
printed report or saved evidence → research finding**. Reconciliation means
comparing records between sources with aligned dates and definitions. Saved
evidence is a dated research snapshot, not a current production table.

## Setup

Run terminal commands from the repository root. On this machine use `rtk proxy`,
which runs the following command through the user's command wrapper; on a
machine without RTK, omit that prefix. `uv` manages Python and the project's
dependencies (external libraries). Python is pinned to 3.12.

```bash
rtk proxy uv sync
```

This prepares `.venv`, the isolated local Python environment, and installs
project dependencies. It can download Python/packages and change the environment
and lockfile as needed. After setup, select `.venv/bin/python` in your editor.
To reproduce the existing lockfile without resolving new versions, use
`rtk proxy uv sync --frozen`; `--frozen` uses the existing lockfile. Check that
`.venv/bin/python` exists and the command exits successfully.

### Shopify configuration

Create `config/shopify/.env` locally:

```dotenv
SHOPIFY_SHOP_DOMAIN=your-store.myshopify.com
SHOPIFY_ADMIN_ACCESS_TOKEN=your-access-token
SHOPIFY_API_VERSION=2026-04
```

The API version is optional and defaults to `2026-04`. The domain chooses the
store. These credentials are ignored by Git; never paste their real values into
chat or documentation. The root `.env.example` is a legacy placeholder, not the
current credential location.

### GA4 configuration

Place a Google OAuth Desktop client file at
`config/ga4/ga4_oauth_client.json`. OAuth means signing in to grant the script
access; the current scope is read-only Analytics access. The first authenticated
run can open a browser and save `config/ga4/ga4_token.json`; later runs refresh
the token when possible. Both files are ignored by Git.

### Meta configuration

For the legacy ads scripts, create `config/meta/.env` with
`META_USER_ACCESS_TOKEN` or the backward-compatible `META_ACCESS_TOKEN`.
Process environment values take precedence over values loaded from the file.
Token loading does not validate permissions or account access.

The unfinished personal OAuth flow additionally uses `META_APP_ID`,
`META_APP_SECRET`, and `META_OAUTH_REDIRECT_URI=http://localhost:8765/callback`.
The redirect must also be configured in the Meta App. It requests `ads_read`,
`pages_show_list`, and `pages_read_engagement`, gets a user token and the Steele
Page token, and writes `META_USER_ACCESS_TOKEN`, `META_PAGE_ACCESS_TOKEN`, and
`META_ACCESS_TOKEN` into the ignored file. It refuses to save when the required
permissions or Page are missing. This Page-oriented flow is not mandatory for
ads-only reporting. The code does not request `pages_read_user_content`.

## Running discovery experiments

**The commands below contact live source APIs.** Run only with authorization
for that source and scope. Check the script's target, dates, fields, and output
paths first. Meta advertising access is strictly read-only.

`uv run` uses the project environment and can prepare it if needed. `python -m`
runs a named module. For example, from the repository root:

```bash
rtk proxy uv run python -m scripts.shopify.test_shopify_connection
```

This reads Shopify configuration, contacts its API, and prints shop information
or an access error. It does not export research files. Confirm the expected shop
before interpreting the result.

Use the same prefix, `rtk proxy uv run python -m`, with a module below. Printed
output means terminal text, not an automatically saved file.

| Module | Purpose and expected output | Effects and limits |
| --- | --- | --- |
| `scripts.shopify.discover_shopify_type_fields Product` | List the fields of a GraphQL object type; print count and saved CSV path | Live read; default writes `evidence/shopify/schema-fields/Product_fields.csv`, replacing it if present |
| `scripts.shopify.export_shopify_orders` | Export orders/lines and print reconciliation counts | Live Shopify reads with order/line pagination; fixed 1–7 July 2026 Melbourne dates; reads two saved GA4 files and replaces three fixed evidence CSVs |
| `scripts.ga4.test_ga4_connection` | Verify authentication; print confirmation | Can open OAuth browser sign-in and save/refresh a local token |
| `scripts.ga4.list_ga4_properties` | Print accessible accounts and properties | Live Admin API read; no automatic evidence export |
| `scripts.ga4.list_ga4_metadata` | Print available dimensions and metrics | Live Data API metadata read for property `268350484` |
| `scripts.ga4.list_ga4_event_counts` | Print event counts | Moving inclusive `7daysAgo`–`today` range |
| `scripts.ga4.list_ga4_item_performance` | Print item views, cart units, purchases, and revenue | Same moving range; top 50 rows by views, not a full item extract |
| `scripts.ga4.list_ga4_purchase_transactions` | Print purchase-item report | Fixed 1–7 July 2026; purchase filter; selected property |
| `scripts.ga4.list_ga4_purchase_events` | Print purchase-event report and response metadata | Same fixed dates/filter/property; grouped report, not raw events |
| `scripts.meta.test_meta_connection` | Print accessible ad accounts | Legacy live Graph API read; does not validate a full performance connection |
| `scripts.meta.list_campaigns` | Print campaign sample | First page only for the selected Steele account |
| `scripts.meta.list_adsets` | Print ad-set sample | First page only; an ad set groups targeting/delivery settings |
| `scripts.meta.list_ads` | Print ad sample | First page only |
| `scripts.meta.inspect_creative` | Print JSON for 15 selected creatives | Live read; creative means the content/configuration used by an ad |
| `scripts.meta.inspect_object_stories` | Inspect referenced posts; print and save results | Reads saved creative JSON and replaces `evidence/meta/object_stories_of_15_ads.json`; saved historical requests all failed permissions |
| `scripts.meta.authorize_meta` | Establish the unfinished personal user/Page-token flow | Opens Facebook Login and listens briefly on localhost port 8765; changes ignored credential files |

For schema discovery, `Product` is the requested object type; `ProductVariant`
and `Order` are other examples. `--output-dir` chooses the directory to write:

```bash
rtk proxy uv run python -m scripts.shopify.discover_shopify_type_fields Product --output-dir /tmp/pi-schema-check
```

This still makes a live read but writes the CSV to `/tmp/pi-schema-check` instead
of replacing retained evidence. Expect a field count and that saved path; inspect
the CSV headers and requested type to confirm the result. For other new
investigations, inspect fixed paths before running; do not overwrite historical
evidence to create a new sample.

The newer Meta report command and its tests live only on the archive branch.
They are not executable features of this checkout; see project state and history.

## Changes to file locations

The October cleanup changes paths, not the discovery logic or Python module
names. References inside preserved Word snapshots retain their historical paths.

| Previous location | Current location |
| --- | --- |
| `outputs/shopify_orders/` | `evidence/shopify/orders/` |
| `outputs/shopify_schema_fields/` and schema-script default `outputs/schema_fields/` | `evidence/shopify/schema-fields/` |
| `outputs/GA4_metadata/` | `evidence/ga4/` (`item_performace.txt` becomes `item-performance.txt`) |
| `outputs/meta_discovery/` | `evidence/meta/` |
| `outputs/discovery/` | `evidence/reconciliation/` |
| September Markdown handoff in `docs/` | `docs/project-state.md` |
| `docs/ga4_discovery_current_state.md` | `docs/research/ga4-findings.md` |
| Three Word documents directly under `docs/` | `docs/reference/` |
| `exports/` | Removed; learning/context packs belong outside the repository |

The two Word research/handoff files are July and September snapshots, not copies
that must be kept synchronized. The original product brief is a supplied
reference. The tracked Excel `~$` lock artifact is preserved but is not evidence
to analyze. Do not infer meaning from an ambiguous legacy filename alone.

## Keeping context useful

Maintain each fact in its owning document; project state can give a short summary
and link to detailed research. Record source, tested dates/settings, evidence,
checks, and limitations. Mark archived, historical, proposed, reported, and
uncommitted work honestly. Git preserves the full commit history; Markdown
history explains the significant changes without duplicating every minor edit.

For this checkout there is no automated test suite. Verify relevant script
changes offline where possible, and verify paths/links for documentation changes.
Live access, successful exports, and production readiness require separate
evidence. Never commit secrets or upload internal source/evidence without
authorization. Generate requested learning or sharing packs outside the repo;
do not recreate `exports/` or replace it with another pack folder.
