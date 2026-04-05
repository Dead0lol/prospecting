# AGENT.md

Project operating guide for future agents and maintainers.

Last reviewed against the codebase on 2026-04-04 using:
`pipeline.py`, `app.py`, `config/settings.py`, `models/lead.py`,
`export/sheets_writer.py`, `verification/seen_tracker.py`,
`scoring/lead_scorer.py`, and the docs under `docs/`.

## Mission

This repository is a Python lead-generation system for finding
English-speaking fitness coaches, enriching their websites, verifying
contactability, scoring ICP fit, deduplicating against past runs, and
exporting the final lead set to Google Sheets.

The project is optimized for fresh, usable outreach targets rather than
raw volume. A "good" change improves lead quality, keeps the pipeline
stable across long runs, and preserves the data contracts used by the
CLI, Streamlit UI, caches, and Google Sheets export.

## Current Product Shape

- `pipeline.py` is the main orchestrator and the primary source of truth
  for runtime behavior.
- `app.py` is a Streamlit UI for running the pipeline, reviewing lead
  data, and inspecting cache/checkpoint state.
- Discovery is keyword-based and global. Geography is mostly cosmetic;
  city targeting is intentionally not part of the active strategy.
- Both bulk discovery and one-off coach-site lookups use DuckDuckGo.
- Website candidates are processed before Instagram candidates because
  they produce stronger, more contactable leads.
- Instagram-only leads without a discoverable real website are
  intentionally dropped.
- Website crawling treats the final fetched URL after redirects as the
  canonical base for relative links and follow-up path hints.
- Optional AI classification now goes through OpenRouter, with
  heuristic classification as the fallback path.
- Email verification happens in batch after candidate collection.
- Export writes tiered snapshots plus cumulative history to Google
  Sheets.

## Core Runtime Flow

1. Discovery via DuckDuckGo query generation and rotation.
2. Candidate splitting, filtering, and seen-lead suppression.
3. Website or Instagram lead processing.
4. Website crawling and data enrichment.
5. Email discovery or guessing.
6. Batch SMTP verification.
7. Classification and heuristic scoring.
8. Deduplication across collected leads.
9. Export to Google Sheets and checkpoint persistence.

## Source of Truth Order

When documentation and code disagree, trust this order:

1. `pipeline.py`
2. `models/lead.py`
3. `config/settings.py`
4. `export/sheets_writer.py`
5. `verification/seen_tracker.py`
6. Everything under `docs/` and `README.md`

If a code change makes the docs inaccurate, update the docs instead of
preserving stale wording.

## Important Project Contracts

### Lead schema

- `models/lead.py` defines the canonical `Lead` dataclass.
- `SHEET_COLUMNS` is a downstream contract, not a cosmetic list.
- Any field addition, removal, rename, or order change can affect:
  export, deduplication, UI tables, tests, historical data, and
  Google Sheets compatibility.

### Google Sheets behavior

- `All_Leads` is append-only historical memory and participates in
  deduplication.
- `Hot_Leads`, `Good_Leads`, and `Review_Queue` are latest-run
  snapshots and are cleared before each export.
- `Run_Log` stores run metadata.

Do not casually rename tabs or alter write behavior without treating it
as a project-level contract change.

### Deduplication and seen-state

- Dedup and seen suppression depend on normalized email, Instagram
  identity, and canonical domain matching.
- `verification/seen_tracker.py` and `verification/deduplicator.py`
  protect the "net-new leads per run" behavior.
- `All_Leads` and `.cache/seen_identities.json` both matter to runtime
  behavior.

### Discovery strategy

- The active strategy is keyword-first prospecting for fitness coaches.
- Query rotation in `.cache/discovery_state.json` is intentional and
  should be preserved unless explicitly redesigned.
- Both bulk discovery and individual coach-site lookups use DuckDuckGo
  with retry logic for reliability.

### Instagram handling

- The codebase should not assume Instagram direct scraping is reliable.
- The current workable path is DDG snippet parsing plus follow-up
  website discovery.
- If Instagram logic changes, review both discovery quality and lead
  cost because weak IG-only leads are intentionally filtered out.

### Email extraction

- Vendor telemetry emails should be treated as noise, not leads.
- `extraction/email_extractor.py` filters service addresses such as
  Wix/Sentry telemetry mailboxes before lead selection.

## Files That Usually Need Joint Updates

When changing one of these areas, check the linked surfaces too:

- Pipeline behavior:
  `pipeline.py`, `docs/PIPELINE.md`, `README.md`, this file
- Lead fields or export columns:
  `models/lead.py`, `export/sheets_writer.py`, `app.py`, tests, docs,
  this file
- Config or env vars:
  `config/settings.py`, `docs/CONFIGURATION.md`, `README.md`, this file
- UI behavior:
  `app.py`, `docs/UI.md`, `README.md`, this file
- Dedup/identity behavior:
  `verification/seen_tracker.py`, `verification/deduplicator.py`,
  `docs/PIPELINE.md`, this file

## Working Rules For Future Changes

- Preserve the distinction between "fresh lead discovery" and
  "historical lead memory".
- Prefer code paths that improve lead quality over simply increasing
  candidate throughput.
- Keep secrets and credentials out of version control.
- Treat long-running behavior, retries, caches, and external-service
  failure modes as product behavior, not implementation trivia.
- When touching heuristics, scoring, or filtering, think about both
  precision and downstream outreach usefulness.
- When docs drift, fix the docs in the same change if the drift affects
  how someone would safely work on the project.

## Required Maintenance Rule

Always update `AGENT.md` whenever you make a change that alters the
function of the project.

This includes any change to:

- pipeline stages or processing order
- discovery strategy or filtering logic
- lead schema or Google Sheets export contract
- scoring thresholds or qualification rules
- cache, checkpoint, or seen-identity behavior
- UI workflow or operator-facing behavior
- environment variables, credentials, or setup requirements
- external integrations or their operational assumptions

Do not leave this file stale after functional changes. If the project
behavior changed, `AGENT.md` must change in the same piece of work.

## Useful Commands

```bash
pip install -r requirements.txt
python pipeline.py --limit 10 --json
python pipeline.py --limit 30
streamlit run app.py
pytest
```

## Practical Review Checklist

Before finishing a functional change, quickly verify:

- Does `AGENT.md` still describe the real runtime behavior?
- Do `README.md` and the relevant docs still match the code?
- Did a schema or tab contract change require UI/test/export updates?
- Did a cache or dedup change affect repeat-run behavior?
- Did a config change require `.env` documentation updates?
