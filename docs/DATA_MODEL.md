# Data Model Documentation

## Lead Dataclass

**File:** `models/lead.py` (114 lines)

The `Lead` dataclass is the central data structure, representing a single prospecting lead. It uses Python `@dataclass(slots=True)` for memory efficiency.

---

## Field Reference

### Scoring & Tiering

| Field        | Type  | Default    | Description                                          |
|--------------|-------|------------|------------------------------------------------------|
| `lead_score` | `int` | `0`        | Composite score 0-100. Set by `score_lead()`.        |
| `lead_tier`  | `str` | `"review"` | `hot` (>=65), `good` (>=45), or `review` (<45).      |

### Contact Information

| Field              | Type  | Default    | Description                                          |
|--------------------|-------|------------|------------------------------------------------------|
| `business_name`    | `str` | `""`       | Coach's business or brand name                       |
| `contact_name`     | `str` | `""`       | Person's actual name (extracted from site title/IG)   |
| `email`            | `str` | `""`       | Contact email address                                |
| `email_status`     | `str` | `"unknown"`| `valid` / `invalid` / `catch-all` / `risky` / `disposable` / `missing` |
| `email_source`     | `str` | `""`       | How email was found: `website` / `link_hub`          |
| `phone`            | `str` | `""`       | Phone number (US format)                             |

### Online Presence

| Field                | Type  | Default    | Description                                    |
|----------------------|-------|------------|------------------------------------------------|
| `website`            | `str` | `""`       | Coach's website URL                            |
| `instagram_url`      | `str` | `""`       | Full Instagram profile URL                     |
| `instagram_username` | `str` | `""`       | Instagram handle (without @)                   |
| `followers`          | `int` | `0`        | Instagram follower count                       |
| `linkedin_url`       | `str` | `""`       | LinkedIn profile URL                           |
| `youtube_url`        | `str` | `""`       | YouTube channel URL                            |
| `tiktok_url`         | `str` | `""`       | TikTok profile URL                             |

### Location

| Field     | Type  | Default | Description                    |
|-----------|-------|---------|--------------------------------|
| `country` | `str` | `""`    | Country code (e.g., "US")      |
| `city`    | `str` | `""`    | City name                      |

### Business Signals

| Field                   | Type   | Default     | Description                                      |
|-------------------------|--------|-------------|--------------------------------------------------|
| `specialty`             | `str`  | `""`        | e.g., "fat loss", "macro coaching"               |
| `offers_online_coaching`| `str`  | `"unknown"` | `yes` / `unknown`                                |
| `offer_type`            | `str`  | `"unknown"` | e.g., "1:1"                                      |
| `booking_link`          | `str`  | `""`        | Calendly/Acuity/TidyCal URL                      |
| `pricing_page`          | `str`  | `""`        | URL of pricing page                              |
| `has_pricing_page`      | `bool` | `False`     | Whether pricing info was found                   |
| `has_lead_magnet`       | `bool` | `False`     | Whether a free guide/ebook/challenge was found   |
| `has_testimonials`      | `bool` | `False`     | Whether client testimonials were found           |
| `platform`              | `str`  | `"unknown"` | Website platform: wordpress/squarespace/wix/kajabi/showit |
| `services_found`        | `List[str]` | `[]`   | Detected service types (e.g., "1:1 coaching")    |
| `social_links`          | `List[str]` | `[]`   | All social media URLs found                      |

### Outreach Intelligence

| Field                 | Type  | Default | Description                                        |
|-----------------------|-------|---------|----------------------------------------------------|
| `weakness`            | `str` | `""`    | Identified gap for outreach angle                  |
| `outreach_angle`      | `str` | `""`    | Suggested pitch angle                              |
| `personalization_note`| `str` | `""`    | Personalized note for email template               |

### Source Tracking

