# Fitness Coach Prospecting MVP

Internal Python pipeline for finding solo and online fitness coaches, enriching public business data, scoring leads, and exporting them to Google Sheets.

## What it does

- discovers candidates with web search queries tuned for fitness coaches
- resolves Instagram bios when public profiles are available
- crawls websites and link hubs for emails, booking links, and social links
- scores leads with rule-based logic and uses AI enrichment only when enabled
- verifies emails with MX and SMTP checks
- exports `Hot_Leads`, `Good_Leads`, `Review_Queue`, and `All_Leads` tabs to Google Sheets

## Setup

1. Make sure `.env` exists in the project root.
2. Make sure your Google service account JSON file is in the project root.
3. AI is optional. Leave `ENABLE_AI=false` if you want the pipeline to run without Gemini.
3. Install dependencies:

```bash
python -m pip install -r requirements.txt
```

## Run

```bash
python pipeline.py --country US --limit 25
```

JSON output for debugging:

```bash
python pipeline.py --country US --limit 10 --json
```

## Notes

- by default, AI is off and the pipeline uses heuristic classification only
- if you want Gemini enrichment, set `ENABLE_AI=true` in `.env`
- if Gemini quota is unavailable, the pipeline falls back to heuristic classification
- Instagram lookups depend on public profile availability and rate limits
- SMTP verification is free but less accurate than paid verification vendors
- search quality will improve as you tune keywords, cities, and filters in `config/`
