# Agent instructions

## Start here

- Read `README.md` for setup, script commands, repository layout, and research
  limitations. Read `docs/Product_Intelligence_Discovery_Handoff_2026-09-29.md`
  for the project direction and historical handoff.
- For GA4 questions, consult `docs/ga4_discovery_current_state.md`, then inspect
  the relevant source and evidence. Saved findings are tied to their dates,
  account/property, filters, and report settings; do not assume they are current.
- Inspect Git status and affected files before editing. Preserve unrelated work.
  Current user instructions and verified source take precedence over older notes.
- On this user's machine, read `/Users/mrinalsood/.codex/RTK.md` and prefix shell
  commands with `rtk`; use `rtk proxy <command>` for commands without a dedicated
  wrapper. If that machine-local file is absent elsewhere, follow local tooling.

## Repository purpose and boundaries

This is a Python discovery repository for Steele's Shopify, Google Analytics 4
(GA4), and Meta Ads data. It supports access checks, API exploration, small
reports, identifier matching, and data-quality research.

- Keep scripts small, explicit, and readable. Reuse `shopify_discovery/`,
  `ga4_discovery/`, and `meta_discovery/` for relevant shared helpers; inspect
  their actual behavior before reuse.
- Use the existing Python 3.12 and `uv` setup described in the README. Do not add
  dependencies or infrastructure without a task-specific need.
- Do not add a production application, database, migrations, scheduled ingestion,
  dashboard, or deployment infrastructure here. Dalgo is the chosen aggregation
  and database direction; needed production connectors belong in its repository.
  Exact source coverage and delivery details still require evidence.
- Treat the earlier custom-build roadmap as historical. Distinguish proposed,
  implemented, verified, historical, and unknown behavior.

## Beginner-friendly communication

Assume no prior technical knowledge unless the user says otherwise.

- Use clear headings and focused numbered steps for complicated explanations.
  Define technical terms immediately in plain language and explain why they matter.
- For code changes, explain the purpose, original behavior, changed behavior,
  important blocks and execution/data flow, why the approach was chosen,
  assumptions, risks, wider project effects, and how to verify the result.
- For debugging, explain the error, which component produced it, likely cause,
  supporting evidence, each troubleshooting step and expected result, and the
  eventual fix. Clearly distinguish a hypothesis from a confirmed cause.
- For commands given to the user, state the working folder, purpose, important
  arguments, file/system effects, expected output, and verification. Warn before
  destructive or difficult-to-reverse operations.
- Prefer complete explanations of the relevant reasoning without unrelated
  advanced detail. Use concrete project examples; do not substitute analogies
  for an explanation of the actual system.

## Source access, credentials, and privacy

- Live API requests require authorization from the current conversation. Honor
  authorization already given for the same scope; a new AGENTS file does not
  reset it. A request to edit documentation alone does not authorize live queries.
- Meta Ads access is strictly for reading and analysis. Never create, edit,
  publish, pause, delete, or otherwise manage campaigns, ad sets, ads, creatives,
  budgets, audiences, or other advertising assets. Do not submit conversion events.
- Target Steele account `2313037395632947` (`act_2313037395632947` in API paths).
  Confirm the configured account before reading; do not silently switch accounts.
- Use `ads_read` for advertising reads. Do not request `ads_management` or
  `business_management` for this discovery. An app use-case label does not prove
  the token's granted permissions; validate the token and account access.
- For new Meta readers, restrict request methods and endpoints to approved reads.
  Use GET reporting and smaller date windows rather than POST background report
  creation. Do not follow arbitrary credential-bearing pagination URLs.
- Advertising reports and Facebook Page/post access are separate. The old
  `scripts/meta/authorize_meta.py` also requires Page permissions and a Page
  token; do not treat that flow as mandatory for ads-only reporting.
- Keep credentials in ignored local configuration. Never print, commit, log,
  export, or paste tokens, App Secrets, or credential-bearing URLs. Redact errors
  and request details. Never ask the user to paste secrets into chat.
- Minimize personal information in exports. Keep unnecessary customer names,
  emails, phone numbers, addresses, and IP addresses out of discovery outputs.
- Save new evidence separately from historical exports. Local saving does not
  authorize uploading or publishing internal data or documents.

## Evidence, verification, and documentation

- Verify API fields against saved metadata or current official documentation.
  Treat expired credentials and permission failures as access failures, not proof
  that the source has no data. Never broaden permissions automatically.
- Handle pagination: a first page is not a complete dataset. Record account,
  reporting dates, currency, time zone, filters, row meaning, attribution settings,
  and collection time when saving reports. Preserve missing/unavailable fields.
- Compare sources only after aligning those settings and metric definitions.
  Shopify describes commercial order state; GA4 describes captured website
  behavior; Meta reports advertising attribution. Meta purchase totals do not
  establish individual Shopify order matches. Do not sum deduplicated reach
  across ads or days as though it were an account total.
- Run focused checks appropriate to the change. Report what was tested and what
  remains unverified. For documentation-only edits, check paths, links, whitespace,
  and consistency; no live queries or application rebuild are needed.
- Update affected README guidance in the same change when scripts, setup,
  configuration, findings, limitations, or repository structure change. Update
  the relevant existing discovery document when its findings change; avoid
  duplicate context trees and session transcripts. Keep AGENTS focused on durable
  instructions rather than temporary token expiry or a running task history.
- Respect explicit checkpoints such as plan-only, one step, or stop-after.
  Finish authorized work without asking for the same permission again. Creating
  or editing local files is not authorization to commit, push, or open a PR.
