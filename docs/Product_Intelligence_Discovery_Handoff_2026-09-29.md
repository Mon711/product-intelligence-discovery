# Product Intelligence Discovery Handoff

**Steele Intel context for a new teammate or AI assistant 29 September 2026**

## Read this first

Product Intelligence, also called PI or Steele Intel in earlier files, is Creatnet's effort to help the Steele business make better product, e-commerce, inventory, and marketing decisions from data that currently sits in separate systems. The June 2026 product brief remains the direction for the product **except for its plan for Creatnet to design and run the aggregation database**. Creatnet has signed a deal with Project Tech4Dev to use its open-source platform, Dalgo, for data aggregation and the database. Creatnet remains responsible for custom source connectors if Dalgo lacks a needed integration, data analytics, dashboards and other product features, and later machine-learning (ML) pipelines. The exact contract, technical handoff, delivery sequence, hosting, and timeline are not recorded in this repository.

Product discovery continues. It means learning which decisions people need to make, what each data source can actually provide, how measures should be defined, where data disagrees, and how Creatnet's work will use the data aggregated in Dalgo. This work can be done through stakeholder conversations, source-system reports, official documentation, Dalgo demonstrations, and small evidence checks. The Python scripts in this repository remain useful starting points when a connector or detailed source check is needed; new discovery research does not have to involve code.

This document is a self-contained starting point. It distinguishes **confirmed current responsibilities**, **verified historical findings**, **product plans that still need delivery**, and **open questions**. A historical finding is a result observed in a particular test window; it is not a guarantee about today's data. Nothing in this repository proves that a production PI database, live dashboard, scheduled pipeline, or Dalgo integration has been delivered.

## What problem is the project trying to solve

Steele's commercial and behavioural information is spread across systems. **Shopify** records products, orders, payments, refunds, and current commercial state. **Google Analytics 4 (GA4)** records website interactions such as product views, cart actions, and captured purchases. **Meta Ads** records advertising objects and, where configured and accessible, campaign performance. A decision maker who wants to understand a product often has to compare these systems manually. Their numbers may differ because they measure different events, use different date and money rules, or miss some activity.

The product brief described four main audiences: leadership, e-commerce, marketing, and design/buying. Example decisions were which products merit more attention or stock, where a product attracts visitors but fails to convert, which campaigns and creatives are effective, and which product attributes perform repeatedly. These remain useful **product discovery prompts**. Their priority and exact first release still need confirmation with the current decision makers.

A useful first result would be a small set of trusted, clearly defined answers to the team's highest-priority recurring decisions. A chart is only useful if its source, date range, meaning, and known gaps are understandable. For example, “sales” might mean gross order value, current order total, or net sales after refunds; these are not interchangeable.

## How the plan changed

The `docs/Steele Intel - Product Brief and Dev Roadmap.docx` was drafted in June 2026. It proposed Shopify, GA4, and Meta integrations; a governed database; daily refresh jobs; dashboards; later natural-language querying, automated insights, and image analysis. **Its product goals largely remain relevant.** The change is who provides the aggregation and database foundation: Dalgo takes that responsibility, while Creatnet owns the product and analytics work around it and builds missing connectors when needed. The brief's Phase 1 estimate of 10–12 calendar weeks depended on the former staffing and architecture assumptions, so it is not a verified current schedule. Meeting notes embedded in the file discussed Django, a frontend choice, Neon Postgres, and saved dashboard layouts; those technology choices need review against the Dalgo arrangement.

| Topic | Earlier brief | Current responsibility or status |
| --- | --- | --- |
| Data aggregation and database | Creatnet designs and operates the central data foundation | Dalgo handles aggregation and the database; its exact setup and data handoff need confirmation |
| Source connectors | Custom integrations were part of the build | Use Dalgo's integrations where they meet requirements; Creatnet builds a missing Shopify, GA4, Meta, or other connector in the Dalgo repository if required |
| Analytics and dashboards | Creatnet builds decision-ready reporting and product views | Remain Creatnet's work; confirm first users, metrics, and release scope |
| Later intelligence | Natural-language querying, ML, and image analysis follow the foundation | Remain in the product direction and Creatnet's remit; timing and acceptance criteria need review |
| This repository | Early source exploration before development | Preserved evidence and reusable experiments; any needed production connector belongs in the Dalgo repository |

