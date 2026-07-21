# GA4 Discovery — Current State

**Steele Intel Product Intelligence Platform**  
**Document status:** Current discovery snapshot — research is still in progress  
**Last updated:** 21 July 2026  
**Prepared for:** Karan and the Product Intelligence database-design team

> This document separates confirmed project evidence from reasonable inference and open work. A field being available in GA4 metadata does not mean Steele is populating it, and an order being absent from one GA4 report window does not prove that it was never collected.

## Contents

1. Document purpose
2. Executive summary
3. Product Intelligence context
4. GA4 concepts needed for this discovery
5. GA4 access, accounts, properties, and APIs
6. Discovery approach and evidence reviewed
7. Verified dimensions and metrics
8. Product and variant identity findings
9. Purchase and transaction reconciliation findings
10. Recommended GA4 database model
11. Dashboard and insight use cases
12. Data-quality, attribution, and reconciliation considerations
13. Confirmed findings
14. Likely findings and assumptions
15. Open questions and unresolved issues
16. Recommended next discovery steps
17. Appendix A — scripts, outputs, and files reviewed
18. Appendix B — field and metric glossary

## 1. Document purpose

This document records what the Product Intelligence discovery project has reliably learned about Google Analytics 4 (GA4) for Steele so far. It is intended to help Karan design the GA4 portion of the Product Intelligence database without treating incomplete research as a finished specification.

The document answers four practical questions:

- What can the current GA4 integration retrieve?
- At what level of detail can the results be stored?
- How can GA4 product and purchase records connect to Shopify?
- What must still be tested before production database and dashboard decisions are finalised?

Every important conclusion is marked as one of the following:

- **Verified:** confirmed by repository code, saved API output, exported source data, or a direct comparison.
- **Likely:** strongly supported by the evidence, but not fully proved.
- **Unverified:** suggested by metadata, discussion, or external documentation but not tested on Steele data.
- **Open question:** requires a specific investigation.

## 2. Executive summary

**Verified — GA4 access and target property.** The repository successfully uses Google OAuth Desktop authentication with the read-only Analytics scope. All saved GA4 Data API reports target property `268350484`. The supplied discovery notes identify it as **Steele AU/NZ — GA4**. The repository does not retain the Admin API console output containing the account name, and it does not yet inspect the property's web data stream.

**Verified — useful ecommerce data exists.** Saved reports contain populated `itemId`, `itemName`, `itemVariant`, `itemsViewed`, `itemsAddedToCart`, `itemsPurchased`, `itemRevenue`, `transactionId`, `ecommercePurchases`, and `purchaseRevenue`. The event-count investigation also recorded standard product-funnel events such as `view_item`, `add_to_cart`, `begin_checkout`, and `purchase`, although the raw event-count output was not saved in the repository.

**Verified — product and variant mapping is strong.** In the tested Steele AU data, GA4 `itemId` follows `shopify_AU_{product_id}_{variant_id}`. In the fixed 1–7 July reconciliation, all **326** captured transaction–variant combinations matched Shopify on product ID, variant ID, product name, variant name, and original purchased quantity.

**Verified — transaction mapping is strong.** GA4 `transactionId` maps to Shopify's numeric order identifier (`legacyResourceId`). All **207** GA4 transaction IDs in the fixed 1–7 July report matched real Shopify orders. The event-level and item-level GA4 reports contained the same 207 transaction IDs, so none of the captured purchase events lacked item rows in this test.

**Verified — there is a selected-window coverage gap.** Shopify GraphQL returned **251** orders created during 1–7 July 2026: 231 Online Store, 16 Draft Orders, 2 Shop, and 2 Refundid/Returns Portal orders. GA4 contained 206 of the 231 Online Store orders, or **89.2%**. The remaining **25 Online Store orders (10.8%)** were absent from both the event-level and item-level GA4 reports for that same fixed window. This is an observed window-level gap, not proof that the transactions never appeared in another date window or property.

**Verified — captured purchase items are reliable, but GA4 is not the commercial ledger.** GA4 preserved original purchase quantities even where Shopify's current quantity later fell to zero. GA4 `purchaseRevenue` exactly matched Shopify's current subtotal for 184 of 207 captured orders, and the most common difference from Shopify's current total was A$10 or A$12, consistent with shipping being excluded. Shopify remains authoritative for order state, returns, refunds, shipping, tax, and current commercial totals; GA4 is the behavioural and attribution source.

**Open — the discovery is not yet broad enough for the final database.** Traffic source, medium, campaign, landing page, device, geography, site search, site-level traffic, and checkout metrics appear in the property metadata or discussion evidence, but have not been saved in tested Steele reports. Exact dimension/metric compatibility has not been checked. The 25 missing Online Store order IDs have not been searched across a wider date window or the older Global property.

### Database-design direction

The first production model should store separate facts for site-day, item-day, purchase, purchase-item, landing-page-day, traffic-source-day, and site-search-day data. It should also include explicit GA4-to-Shopify item mappings, transaction reconciliation results, ingestion jobs, data-quality checks, and metric definitions. GA4 facts should always retain `property_id`, report date, source field names, extraction window, and job lineage.

## 3. Product Intelligence context

The product brief describes a platform that combines Shopify, GA4, and Meta Ads into a governed database and dashboard layer. Shopify explains what was ordered and what later happened commercially. GA4 explains how people reached the site, which pages and products they interacted with, and where they progressed or dropped out of the purchase funnel. Meta Ads is expected to explain paid campaign and creative performance.

The brief also establishes several rules that directly affect GA4 design:

- The platform database should become the governed reporting layer, but each source still has an authoritative role.
- Metric definitions, time zones, currencies, and refund treatment must be explicit.
- Cross-source identifiers should use mapping tables and confidence flags rather than names or URLs alone.
- Daily refreshes and analytics-ready rollups are more important in Phase 1 than real-time complexity.
- Ingestion jobs and source reconciliation must be visible and auditable.
- The first model should remain practical for a small team and a low-cost Postgres deployment.

For this project, the source-of-truth hierarchy should be stated carefully:

- **Shopify:** authoritative source for orders, order lines, discounts, taxes, shipping, refunds, returns, cancellations, and current commercial state.
- **GA4:** behavioural and attribution source for traffic, engagement, product interaction, funnel activity, and captured purchase signals.
- **Product Intelligence database:** governed copy and semantic layer that combines these sources while preserving their different definitions and lineage.

## 4. GA4 concepts needed for this discovery

### 4.1 Property and data stream

A **GA4 property** is the reporting container queried by the Data API. A property can contain one or more web or app **data streams**, which identify where events are collected. The current code selects a property ID directly. The repository has not yet saved the stream ID, stream name, measurement ID, or website URL.

