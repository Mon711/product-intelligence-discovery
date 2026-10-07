# Change history and decisions

**Maintained:** 5 October 2026. Covers all 39 commits on `main` through `9a1afc4`,
the separate Meta archive commit, and the uncommitted organization change.

**6 October update:** the organization change is now committed as `0724d5e`.
The Step 1 entry below records implementation; publication is noted below.

This is a grouped explanation of meaningful work. Commit dates, subjects,
changed paths, relevant safe diffs, saved findings, and the archive handoff are
the evidence. Where intention is not explicit, the reason is marked **inferred**.
Verification here distinguishes retained outputs, recorded past checks, and
checks actually run for this update.

## 21–22 June: establish Shopify access

**Commits:** `2a4f004`, `3e6f9ae`, `cb7ad9a`, `d85f4e9`, `f3475c1`.

Added the initial Python structure, local configuration loader, Shopify request
client, shop query, and connection check. Fixed a missing configuration return
and started the former progress document. A mistakenly tracked environment file
was removed from the working version and ignored. Historical credential contents
were not inspected for this log; removal from files does not erase Git history.

**Reason:** establish working source access before field exploration and keep
local credentials out of subsequent commits. The return fix addresses a concrete
configuration failure. **Verification:** code and commit records establish these
changes; later retained exports support historical Shopify access, not current
credential validity.

## 22–24 June: make field discovery reusable

**Commits:** `49d1a9d`, `666106d`, `bf6af10`, `68daf14`, `463e68f`, `d632d5f`.

Added field-discovery queries, selectable object types, CSV output, a standard
Python entry point, and improved nested field/argument type handling. Updated
progress/configuration notes alongside the work.

**Reason:** the commit subjects describe expanding discovery beyond one object
and fixing type information. **Inferred:** reusable type inventories reduce
manual inspection before deciding which source fields matter. **Verification:**
twelve retained Shopify schema CSVs exist; field availability is not proof that
Steele populates the fields.

## 14–16 July: establish GA4 access and exploratory reports

**Commits:** `1cb6dfa`, `c112a18`, `0492e99`, `89982cb`, `14c352e`, `5c78503`, `69373ae`.

Added Google OAuth authentication, account/property listing, event counts,
metadata, item performance, purchase-item identifiers, and purchase-event
reports. The purchase-event report followed discrepancies between Shopify IDs
and GA4 transaction IDs.

**Reason:** learn which data exists and whether purchases/products can be joined
to Shopify. **Verification:** retained metadata and purchase/item reports support
sample findings. Account/property listing and raw event-count output were not
retained; exact stream configuration remains unverified.

## 15–16 July: standardize Python setup and code organization

**Commits:** `92e533b`, `33755e8`.

Moved dependency/environment management to Python 3.12 and `uv`, with
`pyproject.toml` and a lockfile. Reorganized the earlier generic package into
Shopify and GA4 helper packages and source-specific script folders; centralized
GA4 authentication and moved credential locations under `config/`.

**Reason:** subjects explicitly record the setup migration and organization.
**Inferred:** consistent environments and reusable authentication simplify
running and maintaining experiments. **Verification:** current manifest,
lockfile, imports, and configuration paths agree with that organization. The
wheel configuration lists Shopify/GA4 packages; it does not package the later
Meta code as an independently installable component.

## 17–21 July: align the purchase comparison

**Commits:** `bb61c54`, `c8f5f32`.

Set the GA4 purchase dates and added a paginated Shopify GraphQL order/line
export plus fixed-window reconciliation. The stronger comparison selected
orders created on 1–7 July in Melbourne-local dates rather than treating
ShopifyQL sales activity as a list of newly created orders.

**Reason:** align the population, dates, and record meaning so the coverage test
answers a valid question. **Verification:** retained files contain 251 orders,
385 lines, 207 captured GA4 transactions, and 326 purchase-item rows. Detailed
matching results and caveats belong in the [GA4 research](research/ga4-findings.md).
The 25 missing Online Store orders do not establish a permanent tracking-loss rate.

## 21 July: retain findings and their evidence

**Commits:** `b6f96d4`, `8524c91`.

Added the GA4 Markdown/Word report and saved script outputs, schema inventories,
order exports, and comparison files. A spreadsheet lock artifact was also
tracked; it is preserved but is not a research result.

**Reason:** the subjects explicitly record retaining findings and previously
local output. **Inferred:** keeping evidence alongside explanations makes the
research inspectable without requerying sources. **Verification:** these files
remain present under the new locations; their fingerprints were checked during
the organization change below.

## 23 July: introduce the product reference and consolidate onboarding

**Commits:** `94ec5ca`, `92ec6b9`.

Added Karan's product brief and expanded the README to cover the project and
codebase; removed the older `PROGRESS.md`.

**Reason:** capture the product direction and consolidate repository guidance.
The brief's later-superseded database design must not be treated as current
implementation instructions. **Verification:** the original brief is preserved
under `docs/reference/`; the removed progress file remains available in Git
history rather than as a broken current-document link.

