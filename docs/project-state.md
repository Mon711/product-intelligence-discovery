# Project state and discoveries

**Maintained:** 5 October 2026. **Checkout inspected:** `main` at `9a1afc4`,
with the organization change below still uncommitted. No live source queries
were made for this update. Dates below describe the evidence, not a guarantee
that credentials or reports work today.

## Purpose and current direction

Steele Product Intelligence (PI, also called Steele Intel) is Creatnet's effort
to support product, ecommerce, inventory, and marketing decisions. Shopify
describes commercial orders; Google Analytics 4 (GA4) describes captured website
behavior; Meta Ads describes advertising and the results Meta credits to it.

**Confirmed project direction:** the September handoff records a deal with
Project Tech4Dev to use Dalgo for aggregation (collecting source data together)
and the database foundation. Creatnet's stated remit is missing source
connectors, analytics, dashboards, product features, and later machine learning.
A connector is code or configuration that brings source data into a destination.
Needed production connectors belong in the Dalgo repository.

**Not established:** an operational Steele Dalgo connection, delivered database
or dashboard, exact connector coverage, hosting, access interface, contractual
scope, support, owners, milestones, or delivery timeline. The expected flow is
sources → Dalgo data foundation → Creatnet analytics and product work; that
handoff still needs validation.

This repository holds small Python discovery experiments and saved evidence.
It has no production service, database, scheduled ingestion, deployment, or
automated test suite on the inspected `main` revision. The archived Meta reader
has a separate test suite; see below.

The [original product brief](<reference/Steele Intel - Product Brief and Dev Roadmap.docx>)
remains useful for its leadership, ecommerce, marketing, and design/buying
audiences and proposed product goals. Its custom database architecture, staffing
estimates, technology choices, and 10–12-week schedule are historical proposals.
Dashboard foundations, image-analysis experiments, natural-language querying,
forecasting, and automated insights are goals, not implemented features here.

## Source access register

OAuth means signing in to grant an application access without sharing a login
password. A token is the credential used for subsequent requests. Local token
files establish configuration, not verified current access; never include their
contents in documentation.

| Source and target | Implemented on main | Supported evidence and last known limitation |
| --- | --- | --- |
| Shopify; store domain selected by ignored local configuration | Admin GraphQL client, shop connection check, field discovery, paginated order and order-line export | July saved export: 251 orders and 385 lines. The archived October handoff reports a 1 October refresh rejected with HTTP 401 (invalid credentials). Current access is unverified. The exact store domain is not asserted from secrets. |
| GA4 property `268350484` | Read-only OAuth; Admin account/property listing; Data API metadata, event, item, and purchase reports | July saved reports prove this property's populated ecommerce data. October archived documentation reports a fresh 1 October GA4 recheck against saved Shopify data. Current credentials are unverified. |
| GA4 property labels and streams | Main scripts target the property ID above | “Steele AU/NZ” and older “Steele Global” property `268365916` are earlier reported context; their saved Admin listing/stream configuration is absent. Exact account name, web stream, measurement ID, website URL, and old-property suitability remain unverified. |
| Meta Ads Steele account `2313037395632947` | Token loading, accessible-account check, first-page listings, 15-creative inspection | July evidence records three accessible accounts and first pages of 25 campaigns, 25 ad sets, and 25 ads. These are samples, not totals. October access and performance checks belong to archived work below. |
| Facebook Page `114421101975106` and object stories | Unfinished OAuth/Page-token and object-story experiments | All 15 saved metadata attempts and all 15 saved story requests failed with permission errors. Advertising access and Page content access are separate; these errors do not prove ads reporting is unavailable. |
| Dalgo | No configured connection demonstrated in this repository | Chosen platform direction; Steele source coverage and the technical data handoff still require evidence. |

### How source evidence is bounded

- Shopify's strongest export selects orders created on **1–7 July 2026**, using
  Melbourne-local boundaries represented in UTC. Order and line pagination are
  implemented. The export reads saved GA4 reports and overwrites fixed filenames.
- GA4's fixed purchase-event and purchase-item reports use the same inclusive
  dates, property `268350484`, and a `purchase` event filter. Saved event metadata
  records `Australia/Sydney`, no other-row loss, and no thresholding. Currency is
  not printed in that July metadata; AUD is reported in the October archived
  handoff rather than independently established by that saved metadata.
- GA4 event counts and item performance use a moving `7daysAgo`–`today` range;
  item performance intentionally returns only the top 50 rows. Metadata proves
  field availability, not that Steele populates every field. Reports are grouped
  tables, not raw logs of individual website events.
- Meta lists are first-page evidence. A creative is the content/configuration
  used by an ad; an object story is its referenced Facebook post. Saved failed
  story attempts establish an access limitation, not readable engagement data.

## Cross-source relationships and discoveries

These are **verified historical sample findings** supported by the saved July
files and [detailed research](research/ga4-findings.md). They are not universal
matching rules for every store, period, or property.

| Relationship or finding | Result in the 1–7 July sample | Interpretation and limits |
| --- | --- | --- |
| GA4 `transactionId` → Shopify numeric `legacyResourceId` | All 207 captured GA4 transaction IDs matched saved Shopify orders | Use IDs as keys; matching captured purchases does not prove complete website tracking. |
| GA4 `itemId` → Shopify product and variant IDs | Format `shopify_AU_{product_id}_{variant_id}`; all 326 captured transaction–variant pairs matched identity, labels, and original quantity | A variant is a product option such as size. Preserve the raw ID and validate its format elsewhere. Names are labels, not reliable keys. |
| GA4 purchased quantity → original Shopify `LineItem.quantity` | All 326 captured pairs matched | Later Shopify `currentQuantity` can change after returns or edits; it describes a different commercial state. |
| Website-purchase coverage | 206 of 231 Online Store orders captured: 89.2%; 25 absent in the fixed reports | Shopify also returned 16 Draft Orders, two Shop orders, and two returns-portal orders. Do not count those other channels as missing website purchases. Cause of the 25 absences is unknown. |
| GA4 purchase revenue → Shopify commercial amounts | At displayed cent precision, 184/207 matched current subtotal and 35/207 matched current total | Common A$10/A$12 differences are consistent with shipping, but tagging rules are unverified. GA4 is not authoritative for refunds, tax, shipping, or current financial state. |
| Meta campaign/ad → GA4 or Shopify purchase | No validated cross-source matching exists | Attribution means the rules for crediting marketing with a sale. Meta purchase totals alone cannot identify Shopify orders; tracking labels and identifier completeness need investigation. |