**Use the brief for the product vision, user questions, analytics, dashboard, and later intelligence goals. Replace its custom database and aggregation design with the Dalgo arrangement.** Treat its schedule and specific technology choices as proposals until they are updated with Tech4Dev and the Creatnet team.

The expected division of work is: **source systems → Dalgo integration or a Creatnet-built connector in the Dalgo repository → Dalgo aggregation and database → Creatnet analytics, dashboards, and later intelligence features**. The interface between Dalgo's stored data and Creatnet's product still needs to be designed and tested.

## What this repository contains and what has been done

The repository began in June 2026 as a small **discovery-only** Python project. “Discovery” here means short experiments to learn about source access, available fields, identifiers, and data quality. It is not an application for business users. There is no production database, automated ingestion, live dashboard, deployed service, or automated test suite in this checkout.

From 21 June through 29 July 2026, the Git history shows a sequence of Shopify access and schema inspection, GA4 access and reports, Shopify–GA4 reconciliation, written GA4 findings, and early Meta exploration. There are saved CSV, text, JSON, and workbook outputs under `outputs/`. Some files represent only one page of API results or one fixed historical date range. The unfinished Meta OAuth and object-story experiments were preserved in a separate work-in-progress commit; they are evidence of an interrupted investigation, not a complete connector.

### Repository reading map

| Location | What it is for | How to read it now |
| --- | --- | --- |
| `README.md` | How the discovery scripts and local configuration work | Technical guide; read its build phases with the Dalgo responsibility split in mind |
| `docs/Steele Intel - Product Brief and Dev Roadmap.docx` | Product vision, users, proposed metrics, phases, and meeting notes | Product direction remains relevant; custom database design and old estimates need revision |
| `docs/ga4_discovery_current_state.md` and `docs/GA4_Discovery_Current_State.docx` | Detailed GA4 investigation as of 21 July 2026 | Best source for definitions, calculations, and caveats |
| `shopify_discovery/`, `ga4_discovery/`, `meta_discovery/` | Shared configuration, authentication, and API request helpers | Research code that can inform Creatnet-built connectors if needed |
| `scripts/shopify/`, `scripts/ga4/`, `scripts/meta/` | One-purpose source inspection and report scripts | Inspect before reusing: some dates, IDs, and paths are fixed |
| `outputs/shopify_schema_fields/` | 12 Shopify GraphQL type-field inventories | Available API fields, not proof that every field is populated |
| `outputs/shopify_orders/` and `outputs/discovery/` | July order exports and two comparisons with GA4 | Strongest saved cross-source evidence |
| `outputs/GA4_metadata/` | GA4 metadata and saved item/purchase report text | Historical report snapshots |
| `outputs/meta_discovery/` | Account, first-page listing, 15-creative, and object-story attempts | Early access and structure evidence; no complete performance extract |

The source credential files under `config/` are local and ignored by Git. They are not needed to read this handoff. Never paste tokens, secrets, customer-level exports, or raw object responses into an external AI service without the appropriate internal data-use approval.

### Shopify work completed

The Shopify Admin GraphQL API connection was tested. A reusable client and scripts were added to inspect API object fields and export orders. The saved field inventories cover Product, ProductVariant, Order, LineItem, Refund, Collection, inventory-related objects, media, options, and Customer. This was **schema discovery**: it tells us what the API can expose, not which columns the future platform should ingest or how complete Steele's values are.

The strongest Shopify export selected orders **created from 1 through 7 July 2026 in Melbourne local dates**. It saved 251 order rows and 385 order-line rows. The order extract includes channel/application, timestamps, status, payment, shipping country, discounts, tax, shipping, refund, and current totals, while the line extract includes product and variant IDs, names, original quantity, current quantity, and prices. These are research snapshots, not current business totals.