## 27–29 July: begin Meta object discovery

**Commits:** `644470c`, `4a73e4b`, `fa8130f`, `8d0f10e`, `a89b99d`, `d217041`, `d856633`.

Added Meta token loading, account checks, first-page campaign/ad-set/ad lists,
15-creative inspection, saved examples, and accompanying README updates.

**Reason:** determine accessible accounts and the structure of advertising
objects before deeper analysis. **Verification:** retained outputs show three
accounts and first pages of 25 campaigns, ad sets, and ads. These counts are not
complete account totals; no complete performance extract exists on this main
revision.

## 29 September: preserve unfinished Page/story research

**Commit:** `0523338`.

Preserved user/Page token helpers, a personal OAuth experiment, and object-story
inspection as work in progress. Saved failures instead of implying that story
content was retrieved.

**Reason:** explicitly preserve an interrupted investigation and its permission
limitations. **Verification:** all 15 historical metadata requests and all 15
story requests failed permissions. This says nothing conclusive about ads-only
reporting access; Page/post access is a separate permission path.

## 29 September: record the Dalgo direction and clarify the handoff

**Commits:** `5efbf14`, `6ba6e16`, `953069e`.

Added the project handoff, documented the switch to Dalgo, clarified Creatnet's
continuing analytics/product and missing-connector remit, and removed a proposed
action plan from the handoff while retaining direction and known unknowns.

**Reason:** communicate the changed data-foundation responsibility without
discarding product goals or confusing proposals with delivery. The reason for
removing the action plan beyond the stated edit is not recorded in these commits.
**Verification:** handoff/README diffs establish the clarification; they do not
prove configured Dalgo connections, a contract's technical scope, or deployment.

## 29 September: create a context-sharing copy

**Commit:** `24035d5`.

Added `exports/PI_ChatGPT_Context_Pack_2026-09-29.zip`: a read-first prompt plus
copies of README, the Markdown handoff, GA4 research, and product brief.
**Reason:** the commit subject identifies a ChatGPT handoff. **Verification:**
archive members were inspected before removal. The pack is removed from the
working repository in the cleanup below because the user does not want learning
or context copies here. Its old version remains in Git history.

## 5 October: add shared agent instructions

**Commit:** `9a1afc4`.

Added `AGENTS.md` and a README pointer for source-backed discovery, read-only
Meta access, privacy, beginner-friendly explanations, and maintenance boundaries.
**Reason:** provide agents a predictable place for working instructions.
**Verification:** instructions are tracked on main; automatic reading by every
agent tool is not guaranteed by the existence of the file.

## 5 October: preserve the newer Meta reader separately

**Archive branch:** `archive/meta-ads-reporting-reader`.
**Commit:** `cfa22bb0f039df9e300d1da4441dd8c245a015da`.
**Local evidence stash:** `4db2afe76c99d4837ace8b06b3f72f4e5f7659d2`.

The archive adds the restricted reader/exporter, reporting command, 23-test
suite, learning handoff, and study ZIP. Its recorded implementation-time checks
include ads-only access and a one-day 38-row Insights sample; the revised full
export remains unverified. See [project state](project-state.md) for the precise
scope and partial-run counts.

**Reason:** the archive subject explicitly records preserving code and learning
materials separately. It is not merged into main. **Verification this update:**
archive files and the two stashed manifests were inspected without restoring
them. Both manifests say `failed`. The stash's third parent holds the local-only
untracked reports; an ordinary clone will not include that evidence.

**Historical paths inside those Git objects:**
`docs/Meta_Ads_Code_Learning_Handoff_2026-10-05.md`,
`exports/Meta_Ads_Learning_Pack_2026-10-05.zip`, and
`outputs/meta_discovery/reports/`. These paths describe the archived snapshot,
not files to recreate in the active tree. Existing archives/history are not
rewritten to remove historical sharing packs.

## 6 October: implement Meta discovery Step 1 only (commit `74839ec`)

**Before:** active Meta scripts could load credentials and fetch first-page
advertising samples, but had no small, shared ads-only access validation command
or automated saved Shopify–GA4 identifier audit. The fuller reader remains archived.

**After:** a staged command implements only `access`; the new reader validates
explicit configuration, blocks all endpoints except token inspection and Steele
account metadata, validates token/app/type/scopes/expiry, disables redirects,
uses request timeouts, and returns safe metadata. The separate offline foundation
audit validates saved July report rows, transaction/product/variant identifiers
and original quantities. Fresh timestamped summaries preserve prior evidence.

**Reason:** the user requested one explained implementation step with manual
verification, after the earlier reporting workflow proved too broad to follow.
Existing authentication scripts, dependencies, advertising objects, archived
code and stash remain unchanged. No Step 2 collection or connection claims.

