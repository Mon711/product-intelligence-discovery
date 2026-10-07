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
├── meta_discovery/            Meta token loading, Step 1 access checks and saved-ID audit
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

The new Step 1 command reads only the explicitly selected file (default
`config/meta/.env`), without terminal-environment overrides or legacy token
fallbacks. It requires `META_AD_ACCOUNT_ID=2313037395632947`, `META_APP_ID`,
`META_APP_SECRET`, and `META_USER_ACCESS_TOKEN`. `META_GRAPH_API_VERSION` defaults
to `v26.0`. It accepts only an ads-only User token with `ads_read` and optional
`public_profile`. Credentials remain in ignored local configuration.

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

### Meta connection discovery — Step 1 only

From this repository root, first check the saved July identifiers:

```bash
rtk proxy uv run python -m scripts.meta.discover_connections --offline
```

`--offline` reads the four saved Shopify/GA4 files only; it does not load Meta
credentials or contact any source. It creates a new timestamped folder under
`evidence/meta/access-checks/`, with a `summary.json`. Expect `PASSED`, 207/207
transaction matches, 326/326 item matches, and 25 absent Online Store orders.
It also compares original quantities; it does not investigate absent orders.

Then check current Meta access:

```bash
rtk proxy uv run python -m scripts.meta.discover_connections --stage access
```

`--stage access` is Step 1 and the default. After the saved
audit passes, it makes two GET reads: token validation and Steele account metadata.
Expect `Meta access: passed`, account `2313037395632947`, `AUD`,
`Australia/Sydney`, API version and granted permissions. No advertising objects
are collected or changed. Token validity, matching app, User-token type, permissions,
token expiry and data-access expiry must pass before the account read. Raw token-debug
responses and credential-bearing errors are not saved. Zero expiry means Meta
reported no scheduled expiry; it does not promise permanent access.

Open the printed `summary.json` path. For live success, overall `status`,
`foundation.status` and `meta.status` must all be `passed`, and all foundation
`checks` must be true. An offline success instead has `meta.status: not_requested`.
The report records UTC collection time, account currency/time zone, the historical
July window, input file paths and SHA-256 fingerprints (content identifiers).
It contains counts rather than individual order/customer records. Historical
Shopify/GA4 matches do not prove their current credentials work or establish Meta
attribution. Current Meta currency does not independently verify July GA4 currency.

A safe manual failure check uses an empty configuration source:

```bash
rtk proxy uv run python -m scripts.meta.discover_connections --config /dev/null
```

`--config` selects a different file; `/dev/null` supplies no configuration. Expect
`FAILED`, `Meta access: failed`, a Steele-account configuration error, and a new
failed summary. It never loads your real credentials or contacts Meta. Your
configuration and previous reports remain intact. The process returns exit code
1 for a failed check (0 for success); later stages such as `--stage creatives` are
rejected with code 2 before work starts.

Optional input/output overrides are `--evidence-root` (read a copied evidence
tree) and `--output-dir` (parent for a new run folder). A missing or malformed
saved input is a failure, not an empty successful dataset. A network, permission
or rate-limit rejection fails safely without automatic retries. Fix the reported
access issue before rerunning; never paste credentials into a chatbot.

Run the focused offline tests from the repository root:

```bash
rtk proxy uv run python -m unittest discover -s tests -v
```

`discover -s tests` finds the new standard-library test suite; `-v` prints each
test name. Expect 29 tests and `OK`. Tests use fake Meta responses and temporary
copies of saved evidence; they neither contact source APIs nor change retained
evidence/configuration. `uv run` may prepare the local environment/cache if needed.

Architecture: the command in `scripts/meta/discover_connections.py` coordinates
one step and writes a summary; `meta_discovery/foundation.py` parses saved files
and compares identifiers/quantities; `meta_discovery/reader.py` validates configuration,
sends restricted reads and returns only safe access metadata. The older token
loader and discovery scripts retain their existing behavior. No new dependencies
or discovery stages beyond Step 2 are introduced.

### Meta connection discovery — Step 2 sample

From the repository root, start with one ad:

```bash
rtk proxy uv run python -m scripts.meta.discover_connections --stage sample --max-ads 1
```