### GA4 work completed

The project established read-only OAuth access and used the GA4 Admin and Data APIs. The saved Data API experiments target property `268350484`, identified in earlier notes as Steele AU/NZ. They inspected available dimensions and metrics and produced item-performance and purchase reports. Tested item measures include item views, add-to-cart units, purchased units, and item revenue; tested purchase measures include transaction ID, purchase count, and purchase revenue. An event-count investigation recorded standard funnel event names, but its raw output was not saved. The item-performance script returns only the top 50 rows by views over a moving date window.

There are important **gaps**. A GA4 metadata list means a field exists in GA4 generally; it does not prove Steele sends useful values. Traffic source, medium, campaigns, landing pages, sessions, site search terms, device/geography, and checkout by product were not saved in tested Steele reports. The exact web stream, measurement ID, property settings, and currency configuration were not captured. GA4 Data API reports are grouped tables, not a complete log of every browser event.

### Meta Ads work completed

At the September handoff, Meta work had only just begun when the project paused. The historical files below show preparatory access and object-structure checks, not a completed source discovery.

The saved results show access to three Meta ad accounts and first pages of 25 campaigns, 25 ad sets, and 25 ads for the selected Steele account. These are **first pages**, so the counts are not totals. A comparison of 15 selected ad creatives saved fields such as creative ID, name, thumbnail, object type, URL tags, object-story reference, and, where present, asset-feed or story specifications. This helps identify how ad and creative objects are related.

An OAuth flow and object-story script were added as an explicitly unfinished experiment. The saved object-story file contains 15 attempted examples, each with an object-story ID, but **all 15 metadata requests and all 15 object-story requests failed with HTTP 400 permission errors referencing pages_read_engagement or Page Public Content Access**. The file therefore documents an access limitation, not retrieved engagement, post, comment, or media detail. This does not establish whether the correct permission was approved, granted to the current user, or usable for these objects. No saved Meta spend, impression, click, purchase, ROAS, or full pagination study supports a marketing-performance dashboard yet.

### Meta reader update — 5 October 2026

A separate local ads-only reader now lives in `meta_discovery/reader.py`, with evidence export in `meta_discovery/reporting.py` and the command `scripts.meta.export_ads_report`. It locks configuration to Steele ad account `2313037395632947` and app `2262542241238863`, validates a user token with only `ads_read` and optional `public_profile`, allows only approved GET endpoints/fields, ignores pagination URLs, redacts credential-bearing details, and saves new JSON/CSV runs with completion/failure manifests. It uses the existing Python environment and dependencies. The older Page-dependent OAuth experiment remains separate.

Live checks on 5 October confirmed valid advertising access, AUD currency, and Australia/Sydney time zone using the configured API v26.0. A GET Insights request for **1 September 2026** returned **38 ad/day rows**, including spend, impressions, clicks, purchase-related actions/values, and website purchase ROAS. Those checks prove that the selected report fields are available for that sample; they do not prove agreement with Ads Manager, completeness of purchase tracking, or matching to Shopify orders.

The initial inventory run collected **190 campaigns across 2 pages, 639 ad sets across 7 pages, and 3,114 ads across 32 pages**, under Meta's default status coverage. Its broad creative-library request was interrupted; the subsequent attempt was rate-limited with Meta code `80004`. Meta's numeric headers reported exhausted processing-time allowance (`total_cputime: 101`) and an estimated **51 minutes** to regain access at the last check. These are run-specific observations, not a permanent service limit. Both partial runs under `outputs/meta_discovery/reports/` are marked **failed**, and **no full September performance export has been verified**.

The final reader requests up to 500 basic inventory rows per page, divides insights into inclusive seven-day windows, and reads only unique creative IDs referenced by collected ads with reported delivery in the requested window. This avoids unrelated creative-library entries. Optional creative access failures are recorded without requesting broader permissions. The revised creative path and complete month export have offline coverage but remain unverified live until the API allowance recovers. Reports preserve date/settings/currency/time-zone metadata, missing values, distinct action types, and the distinction between current creative inventory and historical performance. No reach sum is produced. See the README's Meta Ads section for commands and interpretation.