### 4.2 Event

An **event** is a named activity sent to GA4, such as `page_view`, `view_item`, `add_to_cart`, `begin_checkout`, or `purchase`. Event parameters provide details about that activity.

### 4.3 Dimension and metric

A **dimension** is a descriptive field used to group report rows, such as date, transaction ID, item ID, landing page, or traffic source. A **metric** is a number measured for that grouping, such as sessions, items viewed, purchases, or revenue.

The dimensions selected in a report determine its **grain**, meaning what one row represents. For example:

- `date` + `transactionId` produces one row per purchase transaction per day.
- `date` + `transactionId` + `itemId` produces one row per purchased item/variant within a transaction per day.
- `itemId` + `itemVariant` without date or transaction produces an item/variant summary over the whole requested date range.

### 4.4 Event scope, item scope, and session scope

GA4 ecommerce data uses different scopes. `transactionId` and purchase `value` describe the purchase event. `itemId`, `itemName`, `itemVariant`, item price, and item quantity describe entries in the purchase event's `items` array. Session fields such as `sessionSource` describe the session that brought the visitor.

Mixing scopes changes the meaning and sometimes the compatibility of a report. A working item report does not prove that the same item metrics can safely be combined with every landing-page, session, or campaign dimension.

### 4.5 API report versus raw event data

The current scripts use the GA4 Data API to request grouped report tables. These are analytics aggregates defined by the selected dimensions and metrics; they are not a stored copy of every raw browser event payload. This is appropriate for Phase 1 dashboard facts, but raw-event or journey-level ML requirements would need a separate architecture decision.

## 5. GA4 access, accounts, properties, and APIs

### 5.1 Authentication

**Verified.** [`ga4_discovery/auth.py`](../ga4_discovery/auth.py) uses:

- OAuth scope `https://www.googleapis.com/auth/analytics.readonly`;
- a desktop OAuth client file at `config/ga4/ga4_oauth_client.json`;
- a saved token at `config/ga4/ga4_token.json`;
- token refresh through `google.auth.transport.requests.Request`;
- an interactive local browser sign-in through `InstalledAppFlow.run_local_server(port=0)` when no valid refreshable token is available.

This is appropriate for discovery by an authorised user. A production scheduled ingestion service will need a separately approved credential and secret-management approach.

### 5.2 Accounts and properties discovered

| Evidence status | Account/property | What is known | What is not known |
|---|---|---|---|
| **Verified** | Property `268350484` | Every saved Data API script and output targets this property. Reports returned populated Steele ecommerce data. | The saved Admin API output, stream ID, stream URL, measurement ID, and property configuration are not retained. |
| **Likely** | “Steele AU/NZ — GA4” | This display name and the decision to use it are recorded in the supplied discovery notes. | The display name is not present in a saved Admin API output file. |
| **Likely** | Older “Steele Global” property `268365916` | The notes state that this property represents an outdated website and propose searching it for missing transactions. | No repository script output validates its display name, stream, current traffic, or suitability. |
| **Open question** | GA4 account name and full property list | [`scripts/ga4/list_ga4_properties.py`](../scripts/ga4/list_ga4_properties.py) prints accessible accounts and properties. | Its output was not saved, so this document cannot reliably name the account or claim the list is complete. |

### 5.3 Why property `268350484` was selected

**Verified:** it is the property used by all working reports and contains current-looking Steele AU product and purchase data.

**Likely:** the supplied notes say the old Global property tracks an outdated website. This selection rationale should be confirmed by saving both properties' data-stream configuration and recent activity before production ingestion is locked down.

### 5.4 Admin API versus Data API in this project

| API | Current project use | Simple explanation | Evidence |
|---|---|---|---|
| GA4 Admin API | Lists account and property summaries | Reads GA4 configuration and containers: which accounts/properties exist and, in future, which streams/settings belong to them. | [`scripts/ga4/list_ga4_properties.py`](../scripts/ga4/list_ga4_properties.py) uses `AnalyticsAdminServiceClient`. |
| GA4 Data API | Runs reports and reads report metadata | Returns analytics tables made from selected dimensions, metrics, filters, and date ranges. | All item, event, purchase, and metadata scripts use `BetaAnalyticsDataClient`. |