`--stage sample` selects Step 2. It rechecks saved July identifiers and validates
Meta access, then makes a paginated GET Insights report at ad level for **1–7 July
2026**. Each Insights row describes one ad across the whole seven-day account-local
window. Only identifiers, names, dates and impressions are requested: impressions
identify reported delivery, not conversion attribution. No breakdowns, daily rows,
conversion measures or attribution overrides are requested.

After all pages are collected, ads with positive impressions are eligible. Exact
names from the 15 saved creative examples receive priority; within each priority
group ads are sorted by numeric ID. Names are only a sampling hint, not a cross-source
matching key. `--max-ads 1` limits object collection to one ad and its parent ad set
and campaign; it still retrieves all Insights pages so selection is reproducible.
Each unique parent is read once. Creative reads stop at the reference `creative{id}`;
creative content, destination URLs, product sets and Page/posts remain later work.

Then collect the default sample of up to 15 ads:

```bash
rtk proxy uv run python -m scripts.meta.discover_connections --stage sample
```

Each run creates a new folder under `evidence/meta/samples/` without replacing
earlier evidence. `--max-ads` accepts only 1–15. `--offline` remains available only
for Step 1; combining it with `--stage sample` is rejected before work starts.
`--config`, `--evidence-root` and `--output-dir` retain their existing meanings.

**Verified on 6 October:** one complete Insights page returned 42 candidate ad rows.
The one-ad run used six GET requests; the default selected 15 ads, five ad sets and
five campaigns in 28 GET requests, with seven saved-name priorities and no hierarchy
gaps. These are dated observations, not hard-coded required counts. A smaller pool
may return fewer than the requested ads; a fully collected report with no positive
impressions explicitly reports an empty sample.

| Output | How to check it manually |
| --- | --- |
| `summary.json` | Overall status `passed`, Meta status `passed`, sample status `complete`, `insights_complete: true`, `issue_rows: 0` |
| `insights.json` | `complete: true`; requested July dates; period-level rows with account `2313037395632947`; selected ads must exist here with positive impressions |
| `sample.json` | Dates, requested fields, report settings, selection/reference fingerprint, selected rows, unique current objects, collection timestamps and limitations |
| `hierarchy.csv` | One row per selected ad, showing campaign → ad set → ad → creative ID; unique ad IDs, expected sample limit, row status `complete`, empty `issues` |

The CSV names are July Insights labels. Current object names/statuses are stored
separately in `sample.json`; they can change after July. Its `objects.ad` entry for
an ad must have matching parent IDs, and each referenced object must belong to
Steele. Missing optional fields remain null. In Meta Ads Manager, independently
select Steele's account and 1–7 July, locate a selected ad by its ID and compare
the seven-day impressions and parent IDs. Do not filter out currently paused ads
when checking historical delivery. The CSV impressions are repeated selection
evidence, not an analytics report or per-day values.

To verify failure without touching credentials or contacting Meta:

```bash
rtk proxy uv run python -m scripts.meta.discover_connections --stage sample --config /dev/null
```

Expect `FAILED`, a Steele-account configuration error, and exit code 1. Only a
failed summary is created; no sample objects are requested. An invalid size such
as `--max-ads 16` is rejected with exit code 2 before creating a folder/networking.

The reader follows only cursors against the same approved Insights address and
never follows or saves next-page URLs. Missing/repeated cursors, repeated ads,
wrong accounts/dates, rate limits, and network errors stop collection without
retries. Pages already saved remain labelled incomplete. Unavailable referenced
objects and changed parent relationships remain visible as gaps: sample status
`partial`, overall `failed`, exit code 1. A 50-page cap prevents unbounded paging;
a capped run cannot claim completeness.

`meta_discovery/sampling.py` owns deterministic selection, cached unique parent
reads, partial-result preservation and CSV/JSON output. `reader.py` extends the
existing GET gate only after access validation, and node reads are restricted to
IDs actually discovered in Steele Insights and chosen for the sample. The command
coordinates the stage. The Step 1 foundation checker and legacy scripts are unchanged.
Relevant field/GET definitions were checked against Meta's official
[account/Insights SDK source](https://github.com/facebook/facebook-python-business-sdk/blob/main/facebook_business/adobjects/adaccount.py)
and [ad SDK source](https://github.com/facebook/facebook-python-business-sdk/blob/main/facebook_business/adobjects/ad.py);
the live runs verify the requested fields for the configured v26.0 account.

The earlier full Meta report command and its separate tests live only on the archive branch.
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