This dated update applies to the Markdown handoff. Its companion DOCX remains the original 29 September snapshot. No production connector, database, schedule, advertising mutation, or conversion-event submission was added.

## The strongest findings across sources

The 1–7 July 2026 Shopify–GA4 comparison is the clearest completed data-quality test. A **transaction ID** is the identifier sent with a purchase. In this test, all **207** GA4 transaction IDs matched Shopify's numeric order IDs. A **variant** is a particular size or other option of a product. All **326** captured transaction–variant combinations matched Shopify's product ID, variant ID, product name, variant name, and original purchased quantity. The tested GA4 item ID had the form `shopify_AU_{product_id}_{variant_id}`. Preserve the raw ID and verify the format for other periods or stores before relying on the pattern everywhere.

The same comparison found **231 Online Store orders** created in Shopify in that week. GA4 showed **206** of them in both fixed-window purchase reports: **89.2% coverage**. The other **25** were absent from those reports in that window. Shopify also had 16 Draft Orders, two Shop orders, and two returns-portal orders; these other channels should not be counted as missing website purchases. The 25 absent Online Store orders were paid, non-test, not cancelled or edited, and had no refund recorded in the export. Their gateways, countries, product shapes, and dates did not reveal one simple shared cause.

This is a **window-specific discrepancy**, not a confirmed 10.8% permanent tracking loss. The 25 order IDs have not been searched across a wider GA4 date range, an older property, or alternate transaction-ID formats. Browser consent, blocking, delayed tracking, or a different property are possibilities, not diagnoses.

GA4 captured the quantity at the original purchase, even where Shopify's **current quantity** later changed after returns or edits. For 184 of 207 captured orders, GA4 purchase revenue equalled Shopify's current subtotal; it equalled current total for only 35. Common A$10 and A$12 differences from total were consistent with shipping being outside GA4's value, but the exact site tagging rules have not been inspected. **Shopify remains the commercial authority** for orders, refunds, tax, shipping, and current financial state. GA4 remains the behavioural and attribution source, including purchases that it captured. A future report must define its money measures before combining them.

An earlier **9–16 July 2026** workbook compared ShopifyQL sales activity with GA4 item data. It found strong IDs and quantities for matched rows: 110 of 111 GA4 transaction IDs matched Shopify order IDs, and all 159 matched order–variant pairs agreed on identity and quantity. It also found zero exact matches between GA4 item revenue and ShopifyQL net sales for those rows. This was a useful warning about definitions. ShopifyQL `FROM sales` includes sales and reversal activity posted during the window, including activity for older orders; `net_items_sold` is not a count of new orders. Its observed 62.9% purchase-like ID ratio should **not** be reused as a final tracking-loss rate. The later GraphQL comparison selected orders by creation date to answer a better-defined coverage question.

## What remains unknown

**Business and product.** The brief supplies candidate users, decisions, dashboards, and success measures, but their priority, first release, rollout sequence, and decision owners have not been reconfirmed since the Dalgo switch.

**Agreement and operating model.** Dalgo owns aggregation and the database foundation; Creatnet owns missing custom connectors, analytics, dashboards, and later intelligence work. This repository does not contain the Creatnet–Tech4Dev agreement or its technical scope. Hosting, integration configuration, data refreshes, the boundary between warehouse preparation and product analytics, database access, support, cost, and milestones still need confirmation.

**Source coverage.** No source-by-source Dalgo proof exists here for Shopify, GA4, or Meta Ads. If a required integration is unavailable or insufficient, Creatnet will build a custom connector in the Dalgo repository. Before making that decision, check whether the specific Steele account, permissions, required fields, refresh schedule, history, and commercial definitions work through Dalgo's existing options. Microsoft Clarity, Klaviyo, Xero, and other systems were mentioned in old planning but were not explored in this repository.

**Quality and semantics.** The 25-order GA4 discrepancy remains open; so do traffic and campaign attribution, currency, refund handling, checkout granularity, inventory history, product attribute definitions, and Meta performance coverage. Cross-source charts may mislead until these are defined and tested.