**Earlier comparison, 9–16 July:** a ShopifyQL sales-activity workbook matched
110/111 GA4 transaction IDs and all 159 matched order–variant pairs on identity
and quantity, but no item-revenue values exactly matched ShopifyQL net sales.
Sales activity includes reversals and activity for older orders. Its 62.9% ratio
must not be treated as a tracking-loss rate; the later order-creation comparison
answers a better-defined coverage question.

**Reported later check, 1 October:** the archived learning handoff at Git object
`cfa22bb:docs/Meta_Ads_Code_Learning_Handoff_2026-10-05.md` cites fresh GA4 results
of 207 transactions and 326 item rows against saved Shopify data; Shopify refresh
failed with HTTP 401. It references a prior chat, rather than providing a new
retained GA4 output in this checkout. This is not a fresh two-source comparison.
The saved summary of the 1 October discovery session
`01a0f71d-4bfe-7083-b20e-5aff7b519346` also reports a search of the 25 exact IDs over
25 June–20 July without matches. The summary was reviewed during this update,
but its original API output is not retained here: this is reported context,
not independently verified evidence. Another property's data,
alternate IDs, collection timing, and the actual cause remain open.

## Archived Meta reporting work

**Code location:** branch `archive/meta-ads-reporting-reader`, commit `cfa22bb`.
The code is absent from `main`; do not describe its command as available here.
It includes a restricted ads reader, paginated inventory collection, daily
performance reporting, unique run folders, and 23 offline tests. “Offline” means
tests use fake API responses instead of contacting Meta.

The archived October handoff **reports** a passed ads-only access check for the
expected account, `ads_read`, AUD, `Australia/Sydney`, API v26.0, and a 1 September
sample returning 38 ad/day rows. It also reports 23 passing tests. Those checks
were not rerun during this cleanup. A completed September export, agreement with
Ads Manager, full creative coverage, and cross-source joins are not established.

**Local evidence location:** stash `4db2afe` (full identity in change history),
whose third parent preserves untracked files. Its two run manifests were
inspected for status/counts only: both say `failed`. The first records 190
campaigns, 639 ad sets, and 3,114 ads; the second records 190 campaigns and 639 ad
sets. The archived handoff attributes failures to interrupted broad creative
work and a rate-limit rejection. A failed run is partial evidence, not a full
performance dataset. The revised reader's complete live run remains unverified.

The stash is local-only and is not included in an ordinary clone. Preserve it
and the archive branch; restoring either is a separate task. Rate-limit recovery
estimates in old notes are historical snapshots, not current countdowns.

## Evidence map and next investigations

| Location | Contents and how to use them |
| --- | --- |
| [Shopify field inventories](../evidence/shopify/schema-fields/) | Twelve API object field inventories; available fields do not prove populated values |
| [Shopify order evidence](../evidence/shopify/orders/) | Fixed July order and line CSVs; source for commercial state and identifier checks |
| [GA4 evidence](../evidence/ga4/) | Field metadata, top-50 item report, legacy purchase reports, and fixed July purchase reports; legacy filenames remain unchanged except the spelling correction |
| [Reconciliation evidence](../evidence/reconciliation/) | Fixed order comparison and earlier sales-activity workbook; the retained `~$` file is an Excel temporary lock artifact, not a research result |
| [Meta evidence](../evidence/meta/) | Early account/listing/creative samples and failed object-story requests; archived reader runs are in the separate stash |
| [Word references](reference/) | Original product brief, July GA4 report, and September handoff snapshots; edit the canonical Markdown rather than these snapshots |

Open saved data only to verify a relevant claim. Some files contain internal
order/ad records; keeping them locally does not authorize uploading them.

Next investigations depend on the task and fresh authorization:

1. Resolve source access and confirm target store/property/account before new
   reads. Keep ads access read-only; Page permissions are a separate question.
2. Inspect actual destination links and UTM parameters (campaign tracking labels
   in URLs) along both Meta → GA4 → Shopify and Meta → Shopify paths. Define
   attribution only after observing which identifiers survive.
3. Investigate the 25-order coverage gap, exact tagging/revenue semantics,
   populated traffic/funnel fields, and dimension/metric compatibility.
4. Confirm Dalgo connector coverage, historical data, refresh behavior, quality
   checks, and how Creatnet will read the data. Agree users, measures, and owners
   before calling a dashboard or connector delivered.

## Context ownership

Read [README](../README.md) for setup and folder purposes, [agent instructions](../AGENTS.md)
for working rules, [change history](change-history.md) for why work changed, and
the GA4 report for detailed reasoning. Update this file when project knowledge
changes; it is a compact shared summary, not a transcript or authorization log.
Historical public Dalgo references reviewed for the September handoff were the
[platform introduction](https://docs.dalgo.org/intro/) and
[source guide](https://docs.dalgo.org/self-serve-documentation/data-sources/adding-a-data-source/).
They describe the platform, not a configured Steele workspace; they were not
refreshed during this maintenance change.