**Actual checks:** 15 offline tests passed, including invalid/more broadly scoped
tokens, expiry, wrong account, redirects, redacted errors, blocked endpoints,
malformed/truncated evidence, unmatched items, unique outputs, offline isolation,
and rejection of later stages. Live Step 1 passed two Meta GET reads: expected
account `2313037395632947`, v26.0, AUD, Australia/Sydney, `ads_read/public_profile`.
Saved foundation reproduced 207 transactions, 326 matching item rows and original
quantities, plus 25 absent Online Store orders. An intentional `/dev/null` config
run exited 1 before networking and saved failure. Evidence paths are recorded
in [project state](project-state.md). README includes reproducible manual checks.

**Remaining:** current Shopify/GA4 access, Meta fields/sample collection and actual
cross-source connections remain unverified by this step. Original Shopify–GA4
gap causes remain out of scope. New code is uncommitted; no commit, push, or PR.
The requested small teaching handoff is saved outside this repository in Downloads.

**Publication:** committed and pushed to `origin/main` as `74839ec` at the user's
request. The isolated Step 1 tree passed all 15 tests before committing. Step 2
code, tests, evidence and shared-file additions remained unstaged/uncommitted;
the Git index was verified empty after commit. This publication note is recorded
with Step 2 rather than in a separate documentation-only commit.

## 6 October: implement Meta discovery Step 2 only

**Before:** the active command could validate access and audit saved identifiers,
but could not choose a dated advertising sample or save campaign/ad-set/ad references.

**After:** `--stage sample` retrieves complete period-level ad Insights for 1–7
July, selects up to 15 positive-impression ads using saved-example name priority
then numeric ID, and reads only selected ads and unique parent campaign/ad-set
objects. It saves a hierarchy CSV plus source/settings/selection evidence. The
reader's GET gate now permits only fixed-window Insights and registered IDs
discovered from this account; validated ownership/fields, cursor paging, partial
failure preservation and credential redaction remain enforced. Creative reads
stop at ID references. Step 1 behavior and legacy scripts are preserved.

**Reason:** implement the user's next explained checkpoint and provide manual
verification plus a flat Downloads learning ZIP with exact source and Git diffs.
The Step 1 working files were snapshotted before this change so incremental
diffs can distinguish Step 2 from still-uncommitted Step 1 additions.

**Actual checks:** 29 offline tests passed. Live one-ad and 15-ad samples both
passed; Insights returned 42 rows in one page. The full sample read 15 ads, five
ad sets and five campaigns in 28 GET requests (including validation), with seven
saved-name priorities and zero hierarchy gaps. Empty configuration failed before
networking. Recorded output paths/settings/limits are in project state. Ads
Manager/manual UI comparison is not established by these API checks.

**Remaining:** Step 3 creative content/link discovery, Meta-to-GA4/Shopify matching
and existing discrepancy causes are not implemented. No new dependencies or
production infrastructure or change to the archived Meta branch/evidence stash.

**7 October publication preparation:** the user authorized staging, committing
and pushing Step 2, including its saved sample evidence. All 29 offline tests and
the whitespace check passed again. This entry accompanies the implementation
commit; its Git identity is available in repository history.

## Git publication evidence and limits

At inspection, local `main` and `origin/main` both pointed to `9a1afc4`, and local
and remote-tracking archive refs both pointed to `cfa22bb`. The 39 main commits
were reachable from that locally recorded `origin/main` revision. Local reflog
entries identify some remote-tracking updates as “update by push.” No network
fetch was performed, so this is evidence of locally recorded publication state,
not a fresh remote check or a complete timeline of when/who pushed each commit.
The stash is a local snapshot, not a published branch.

## 5 October: clarify documentation and evidence ownership (uncommitted)

**Before:** current knowledge overlapped across README, a dated handoff, and a
long GA4 report; `outputs/` mixed research artifacts under unclear names;
`exports/` duplicated project context as a learning/sharing ZIP.

**After:** README explains setup/layout, project state owns the compact findings
register, this file explains changes, GA4 research retains detailed evidence,
and Word references remain dated snapshots. Research files live under
`evidence/` by source or comparison. Removed `exports/` at the user's request;
future requested packs belong outside this repository.

**Reason:** make onboarding and future context updates easier for humans and
different agent tools while avoiding duplicated knowledge. Code edits change
only file paths in three scripts; packages, commands, API queries, calculations,
dependencies, credentials, branch refs, and the stash are preserved. The schema
script's default now agrees with the retained Shopify schema-evidence directory.

**Verification performed:** all 32 research files and Word references retained
identical SHA-256 fingerprints (content checks), as did five incidental Finder
metadata files. All 29 Python modules passed syntax checks; their parsed code
matched the previous versions after only the expected path substitutions in
three scripts. All 39 main commit hashes are represented in this history, and
all 43 local Markdown links resolved. Mocked schema exports exercised both the
new default and explicit directory override; mocked Shopify and Meta runs read
and wrote the new layouts in temporary folders with network access blocked.
Retained input/output paths resolved, credential-ignore checks passed, and all
Git refs including the archive branch and stash were unchanged. Whitespace
checks passed. No live API requests, deployment, commit, push, or publication
was performed. New work is uncommitted; do not invent a commit hash for it.