**Current operations.** The saved July outputs are snapshots. No live API was called for this handoff. They should not be used as today's performance report or as proof that credentials still work.

## What Dalgo publicly appears to offer

As of this handoff, the public [Dalgo GitHub organization](https://github.com/DalgoT4D) identifies Dalgo as Project Tech4Dev's open-source data platform for the social sector and links its backend, frontend, documentation, and roadmap. Its overview describes ingestion, scheduled runs, transformations, and visualisation in a web interface. The [Dalgo introduction](https://docs.dalgo.org/intro/) describes a warehouse, data cleaning and joining with dbt, charts, dashboards, reports, and monitoring. A [Dalgo source guide](https://docs.dalgo.org/self-serve-documentation/data-sources/adding-a-data-source/) distinguishes a **source** (saved access to an external system) from a **connection** (which tables or streams are synced). These are public descriptions of the platform, **not evidence of Creatnet's configured workspace, connector coverage, or contracted features**. Dalgo's public visualisation features do not change the project owner's stated division of responsibility for Creatnet's analytics and product work.

Dalgo's public history also shows a shift toward helping teams use data in regular decisions, with native charts and dashboards described in a [Tech4Dev Dalgo 2.0 article](https://projecttech4dev.org/dalgo-2-0-from-pipelines-to-actionable-insights/). That is potentially relevant to a discovery process focused on business questions. Confirm the exact product version, features, permissions, and support included in Creatnet's arrangement directly with Tech4Dev.

## Glossary for new readers

**API** means an interface through which one program asks another for data; the scripts used Shopify, Google, and Meta APIs to learn what each would return. **Schema** means the available fields and their types; a field appearing in a schema does not mean Steele fills it in. **Connector** means the configured route that reads data from a source. **Warehouse** means the place where copied and prepared data can be joined and queried. **Transformation** means cleaning or reshaping source data into measures people can use. **Reconciliation** means comparing two sources over a clearly defined population and date range to find agreements and differences. **Grain** means what one row represents, such as an order, order line, product per day, or campaign per day. **Attribution** means the rules a platform uses to credit a visit or purchase to a marketing source. **Source of authority** means the system trusted for a particular fact; Shopify is the commercial authority here, while GA4 describes captured website behaviour.

## Evidence and reading order

For a quick restart, read this document, then the `docs/Steele Intel - Product Brief and Dev Roadmap.docx` for the largely unchanged product vision, then `README.md` for repository mechanics, and `docs/ga4_discovery_current_state.md` for detailed Shopify–GA4 reasoning. Use this handoff to override the brief's custom aggregation/database architecture and old schedule. Open saved outputs only when checking a specific claim; some contain order-level or ad-level records. The most important local evidence is:

- `outputs/discovery/shopify_ga4_order_reconciliation_2026-07-01_to_2026-07-07.csv`, plus the matching order and order-line CSVs under `outputs/shopify_orders/`.
- `outputs/GA4_metadata/purchase_events_2026-07-01_to_2026-07-07.txt` and `purchase_items_2026-07-01_to_2026-07-07.txt`.
- `outputs/discovery/Shopify_GA4_purchase_reconciliation_2026-07-09_to_2026-07-16.xlsx`, especially its Notes sheet, for the earlier comparison and its limitations.
- `outputs/meta_discovery/list_creatives_of_15_ads.json` and `object_stories_of_15_ads.json` for the unfinished Meta exploration and permission failure.

Public Dalgo references reviewed on 29 September 2026: [GitHub organization](https://github.com/DalgoT4D), [platform introduction](https://docs.dalgo.org/intro/), [adding a data source](https://docs.dalgo.org/self-serve-documentation/data-sources/adding-a-data-source/), and [Tech4Dev's Dalgo 2.0 overview](https://projecttech4dev.org/dalgo-2-0-from-pipelines-to-actionable-insights/). Public descriptions can change. The project owner's responsibility split stated above is the current project direction; the agreement and live workspace will define the technical delivery details.
