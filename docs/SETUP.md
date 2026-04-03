# Setup & Installation Guide

## Prerequisites

- Python 3.10+ (developed on 3.12)
- A Google Cloud service account with Sheets API access
- A Google Spreadsheet shared with the service account email

---

## 1. Clone the Repository

```bash
git clone https://github.com/Dead0lol/prospecting.git
cd prospecting
```

---

## 2. Install Dependencies

The `requirements.txt` is **incomplete** - it only lists `streamlit` and `pandas`. Install all actual dependencies:

```bash
pip install streamlit pandas ddgs "scrapling[fetchers]" gspread dnspython instaloader python-dotenv google-generativeai
```

Or use the corrected requirements (see [CODE_REVIEW.md](CODE_REVIEW.md) for the recommended fix):

```
streamlit
pandas
ddgs
scrapling[fetchers]
gspread
dnspython
instaloader
python-dotenv
google-generativeai
```

---

## 3. Configure Environment

Copy the example environment file and fill in your credentials:

```bash
cp .env.example .env
```

### Required settings in `.env`:

```env
# Google Sheets (REQUIRED)
GOOGLE_SHEET_NAME=Fitness Coach Leads
GOOGLE_SERVICE_ACCOUNT_FILE=service_account.json.json

# AI Classification (OPTIONAL - leave false for faster heuristic-only runs)
ENABLE_AI=false
GEMINI_API_KEY=

# Instagram (CURRENTLY UNUSED - Instaloader blocked by IG)
IG_USERNAME=
IG_PASSWORD=

# Rate Limiting
DISCOVERY_DELAY_SECONDS=3
MAX_DISCOVERY_QUERIES=40
MAX_SEARCH_RESULTS_PER_QUERY=20
WEBSITE_DELAY_SECONDS=2
SMTP_DELAY_SECONDS=3
MAX_PAGES_PER_SITE=5
REQUEST_TIMEOUT_SECONDS=20
DDGS_TIMEOUT_SECONDS=15
```

---

## 4. Set Up Google Sheets

### Create Service Account:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or use existing)
3. Enable the **Google Sheets API** and **Google Drive API**
4. Create a **Service Account** under "Credentials"
5. Generate a JSON key and download it
6. Save it as `service_account.json.json` in the project root

### Create Spreadsheet:

1. Create a new Google Spreadsheet named `Fitness Coach Leads` (or match your `.env` value)
2. Share it with the service account email (found in your JSON key file, field `client_email`)
3. Give the service account **Editor** access
4. The pipeline will create the required tabs automatically on first run

### Required tabs (created automatically):
- `Hot_Leads` - Latest run's hot leads
- `Good_Leads` - Latest run's good leads
- `Review_Queue` - Latest run's review leads
- `All_Leads` - Cumulative history (never cleared, used for deduplication)
- `Run_Log` - Run history metadata
- `Config` - Reserved

---

## 5. Run the Pipeline

### CLI Mode:

```bash
# Standard run - produces 30 leads to Google Sheets
python pipeline.py --limit 30

# Small test run with JSON output to terminal
python pipeline.py --limit 10 --json

# Quiet run logged to file
python pipeline.py --limit 50 > .cache/runs/my_run.log 2>&1
```

### Web UI Mode:

```bash
streamlit run app.py
# Opens http://localhost:8501
```

---

## 6. Verify Installation

Run a small test to verify everything works:

```bash
python pipeline.py --limit 5 --json
```

Expected output:
- Discovery queries execute against DuckDuckGo
- Websites are crawled for contact data
- SMTP verification runs on discovered emails
- Results printed as JSON to terminal
- Leads exported to Google Sheets

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'ddgs'"
Install the missing dependency: `pip install ddgs`
(This is the most common issue since `requirements.txt` is incomplete)

### "Could not load seen identities from sheet"
- Check that `GOOGLE_SHEET_NAME` matches your spreadsheet name exactly
- Verify the service account has Editor access to the sheet
- Verify `GOOGLE_SERVICE_ACCOUNT_FILE` points to the correct JSON file

### "Pipeline produces 0 leads"
- DuckDuckGo may be rate-limiting your IP - increase `DISCOVERY_DELAY_SECONDS`
- Check `.cache/runs/` for checkpoint files with error details
- Try resetting query rotation: delete `.cache/discovery_state.json`

### "All emails show 'unknown' status"
- Some mail servers block or timeout on SMTP verification
- Check `.cache/smtp/` for individual results
- SMTP verification from residential IPs is inherently unreliable

### Slow runs
- SMTP verification is the bottleneck (~5s per email domain)
- Reduce lead count for faster runs
- SMTP results are cached, so subsequent runs for the same domains are fast

---

## File Permissions

Ensure the following files are NOT committed to version control:
- `.env` - Contains live credentials
- `service_account.json.json` - Contains private key
- `.cache/` - Contains cached data

The `.gitignore` should already handle these, but verify.