| Field               | Type  | Default    | Description                                   |
|---------------------|-------|------------|-----------------------------------------------|
| `source_url`        | `str` | `""`       | URL where the lead was first discovered        |
| `source_type`       | `str` | `""`       | `instagram` / `website`                        |
| `source_query`      | `str` | `""`       | Search query that found this lead              |
| `source_confidence` | `str` | `"medium"` | `high` / `medium` / `low`                     |

### Website Metadata

| Field                 | Type  | Default | Description                    |
|-----------------------|-------|---------|--------------------------------|
| `business_category`   | `str` | `""`    | IG business category           |
| `bio_text`            | `str` | `""`    | Instagram bio text             |
| `website_title`       | `str` | `""`    | HTML `<title>` tag content     |
| `website_description` | `str` | `""`    | Meta description content       |

### AI Classification

| Field           | Type  | Default       | Description                         |
|-----------------|-------|---------------|-------------------------------------|
| `ai_icp_match`  | `str` | `"uncertain"` | `yes` / `uncertain`                 |
| `ai_maturity`   | `str` | `"unknown"`   | `early` / `established` / `scaled`  |

### System Fields

| Field          | Type            | Default        | Description                           |
|----------------|-----------------|----------------|---------------------------------------|
| `notes`        | `List[str]`     | `[]`           | Processing notes/errors               |
| `discovered_at`| `str`           | `utc_now()`    | ISO timestamp of discovery            |
| `verified_at`  | `str`           | `""`           | ISO timestamp of SMTP verification    |
| `run_id`       | `str`           | `""`           | Pipeline run identifier               |
| `raw_payload`  | `Dict[str,Any]` | `{}`           | Raw crawl data (not exported to Sheets)|

---

## Serialization

### `to_dict()` method

Converts the Lead to a flat dictionary for export:
- `services_found` list -> comma-separated string
- `social_links` list -> comma-separated string
- `notes` list -> pipe-separated string (`" | "`)
- `raw_payload` is included in dict but excluded from Sheets export

### `SHEET_COLUMNS` list

Defines the 43-column order for Google Sheets export. Excludes `raw_payload` and `pricing_page` (note: `pricing_page` field exists on the Lead but is not in `SHEET_COLUMNS`).

Column order:
```
lead_score, lead_tier, contact_name, email, email_status, email_source,
business_name, specialty, country, city, instagram_url, instagram_username,
followers, website, offers_online_coaching, offer_type, booking_link,
has_lead_magnet, has_pricing_page, has_testimonials, platform, weakness,
outreach_angle, personalization_note, phone, linkedin_url, youtube_url,
tiktok_url, source_url, source_type, source_query, source_confidence,
business_category, bio_text, website_title, website_description,
services_found, social_links, notes, discovered_at, verified_at,
ai_icp_match, ai_maturity, run_id
```

---

## Identity Keys (for deduplication)

A lead is identified by these unique keys (in priority order):

1. **Email address** (lowercased)
2. **Instagram username** (normalized, lowercased)
3. **Website domain** (netloc, stripped of `www.`)
4. **Source URL domain** (if different from website domain)
5. **Fallback:** `business_name:city` combination

Leads sharing any of these keys are merged during deduplication.

---

## Lead Lifecycle

```
1. Created (process_website_candidate or process_instagram_candidate)
   -> Fields set: business_name, source_*, country
   
2. Enriched (enrich_lead_from_website)
   -> Fields set: website_*, email, phone, booking_link, socials, services_found, platform
   
3. Email found/guessed (find_email_for_lead)
   -> Fields set: email, email_source
   
4. Verified (verify_leads_in_batch)
   -> Fields set: email_status, verified_at
   
5. Classified (classify_and_score)
   -> Fields set: ai_icp_match, specialty, ai_maturity, weakness, outreach_angle
   
6. Scored (score_lead)
   -> Fields set: lead_score, lead_tier
   
7. Deduplicated (deduplicate_leads)
   -> Merged with matching leads, best values kept
   
8. Exported (export_run)
   -> Written to Google Sheets via to_dict() + SHEET_COLUMNS
```
