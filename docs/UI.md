# Streamlit UI Documentation

## Overview

The Streamlit web UI (`app.py`) provides a browser-based interface for managing and monitoring the prospecting pipeline. It reads data from Google Sheets and local cache files.

**Launch:** `streamlit run app.py`
**URL:** `http://localhost:8501`

---

## Pages

### 1. Dashboard (`lines 186-252`)

The main overview page showing lead counts and run history.

**Components:**
- **Metric cards (4 columns):**
  - Hot Leads count
  - Good Leads count
  - Review Queue count
  - All Leads Ever count

- **Recent Runs table:** Displays the last 20 runs from Run_Log with timestamp, status, and lead counts

- **Lead Breakdown chart:** Bar chart showing Hot/Good/Review distribution

- **Email Status chart:** Bar chart showing email verification status distribution across all leads

- **Latest Leads table:** Combined Hot + Good leads (top 20) showing key columns

---

### 2. Leads (`lines 259-344`)

Searchable and filterable lead browser with tabbed views.

**Tabs:** Hot | Good | Review | All Leads

**Filters per tab:**
- **Text search:** Searches across all columns (case-insensitive)
- **Tier filter:** All / Hot / Good / Review
- **Email filter:** All / Has Email / No Email
- **Sort by:** Score (desc/asc) / Name (A-Z/Z-A)

**Displayed columns:**
```
business_name, contact_name, email, website,
instagram_url, lead_score, lead_tier,
specialty, offers_online_coaching, email_status
```

**Actions:**
- CSV download button per tab

---

### 3. Run (`lines 351-428`)

Pipeline execution controls with live log output.

**Components:**
- **Number input:** Lead count (5-200, step of 5, default from last run)
- **Run Pipeline button:** Launches `pipeline.py` as a subprocess
- **Live log viewer:** Streams pipeline stdout in real-time (last 50 lines during run, last 80 after)
- **Checkpoint viewer:** Expandable sections showing data from the last 5 checkpoint files

**How it works:**
1. User clicks "Run Pipeline"
2. `run_pipeline()` spawns `pipeline.py` as a subprocess via `subprocess.Popen`
3. A background `threading.Thread` reads stdout line-by-line
4. Streamlit polls every 2 seconds and displays new log lines
5. On completion, shows success message and triggers page refresh

---

### 4. Settings (`lines 435-545`)

Configuration viewer and cache management.

**Components:**

- **Pipeline Settings table:** Displays all key config values:
  - AI Enabled, Hot/Good thresholds, Discovery queries, delays, timeouts, etc.

- **Discovery Keywords table:** Shows keyword tier names and counts

- **Cache Stats:**
  - SMTP Cache Entries count
  - Checkpoint Files count
  - "Clear SMTP Cache" button
  - "Clear Checkpoints" button

- **Discovery State viewer:** JSON display of `.cache/discovery_state.json`

---

## Data Sources

The UI reads from two sources:

### Google Sheets (via `gspread`)
- `load_sheet_data()` - Cached for 60 seconds (`@st.cache_data(ttl=60)`)
- Reads tabs: Hot_Leads, Good_Leads, Review_Queue, All_Leads, Run_Log
- Each tab converted to a Pandas DataFrame

### Local Cache Files
- `.cache/ui_state.json` - UI state persistence (run limit, sheet name)
- `.cache/runs/*.json` - Checkpoint files from pipeline runs
- `.cache/smtp/*.json` - SMTP cache entries (count only)
- `.cache/discovery_state.json` - Query rotation state

---

## State Management

### Session State
- `st.session_state["selected_sheet"]` - Currently selected Google Sheet name

### Pipeline State
- `_pipeline_state` - Module-level `PipelineState` object tracking:
  - `lines: list[str]` - Log output lines
  - `running: bool` - Pipeline execution status
  - `done: bool` - Completion flag

### Persistent State
- `load_state()` / `save_state()` - Reads/writes `.cache/ui_state.json`

---

## Known Issues

1. **Indentation bug in Leads page (line 279):** The content inside the tab loop uses inconsistent indentation - content renders outside the tab context, causing all tabs to show the same filtering UI and potentially displaying incorrect data.

2. **Infinite rerun loop risk (lines 397-402):** The `while thread.is_alive()` loop calls `st.rerun()` inside a `time.sleep(2)` loop. Each `st.rerun()` restarts the entire script, and the thread reference from the previous execution is lost. The loop condition `not _pipeline_state.done` plus `thread.is_alive()` on a stale thread object could cause unexpected behavior.

3. **Data loading performance:** Each page load triggers a Google Sheets API call (cached for 60 seconds). For large sheets, this can be slow.

4. **No authentication:** The UI has no login or access control. It's assumed to run locally only.

5. **Width parameter:** `st.dataframe(width='stretch')` - The `width` parameter expects an integer, not a string. This may cause warnings in newer Streamlit versions. The correct parameter is `use_container_width=True`.