Official supporting context: the [Admin API](https://developers.google.com/analytics/devguides/config/admin/v1) manages and reads Analytics configuration, while the [Data API](https://developers.google.com/analytics/devguides/reporting/data/v1) produces reporting data.

## 6. Discovery approach and evidence reviewed

The discovery proceeded in increasing levels of reliability:

1. Authenticate with GA4 and list accessible properties.
2. Inspect property metadata to learn supported field names.
3. Run event-count and item-performance reports to confirm that ecommerce and engagement data is populated.
4. Run item-level purchase reports containing transaction and product identifiers.
5. Compare a moving-window GA4 item report with a ShopifyQL sales report. This exposed definition and date-window problems.
6. Replace ShopifyQL with a Shopify Admin GraphQL export of actual orders created in a fixed Melbourne-local period.
7. Compare fixed-date GA4 purchase-event and purchase-item reports with Shopify orders and order lines.

The final two fixed-date comparisons are the strongest evidence because they align the question, source grain, and date window.

### 6.1 Evidence strength

- **Primary repository evidence:** current scripts, saved GA4 text outputs, Shopify order/order-line CSVs, and the fixed reconciliation CSV.
- **Secondary repository evidence:** the earlier July 9–16 reconciliation workbook based on ShopifyQL sales activity.
- **Provided context:** the ChatGPT conversation-output notes and the Steele Intel product brief.
- **Supporting external context:** official Google Analytics and Shopify documentation, used only to clarify field definitions and platform behaviour.

No live API calls were made while preparing this document.

## 7. Verified dimensions and metrics

### 7.1 Tested field inventory

The table below focuses on fields that were actually used in successful project reports. “Saved output” is stronger than “documented execution” because the returned rows can be inspected directly in the repository.

<!-- LANDSCAPE_START -->

| GA4 field | Type | Simple meaning | Grain when tested | Tested status | Product Intelligence use | Shopify relationship | Caveats |
|---|---|---|---|---|---|---|---|
| `eventName` | Dimension | Name of the tracked activity | Event type over a date range | **Verified — documented execution** | Establish which funnel and engagement events exist | No direct key | Raw event-count output was not saved. |
| `eventCount` | Metric | Number of times an event occurred | Event type over a date range | **Verified — documented execution** | Event-volume and instrumentation checks | Compare only after definitions align | Current script uses a moving inclusive range. |
| `date` | Dimension | GA4 reporting date | Day | **Verified — saved output** | Daily facts and reconciliation | Compared with Shopify Melbourne-created date | Property report timezone returned `Australia/Sydney`. |
| `transactionId` | Dimension | Ecommerce transaction identifier | Transaction/day; transaction-item/day | **Verified — saved output** | Purchase facts and order reconciliation | Equals Shopify numeric order ID in all 207 fixed-window matches | Search beyond the selected window is still pending. |
| `itemId` | Dimension | Identifier sent for an ecommerce item | Item/variant; transaction-item | **Verified — saved output** | Variant-level product facts | Parses to Shopify product and variant IDs | Format is implementation-specific and must be validated. |
| `itemName` | Dimension | Name sent for the ecommerce item | Item/variant; transaction-item | **Verified — saved output** | Human-readable product analysis | Matched Shopify title for 326/326 fixed-window pairs | Names can change and are not safe keys. |
| `itemVariant` | Dimension | Specific variation, such as size | Item/variant; transaction-item | **Verified — saved output** | Size/variant performance | Matched Shopify variant title for 326/326 pairs | Variant labels are not stable identifiers. |
| `itemsViewed` | Metric | Quantity of item units included in `view_item` events | Item/variant over report range | **Verified — saved top-50 output** | Product interest and funnel entry | Join through parsed item ID | Current script returns only 50 item rows. |
| `itemsAddedToCart` | Metric | Quantity of item units in `add_to_cart` events | Item/variant over report range | **Verified — saved top-50 output** | Add-to-cart demand and drop-off | Join through parsed item ID | Quantity count, not unique users. |
| `itemsPurchased` | Metric | Quantity of item units in purchase events | Item/variant; transaction-item | **Verified — saved output** | Product purchase quantity | Matches Shopify original `LineItem.quantity`, not `currentQuantity` | Purchase-only filter excludes refund events from the tested extract. |
| `itemRevenue` | Metric | Item price × quantity, excluding event-level shipping and tax | Item/variant; transaction-item | **Verified — saved output** | Product purchase-value signal | Not equivalent to Shopify `net_sales` | Payload discount/tax treatment still needs explicit validation. |
| `ecommercePurchases` | Metric | Count of completed `purchase` events | Transaction/day | **Verified — saved output** | Captured purchase count and event-level reconciliation | One per captured Shopify order in the fixed test | GA4 capture is not complete for all Online Store orders. |
| `purchaseRevenue` | Metric | Purchase-event revenue supplied through the event `value` | Transaction/day | **Verified — saved output** | Captured order-value signal | Matched Shopify current subtotal for 184/207 captured orders | Not authoritative for shipping, tax, refunds, or final order state. |

<!-- LANDSCAPE_END -->

### 7.2 Events observed

**Verified through documented script output, but raw output not retained:** `view_item`, `add_to_cart`, `begin_checkout`, `add_payment_info`, `purchase`, `page_view`, `scroll`, `session_start`, `user_engagement`, `search`, `view_search_results`, and the custom event `Covet.pics Gallery View` were recorded in the supplied discovery notes.

This proves that the property receives multiple funnel and engagement event types. It does not prove that every event has all expected parameters, that counts are complete, or that fields can be grouped at product level.

### 7.3 Metadata-supported fields that remain untested on Steele data

The saved metadata output contains 1,870 lines and confirms that the Data API exposes many relevant standard fields. The following subset is directly useful to Product Intelligence, but availability in metadata is not proof of population.

<!-- LANDSCAPE_START -->

| GA4 field | Type | Simple meaning | Likely grain | Tested status | Product Intelligence use | Shopify relationship | Caveats |
|---|---|---|---|---|---|---|---|
| `currencyCode` | Dimension | Currency sent with an ecommerce event | Event/transaction | **Unverified — metadata only** | Multi-currency controls | Compare with Shopify shop/presentment currency | Not requested in saved reports. |
| `itemBrand` | Dimension | Brand sent for an item | Item | **Unverified — metadata only** | Brand-level performance | Could compare with Shopify vendor/brand | Population and naming rules unknown. |
| `itemCategory`–`itemCategory5` | Dimension | Hierarchical item categories | Item | **Unverified — metadata only** | Category/silhouette-style analysis | Could map to Shopify taxonomy/collections | Steele population and semantics unknown. |
| `itemListId`, `itemListName` | Dimension | List or collection context in which an item appeared | Item interaction | **Unverified — metadata only** | Collection/list placement analysis | Possible Shopify collection mapping | Attribution through later funnel steps must be tested. |
| `landingPage` | Dimension | First page path in a session | Session/landing page | **Unverified — metadata only** | Landing-page performance | Product URL mapping may be possible | URL changes and query strings make it a weak product key. |
| `pagePath`, `pageTitle`, `unifiedPagePathScreen` | Dimension | Page where activity occurred | Page/event | **Unverified — metadata only** | Page and product-page analysis | May map to Shopify handles/URLs | Exact product-page conventions and compatibility untested. |
| `sessionSource`, `sessionMedium`, `sessionSourceMedium` | Dimension | Source/medium that initiated a session | Session | **Unverified — metadata only** | Channel and attribution reporting | Relates to Shopify order attribution, not a stable order key | GA4 attribution rules and compatibility must be documented. |
| `sessionCampaignName`, `sessionDefaultChannelGroup` | Dimension | Campaign and channel grouping for the session | Session | **Unverified — metadata only** | Marketing and funnel segmentation | Can be compared with Shopify/Meta at aggregate level | Naming, missing values, and cross-source definitions unresolved. |
| `deviceCategory`, `country` | Dimension | Device class and inferred country | User/session/event aggregate | **Unverified — metadata only** | Segment funnel and diagnose coverage | Shopify has shipping country, not the same concept | Privacy/thresholding and semantic differences apply. |
| `searchTerm` | Dimension | Term searched on the site | Search event | **Unverified — metadata only** | Site-search demand and unmet-interest analysis | Can lead to product/category insights | `search` events exist, but term population is not tested. |
| `sessions`, `activeUsers`, `engagedSessions`, `screenPageViews` | Metric | Site traffic and engagement counts | Property/day plus chosen dimensions | **Unverified — metadata only** | Site-day and landing-page dashboards | No direct Shopify key | User/session metrics may be approximated and attribution-sensitive. |
| `addToCarts`, `checkouts` | Metric | Cart additions and checkout starts | Property/day plus compatible dimensions | **Unverified — metadata only** | Site-level funnel | Compare only as behaviour, not order state | Item-level compatibility and population need testing. |
| `cartToViewRate`, `purchaseToViewRate` | Metric | GA4 user-based item funnel rates | Compatible item grouping | **Unverified — metadata only** | Product conversion diagnostics | Join through item mapping if compatible | Not the same as quantity ratios calculated from tested item metrics. |

<!-- LANDSCAPE_END -->

### 7.4 Known-compatible report bundles

The following combinations have successfully returned data:

1. `eventName` with `eventCount`.
2. `itemId`, `itemName`, `itemVariant` with `itemsViewed`, `itemsAddedToCart`, `itemsPurchased`, `itemRevenue`.
3. `date`, `transactionId`, `itemName`, `itemId`, `itemVariant` with `itemsPurchased`, `itemRevenue`, filtered to `eventName = purchase`.
4. `date`, `transactionId` with `ecommercePurchases`, `purchaseRevenue`, filtered to `eventName = purchase`.

**Open question — incompatible fields.** The repository does not contain a `checkCompatibility` script or saved compatibility output. Therefore, no specific untested pair should be declared compatible or incompatible. In particular, item-scoped dimensions should not yet be combined blindly with landing-page, session-source, campaign, geography, or user metrics. Google's official [`checkCompatibility`](https://developers.google.com/analytics/devguides/reporting/data/v1/rest/v1beta/properties/checkCompatibility) method should be run for each proposed production report bundle.

## 8. Product and variant identity findings

### 8.1 Verified identifier pattern

**Verified.** The saved outputs repeatedly use this format:

```text
shopify_AU_{shopify_product_id}_{shopify_variant_id}
```

Example:

```text
shopify_AU_8079982592139_45560627265675
```

This parses to:

- Shopify product ID `8079982592139`
- Shopify variant ID `45560627265675`
- source/store prefix `shopify_AU`

The fixed-window comparison provides the strongest validation: all 326 GA4 transaction–variant combinations found a Shopify order line with the same product ID and variant ID, and all 326 also matched product name, variant name, and original quantity.

### 8.2 Mapping findings

<!-- LANDSCAPE_START -->

| GA4 identifier | Shopify identifier | Mapping method | Verified status | Reliability | Recommended database treatment |
|---|---|---|---|---|---|
| `itemId` full value | Product + variant context | Preserve raw string | **Verified** | High for tested Steele AU data | Store unchanged as `raw_ga4_item_id`; never discard the source value. |
| First numeric segment after `shopify_AU_` | Product `legacyResourceId` / numeric product ID | Parse validated pattern | **Verified: 326/326 fixed-window matches** | High, subject to format validation | Store parsed `shopify_product_id`, parser version, and validation result. |
| Second numeric segment | Variant `legacyResourceId` / numeric variant ID | Parse validated pattern | **Verified: 326/326 fixed-window matches** | High, subject to format validation | Use as the preferred variant join; enforce source/store context. |
| Prefix `shopify_AU` | Store/source context | Parse prefix | **Likely** | Medium | Map through a source-store table; do not assume future regional prefixes. |
| `itemName` | Shopify product title | Exact comparison in fixed window | **Verified: 326/326** | Low as a long-term key | Keep as observed label and quality check, not a key. |
| `itemVariant` | Shopify variant title | Exact comparison in fixed window | **Verified: 326/326** | Low as a long-term key | Keep as observed label and quality check, not a key. |
| Product-page URL | Shopify handle/product | Not tested | **Unverified** | Low until conventions are tested | Use only as a secondary mapping signal with normalisation and validity dates. |

<!-- LANDSCAPE_END -->

### 8.3 Mapping risks

- Product and variant names can change, contain formatting differences, or be reused. They are useful for validation but unsafe as durable keys.
- URLs can change with handles, redirects, locale, domain, and query strings.
- A parsed pattern is still an implementation convention, not a GA4 standard. Blank values, `(not set)`, malformed values, legacy formats, and future regional prefixes must be retained and classified.
- The current mapping is verified for the Steele AU property and observed period, not for every historical record or another store/property.
- Shopify GraphQL IDs can appear as `gid://shopify/...`; the tested GA4 pattern uses numeric legacy IDs. The database should store both forms where useful and make the conversion explicit.

### 8.4 Recommended mapping table

A practical mapping table should include:

```text
property_id
raw_ga4_item_id
store_prefix
parsed_shopify_product_id
parsed_shopify_variant_id
matched_dim_product_id
matched_dim_variant_id
mapping_method
mapping_status
confidence
first_seen_date
last_seen_date
parser_version
validation_notes
```

Recommended statuses include `exact_id_match`, `valid_pattern_unmatched`, `malformed`, `blank_or_not_set`, `name_only_candidate`, and `retired_or_missing_shopify_record`.

## 9. Purchase and transaction reconciliation findings

### 9.1 What was compared

The strongest comparison uses these fixed 1–7 July 2026 sources:

- GA4 purchase-event rows: `date`, `transactionId`, `ecommercePurchases`, `purchaseRevenue`.
- GA4 purchase-item rows: `date`, `transactionId`, item fields, `itemsPurchased`, `itemRevenue`.
- Shopify Admin GraphQL orders selected by `createdAt` across exact UTC boundaries corresponding to Melbourne-local 1–7 July.
- Shopify order lines containing product/variant IDs, names, original `quantity`, current `currentQuantity`, and price fields.
- A reconciliation CSV classifying each Shopify order by presence in both GA4 reports.

The GA4 response reported `Australia/Sydney` as its reporting timezone. Shopify timestamps were converted to `Australia/Melbourne`. All 207 matched transactions had the same calendar date in this stable test period.

### 9.2 Order-level result

| Shopify source/application | Shopify orders created | Found in GA4 | Absent from selected GA4 window | Interpretation |
|---|---:|---:|---:|---|
| Online Store | 231 | 206 | **25** | The relevant browser-store coverage comparison. |
| Draft Orders | 16 | 1 | 15 | Most are not expected to follow a normal browser checkout; one exception did generate GA4. |
| Shop | 2 | 0 | 2 | Separate commerce channel, not proof of a website-tracking failure. |
| Refundid: Returns Portal | 2 | 0 | 2 | App-created/returns workflow, not a normal browser purchase path. |
| **Total** | **251** | **207** | **44** | The total 44 must not be presented as 44 missing Online Store purchases. |

**Verified:** the selected-window Online Store capture rate was `206 / 231 = 89.2%`; 25 Online Store orders, or 10.8%, were absent from both fixed-window GA4 purchase reports.

### 9.3 What the 25 absent Online Store orders look like

**Verified from the exported Shopify order data:** all 25 were paid, non-test, not cancelled, not edited, and had zero refunded amount. Twenty-four were fulfilled and one was partially fulfilled. They included 34 line items across 27 products, 24 Australian shipping addresses and one Swiss address, and A$4,294.47 in current Shopify order value.

Payment-gateway rows were:

- 20 Shopify Payments;
- 2 Airwallex Afterpay;
- 1 Airwallex Afterpay plus gift card;
- 2 PayPal.

The same gateway families, products, variants, countries, single/multi-item shapes, and dates also occur among captured orders. No single available Shopify field explains the gap.

### 9.4 Transaction and item accuracy when GA4 captures a purchase

**Verified:**

- 207 GA4 event transaction IDs = 207 GA4 item-report transaction IDs.
- All 207 GA4 transaction IDs matched Shopify numeric order IDs.
- All 326 captured transaction–variant rows matched Shopify product ID and variant ID.
- All 326 matched product name, variant name, and original quantity.
- Nine matched Shopify lines later had `currentQuantity = 0`, while GA4 correctly retained the original purchased quantity of 1.

This establishes the rule:

```text
GA4 itemsPurchased ↔ Shopify LineItem.quantity at purchase time
GA4 itemsPurchased ≠ Shopify LineItem.currentQuantity after later changes
```

### 9.5 Why one Shopify or GA4 transaction can produce multiple rows

One order can contain several product variants. The transaction ID repeats once per grouped item/variant row. Therefore:

- unique `transactionId` represents captured transactions/orders;
- report rows represent transaction–item combinations;
- summing rows as though each row were a new order overcounts orders.

### 9.6 Revenue findings

**Verified:** GA4 `purchaseRevenue` exactly matched Shopify current subtotal for 184 of 207 captured transactions. It matched Shopify current total for only 35 of 207. The most common `purchaseRevenue - currentTotal` differences were `-A$10` (117 orders) and `-A$12` (32 orders), consistent with common shipping charges being present in Shopify total but absent from GA4 purchase value.

**Verified:** the earlier July 9–16 comparison found zero exact matches between GA4 `itemRevenue` and ShopifyQL `net_sales` across 159 matched item rows. These are not equivalent fields: the tested GA4 report was filtered to purchase events, while Shopify net sales reflects discounts and sales reversals under Shopify reporting rules.

**Open question:** the exact Steele tagging rule for GA4 item price, order `value`, discount allocation, tax, and currency has not been inspected. The database should not derive authoritative sales from GA4 revenue.

### 9.7 What ShopifyQL taught us

The earlier ShopifyQL comparison was valuable but not the final coverage test. `FROM sales` returned sales activity recorded in the selected period, including returns, reversals, and adjustments relating to older orders. It also used `net_items_sold`, which is not an order count.

That comparison initially found 72 unique Shopify IDs absent from a GA4 item export. Later analysis separated return-only, zero-value, channel, and date-definition effects. The GraphQL export answered the correct question: which actual orders were created in the period?

Changing ShopifyQL to Shopify GraphQL did not change GA4 coverage. It changed the Shopify comparison population and made the coverage question valid.

### 9.8 Does the evidence prove GA4 is incomplete?

**Verified:** 25 genuine Online Store orders are absent from property `268350484` in the GA4 reports for the same 1–7 July date window.

**Not yet proved:** that those 25 purchases were never collected anywhere. They may have appeared later, been routed to the old property, or been recorded with a malformed/different transaction ID.

**Likely:** intermittent browser-side collection or consent conditions are plausible because the missing group has no obvious Shopify order-property pattern. Shopify's official [analytics discrepancy guidance](https://help.shopify.com/en/manual/reports-and-analytics/discrepancies) notes that JavaScript/cookie blocking, privacy settings, extensions, time zones, and differing tracking mechanisms can cause third-party analytics gaps. This is supporting context, not a diagnosis of these 25 orders.

<!-- LANDSCAPE_START -->

## 10. Recommended GA4 database model

The model below is deliberately practical. It separates grains that answer different questions and avoids forcing all GA4 fields into one wide table.

| Proposed table | Grain | Key fields | Primary purpose | Related Shopify table | Current evidence level |
|---|---|---|---|---|---|
| `ga4_source_property` | One row per GA4 property/stream version | property ID, display name, stream ID, URL, timezone, currency, active dates | Source registry and routing | Store/source connection | **Verified property ID; stream fields open** |
| `fact_ga4_site_day` | Property × date | sessions, active users, engaged sessions, page views, purchases, revenue | Daily site health and leadership KPIs | Daily Shopify commercial summary | **Unverified fields except purchases/revenue** |
| `fact_ga4_item_day` | Property × date × raw item ID | parsed product/variant IDs, item labels, views, add-to-cart units, purchased units, item revenue | Product/variant funnel and demand | `dim_product`, `dim_variant`, product-day facts | **Core item metrics verified; date grain needs a new report** |
| `fact_ga4_funnel_day` | Property × date × chosen compatible product/page/source keys | views, add-to-carts, checkout starts, purchases, derived ratios | Funnel movement and drop-off | Product/variant/channel dimensions | **Views/cart/purchase verified; checkout and compatibility open** |
| `fact_ga4_purchase` | Property × transaction ID × GA4 date | ecommerce purchases, purchase revenue, currency, source dimensions where compatible | Captured purchase signal and order join | `fact_order` | **Verified core fields** |
| `fact_ga4_purchase_item` | Property × transaction ID × raw item ID | item IDs/names/variant, purchased quantity, item revenue | Captured item detail at purchase time | `fact_order_line` | **Verified: 326 matched rows** |
| `fact_ga4_landing_page_day` | Property × date × landing page × approved traffic dimensions | sessions, engaged sessions, purchases, revenue | Landing-page quality and conversion | Optional product/page map | **Unverified — metadata only** |
| `fact_ga4_traffic_source_day` | Property × date × source × medium × campaign/channel | sessions, engagement, purchases, revenue | Acquisition and campaign analysis | Channel dimensions; aggregate Meta comparison | **Unverified — metadata only** |
| `fact_ga4_site_search_day` | Property × date × search term | searches/events, users/sessions, downstream behaviour where compatible | Search demand and unmet intent | Product/category opportunity facts | **Search events documented; term report untested** |
| `bridge_ga4_shopify_item` | Property × raw GA4 item ID × validity period | parsed IDs, matched keys, method, confidence, status | Explicit product/variant mapping | `dim_product`, `dim_variant` | **Exact mapping verified for sampled AU data** |
| `recon_ga4_shopify_transaction` | Property × reconciliation run × Shopify order ID | GA4 presence, event/item presence, searched window, source channel, classification | Coverage monitoring and investigation queue | `fact_order` | **Verified fixed-window pattern** |
| `ingestion_job` / `data_quality_check` | One row per job/check | source, property, request bundle, dates, row count, metadata flags, status, errors | Freshness, retries, completeness, lineage | Shared system tables | **Required by brief; not implemented** |
| `metric_definition` | One row per governed metric version | name, formula, source fields, grain, timezone, refund/currency rules | Prevent dashboard-definition drift | Shared semantic layer | **Required by brief; not implemented** |

<!-- LANDSCAPE_END -->

### 10.1 Storage rules

- Keep the raw GA4 identifier and parsed Shopify identifiers together.
- Include `property_id` in every GA4 fact key; the same transaction or item pattern must never be assumed globally unique across properties.
- Store the report's start/end date, extraction timestamp, timezone, request definition/version, and ingestion job ID.
- Preserve GA4 dates as reported and Shopify timestamps in UTC plus the selected business timezone.
- Store currency code explicitly before combining money across stores or presentment currencies.
- Keep original purchase-state facts separate from current Shopify commercial state.
- Do not overwrite an earlier reconciliation result when a wider search later finds a transaction; record status history and searched windows.
- Use idempotent upserts keyed by the fact grain and request version.

### 10.2 Metric-definition rules

At minimum, define these separately:

- GA4 item units viewed, added, and purchased;
- quantity-based add-to-view and purchase-to-view rates calculated by Product Intelligence;
- GA4's user-based `cartToViewRate` and `purchaseToViewRate` if later tested;
- GA4 captured purchases;
- Shopify created orders;
- GA4 purchase revenue;
- Shopify original subtotal, current subtotal, total, net sales, refunds, and returns.

The same label “revenue” or “conversion rate” must not point to different formulas across dashboards.

## 11. Dashboard and insight use cases

### 11.1 Supported now from tested fields

| Use case | Inputs | Status | Important caveat |
|---|---|---|---|
| Product views | `itemId`, `itemName`, `itemVariant`, `itemsViewed` | **Verified** | Current saved script is top 50 over a moving range. |
| Add-to-cart analysis | item keys + `itemsAddedToCart` | **Verified** | Counts item units, not unique shoppers. |
| Purchase analysis | item keys + `itemsPurchased` | **Verified** | GA4 does not capture every selected-window Online Store order. |
| Item revenue | item keys + `itemRevenue` | **Verified** | Behavioural purchase value, not Shopify net sales. |
| High-view, low-purchase products | views and purchases | **Derived from verified metrics** | Define minimum volume and quantity-based rate explicitly. |
| High-add-to-cart, low-purchase products | cart and purchase units | **Derived from verified metrics** | Not a user-level abandon rate. |
| Variant/size performance | parsed variant ID + `itemVariant` + item metrics | **Verified** | Mapping must preserve invalid/unmapped rows. |
| Product-level Shopify reconciliation | transaction + parsed item IDs + quantities | **Verified** | Original purchase state and current order state must remain separate. |
| Purchase coverage monitoring | Shopify Online Store order set vs GA4 transaction set | **Verified** | Classification must say “absent in selected window.” |

### 11.2 Possible after small additional tests

- Site traffic and engagement using sessions, active users, engaged sessions, and page views.
- Landing-page performance using landing page with compatible session and purchase metrics.
- Source/medium/channel and campaign analysis.
- Product funnel including checkout starts, if an item-compatible checkout report works and Steele populates item arrays consistently.
- Site-search term demand and downstream product behaviour.
- Device and geography segmentation for funnel quality and tracking diagnostics.

These are **Unverified** until saved Steele outputs demonstrate population and compatibility.

### 11.3 Future rule-based and ML uses

The tested daily product signals can later support:

- anomaly flags for sudden changes in views, cart additions, or captured purchases;
- product opportunity scores combining demand, conversion, inventory, margin, and ad spend;
- forecasting features based on daily product and variant history;
- tracking-quality anomaly detection using the Shopify-to-GA4 reconciliation rate;
- product and creative feature analysis described in the product brief.

These are **Unverified future uses**. They require stable daily backfills, governed definitions, missingness features, and enough history. GA4 capture gaps must be modelled explicitly rather than treated as zero demand.

## 12. Data-quality, attribution, and reconciliation considerations

### 12.1 Moving windows and inclusive dates

The early scripts use `start_date="7daysAgo"` and `end_date="today"`. GA4 date ranges are inclusive, so this contains eight calendar dates and changes every time it runs. Fixed closed ranges should be used for reconciliation and reproducible backfills. See Google's official [DateRange definition](https://developers.google.com/analytics/devguides/reporting/data/v1/rest/v1beta/DateRange).

### 12.2 Time zones

The fixed GA4 purchase response reported `Australia/Sydney`; Shopify timestamps were converted to `Australia/Melbourne`. The calendar dates matched for all 207 captured transactions in this July test, so timezone did not explain the coverage gap. Timezone remains a design requirement because settings can change, daylight-saving rules matter, and other periods/properties may differ.

### 12.3 Currency

The Shopify exports contain AUD shop/presentment fields. The GA4 reports did not request `currencyCode`, so the database must not infer currency silently. A production report should include currency where compatible and store both source and normalised reporting amounts.

### 12.4 Attribution

Traffic source, medium, campaign, channel group, and landing page have not yet been tested together with product or purchase metrics. Attribution definitions and lookback behaviour can change the meaning of purchase-by-channel reports. Product Intelligence should store the exact GA4 field name and scope rather than renaming every source field to a generic `channel`.

### 12.5 Sampling, thresholding, and high-cardinality rows

**Verified for the fixed purchase-event report only:** `row_count = 207`, `data_loss_from_other_row = False`, and `subject_to_thresholding = False`. No sampling metadata lines were present in the output. This rules out a row limit, `(other)`-row loss, or thresholding for that report, but not for future higher-cardinality traffic or user reports.

Official [reporting data expectations](https://developers.google.com/analytics/devguides/reporting/data/v1/reporting-data-expectations) explain that sampling, unique-count approximation, thresholding, and `(other)` rows can affect Data API reports. Each ingestion job should persist the response metadata flags.

### 12.6 API limits and pagination

The fixed purchase scripts returned all rows without an explicit low limit. The item-performance script deliberately limits output to 50, so it cannot be ingested as a complete product table. Production extractors must use appropriate limits/offset pagination and compare returned `row_count` with stored rows.

### 12.7 Product identifiers

The observed `itemId` format is excellent for exact joins, but invalid values must remain visible. A successful parse is not a successful Shopify match; both states should be recorded separately.

### 12.8 Order-state differences

GA4 records a behavioural event at purchase time. Shopify order and line fields can change later. Reconciliation must compare GA4 purchased quantity with original Shopify quantity and separately compare current quantity, refunds, and returns.

## 13. Confirmed findings

1. **Verified:** OAuth Desktop access works with the Analytics read-only scope and saved-token refresh.
2. **Verified:** property `268350484` returns populated Steele ecommerce report data.
3. **Verified:** item-level view, add-to-cart, purchase, and item-revenue metrics are populated for sampled products.
4. **Verified:** `itemId` embeds numeric Shopify product and variant IDs in the tested `shopify_AU_...` format.
5. **Verified:** `transactionId` equals Shopify numeric order ID for all 207 fixed-window captured purchases.
6. **Verified:** the event and item transaction sets are identical for 1–7 July; no captured purchase lacked items.
7. **Verified:** all 326 captured transaction–variant combinations match Shopify product ID, variant ID, name, variant, and original quantity.
8. **Verified:** GA4 captured 206 of 231 Online Store orders created in the fixed window; 25 were absent from that window.
9. **Verified:** the missing Online Store group has no obvious single pattern in the exported Shopify status, gateway, country, product, or order-size fields.
10. **Verified:** ShopifyQL sales activity is not a substitute for a GraphQL `createdAt` order population in coverage reconciliation.
11. **Verified:** GA4 purchase and item revenue are not substitutes for authoritative Shopify order, refund, and net-sales measures.

## 14. Likely findings and assumptions

- **Likely:** property `268350484` is the intended current Steele AU/NZ web property; the exact stream configuration should still be saved.
- **Likely:** the old property `268365916` represents an outdated Global website; this comes from the discussion notes, not a saved Admin API output.
- **Likely:** browser consent, blocking, page completion, or intermittent tag/pixel execution may explain at least part of the 25-order gap, because the available Shopify order fields show no common cause. This is not diagnosed.
- **Likely:** GA4 purchase `value` is usually Steele's discounted order subtotal excluding shipping, supported by 184 exact subtotal matches and common A$10/A$12 gaps to total.
- **Likely:** the `shopify_AU` prefix identifies store/region context. A source mapping should still validate it rather than hard-code one prefix globally.
- **Assumption used in this document:** the provided ChatGPT conversation notes accurately preserve earlier executed outputs that were not saved, including property display names and observed event names.

## 15. Open questions and unresolved issues

<!-- LANDSCAPE_START -->

| Question | Why it matters | Current evidence | Recommended test | Priority |
|---|---|---|---|---|
| Do the 25 absent Online Store orders appear later or earlier in property `268350484`? | Distinguishes delayed/replayed events from non-collection | Absent only in 1–7 July fixed window | Search exact transaction IDs from 25 June–20 July | **P0** |
| Do any appear in old property `268365916`? | Detects property-routing problems | Old property mentioned only in notes | Repeat exact-ID search in old property | **P0** |
| Were any recorded with malformed/different transaction IDs? | Exact-ID search could miss altered values | Item/transaction mappings are strong for captured rows | Search nearby purchase rows by timestamp/value; inspect tagging/pixel logs if available | **P0** |
| What are the exact current web stream, measurement ID, URL, timezone, and currency settings? | Required for source registry and reproducibility | Only property ID and report timezone are saved | Use Admin API to list property and data-stream configuration; save output | **P0** |
| Which traffic, landing-page, campaign, device, geography, and search fields are populated? | Needed for most non-commerce dashboards | Metadata only; search events documented | Run small fixed-date population reports with null/`(not set)` rates | **P0** |
| Which proposed field bundles are compatible? | Prevents failed or misleading production queries | Four working bundles; no compatibility matrix | Use `checkCompatibility` for each planned fact table | **P0** |
| Can checkout starts be stored at item/variant grain? | Completes product funnel | `begin_checkout` exists; item checkout report untested | Test `itemsCheckedOut`/`checkouts` with item keys and compare population | **P1** |
| What exact values are sent for item price, order value, discount, tax, shipping, and currency? | Governs revenue meaning and reconciliation | Strong subtotal pattern; item/net-sales mismatch | Inspect tagging implementation and run fields including currency; compare original/current Shopify amounts | **P1** |
| How stable is purchase coverage over closed historical windows? | One week may not represent normal quality | One strong fixed week only | Backfill 8–12 closed weeks and calculate daily/channel coverage | **P1** |
| Are item IDs always valid across history and other regions? | Mapping quality affects all product facts | 326/326 fixed-window matches and top-50 examples | Profile raw item IDs over historical windows; validate all prefixes and malformed rates | **P1** |
| Are high-cardinality or user reports sampled/thresholded? | Can bias traffic and attribution facts | Fixed purchase report had no flags | Persist metadata flags for every new report and test representative ranges | **P1** |
| Is Data API aggregation enough for future journey/ML needs? | Determines whether a raw-event export is needed | Current requirements are mostly daily facts | Define ML questions and evaluate Data API facts versus GA4 BigQuery export | **P2** |

<!-- LANDSCAPE_END -->

## 16. Recommended next discovery steps

The smallest high-value plan is:

1. **Resolve the 25-order question.** Search the exact Online Store order IDs in property `268350484` from 25 June to 20 July, then repeat in `268365916`. Record whether each appears later, in the old property, with a different ID, or nowhere.
2. **Save the source configuration.** Export the accessible account/property list and data streams, including property/stream names, IDs, URLs, timezone, and currency. This turns current discussion claims into traceable evidence.
3. **Create a compatibility-and-population matrix for planned tables.** Test only the field bundles needed for `site_day`, `item_day`, `landing_page_day`, `traffic_source_day`, and `site_search_day`. Save row counts, `(not set)` rates, and response metadata.
4. **Complete the item funnel.** Test checkout metrics at site and item grain. Confirm whether `itemId` is populated consistently in `begin_checkout` events.
5. **Define money fields.** Add currency to the GA4 test and compare purchase value/item revenue with Shopify original subtotal, discounts, tax, shipping, refunds, and current totals.
6. **Measure stability.** Repeat the fixed-window reconciliation across closed historical weeks, waiting at least 48 hours after the final date. Report coverage by day and Shopify source without treating non-web sources as misses.

These investigations are more valuable for database design than testing a long list of unrelated GA4 fields.

## 17. Appendix A — scripts, outputs, and files reviewed

### Repository code

- [`ga4_discovery/auth.py`](../ga4_discovery/auth.py) — OAuth credentials, token refresh, and read-only scope.
- [`scripts/ga4/list_ga4_properties.py`](../scripts/ga4/list_ga4_properties.py) — Admin API account/property listing.
- [`scripts/ga4/list_ga4_event_counts.py`](../scripts/ga4/list_ga4_event_counts.py) — event names and counts over a moving range.
- [`scripts/ga4/list_ga4_metadata.py`](../scripts/ga4/list_ga4_metadata.py) — property reporting metadata.
- [`scripts/ga4/list_ga4_item_performance.py`](../scripts/ga4/list_ga4_item_performance.py) — top-50 item performance.
- [`scripts/ga4/list_ga4_purchase_transactions.py`](../scripts/ga4/list_ga4_purchase_transactions.py) — fixed-date purchase-item report.
- [`scripts/ga4/list_ga4_purchase_events.py`](../scripts/ga4/list_ga4_purchase_events.py) — fixed-date purchase-event report and response metadata.
- [`scripts/shopify/export_shopify_orders.py`](../scripts/shopify/export_shopify_orders.py) — fixed-window Shopify order/order-line export and GA4 reconciliation.
- [`shopify_discovery/shopify_client.py`](../shopify_discovery/shopify_client.py), [`config.py`](../shopify_discovery/config.py), and [`queries.py`](../shopify_discovery/queries.py) — Shopify access and schema support.
- [`README.md`](../README.md), [`PROGRESS.md`](../PROGRESS.md), and [`pyproject.toml`](../pyproject.toml) — project workflow, status, and dependencies.

### Saved repository outputs

- `outputs/GA4_metadata/metadata.txt` — saved property dimension/metric metadata.
- `outputs/GA4_metadata/item_performace.txt` — top-50 product/variant metrics; filename retains the original spelling.
- `outputs/GA4_metadata/item_purchases.txt` and `item_purchases_2.txt` — July 9–16 moving-window item purchase exports.
- `outputs/GA4_metadata/purchase_events_2026-07-01_to_2026-07-07.txt` — 207 fixed-window event rows plus response metadata.
- `outputs/GA4_metadata/purchase_items_2026-07-01_to_2026-07-07.txt` — 326 fixed-window transaction–item rows.
- `outputs/shopify_orders/orders_2026-07-01_to_2026-07-07.csv` — 251 GraphQL order rows.
- `outputs/shopify_orders/order_lines_2026-07-01_to_2026-07-07.csv` — 385 Shopify order-line rows.
- `outputs/discovery/shopify_ga4_order_reconciliation_2026-07-01_to_2026-07-07.csv` — 251 order-level reconciliation rows.
- `outputs/discovery/Shopify_GA4_purchase_reconciliation_2026-07-09_to_2026-07-16.xlsx` — earlier ShopifyQL-versus-GA4 reconciliation workbook.
- `outputs/shopify_schema_fields/*.csv` — Shopify schema field inventories used to understand available product/order objects.

### Provided context

- `ChatGPT Conversation Outputs.md` — curated record of prior discovery analysis, manual item-ID checks, event observations, and reconciliation reasoning.
- `Steele Intel - Product Brief and Dev Roadmap.docx` — product scope, database principles, dashboards, metric governance, reconciliation, and future ML requirements.

### Expected evidence not found

- saved Admin API account/property-list output;
- saved data-stream/website configuration;
- raw event-count output;
- tested traffic-source, landing-page, device, geography, campaign, and site-search reports;
- a dimension/metric compatibility report;
- a wider-window/old-property search for the 25 absent Online Store orders;
- direct tag/pixel payload or implementation evidence explaining the coverage gap;
- explicit GA4 currency output in the saved reports.

### External supporting documentation

- Google: [Data API overview](https://developers.google.com/analytics/devguides/reporting/data/v1), [API dimensions and metrics](https://developers.google.com/analytics/devguides/reporting/data/v1/api-schema), [ecommerce scopes](https://support.google.com/analytics/answer/12947610), and [reporting data expectations](https://developers.google.com/analytics/devguides/reporting/data/v1/reporting-data-expectations).
- Shopify: [Order GraphQL object](https://shopify.dev/docs/api/admin-graphql/latest/objects/Order), [LineItem GraphQL object](https://shopify.dev/docs/api/admin-graphql/latest/objects/LineItem), [sales-report definitions](https://help.shopify.com/en/manual/reports-and-analytics/shopify-reports/report-types/default-reports/sales-report), and [analytics discrepancies](https://help.shopify.com/en/manual/reports-and-analytics/discrepancies).

## 18. Appendix B — field and metric glossary

| Term | Simple definition | Project-specific note |
|---|---|---|
| Property | GA4 reporting container selected by property ID | Current scripts use `268350484`. |
| Data stream | Website or app source feeding a GA4 property | Exact Steele stream has not been saved. |
| Event | Named user or system activity sent to GA4 | Examples include `view_item`, `add_to_cart`, and `purchase`. |
| Dimension | Descriptive field used to group report rows | Dimensions determine the report grain. |
| Metric | Numeric measurement calculated for the selected grouping | Metric meaning can change with scope and filters. |
| Grain | What one database or report row represents | Must be explicit in every fact table. |
| `itemId` | Item identifier sent in an ecommerce event | Tested value embeds Shopify product and variant IDs. |
| `itemVariant` | Specific product variation sent to GA4 | Steele values include sizes such as XS, S, M, L, and XL. |
| `transactionId` | Identifier sent for an ecommerce transaction | Equals Shopify numeric order ID in the fixed test. |
| `itemsViewed` | Quantity of item units in `view_item` events | Tested in top-50 item performance output. |
| `itemsAddedToCart` | Quantity of item units in `add_to_cart` events | Not a unique-user count. |
| `itemsPurchased` | Quantity of item units in purchase events | Maps to original Shopify line quantity in the test. |
| `itemRevenue` | Revenue from items, excluding event-level tax and shipping | Not Shopify net sales. |
| `ecommercePurchases` | Count of completed purchase events | 207 in the fixed GA4 output. |
| `purchaseRevenue` | Revenue supplied through purchase-event `value` | Usually matched Shopify subtotal in the fixed test. |
| Session | Group of user interactions within GA4's session rules | Session fields remain untested in saved Steele reports. |
| Landing page | First page path associated with a session | Metadata-supported, not population-tested. |
| Source / medium | Attribution fields describing where a session came from | Must retain exact GA4 scope/field names. |
| Thresholding | Removal of low-volume rows to protect user privacy | Not present in the fixed purchase-event response. |
| `(other)` row | Grouping of less-common high-cardinality values | Fixed purchase response reported no data loss from this. |
| Original quantity | Units ordered at purchase time | GA4 aligns with Shopify `LineItem.quantity`. |
| Current quantity | Units remaining after later refunds/removals | Shopify `LineItem.currentQuantity`; can differ from GA4. |
| Reconciliation window | Date range searched in both systems | Must be stored with every reconciliation result. |

---

**Document status:** Current discovery snapshot. The GA4 portion of the Product Intelligence database should not be treated as final until the P0 investigations in Section 15 are completed.
