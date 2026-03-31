"""
Fitness Coach Prospecting — Streamlit UI

Launch with:
    streamlit run app.py
"""

from __future__ import annotations

import json
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path

import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Fitness Coach Prospector",
    page_icon="🏋️",
    layout="wide",
    initial_sidebar_state="expanded",
)

ROOT = Path(__file__).parent
CACHE_DIR = ROOT / ".cache"
CACHE_DIR.mkdir(exist_ok=True)
RUNS_DIR = CACHE_DIR / "runs"
RUNS_DIR.mkdir(exist_ok=True)
CHECKPOINT_FILE = CACHE_DIR / "ui_state.json"


def load_state():
    try:
        return json.loads(CHECKPOINT_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"run_limit": 30, "last_run_id": "", "sheet_name": ""}


def save_state(state: dict) -> None:
    CHECKPOINT_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Google Sheets helpers
# ---------------------------------------------------------------------------

@st.cache_data(ttl=60)
def load_sheet_data(sheet_name: str):
    try:
        from config.settings import settings
        import gspread

        client = gspread.service_account(
            filename=str(settings.google_service_account_file)
        )
        sheet = client.open(sheet_name)
        tabs = {}
        for tab in ["Hot_Leads", "Good_Leads", "Review_Queue", "All_Leads", "Run_Log"]:
            try:
                rows = sheet.worksheet(tab).get_all_records()
                tabs[tab] = pd.DataFrame(rows) if rows else pd.DataFrame()
            except Exception:
                tabs[tab] = pd.DataFrame()
        return tabs
    except Exception as exc:
        return {"error": str(exc)}


def load_run_history(sheet_name: str) -> pd.DataFrame:
    try:
        from config.settings import settings
        import gspread

        client = gspread.service_account(
            filename=str(settings.google_service_account_file)
        )
        sheet = client.open(sheet_name)
        rows = sheet.worksheet("Run_Log").get_all_records()
        df = pd.DataFrame(rows) if rows else pd.DataFrame()
        if not df.empty and "run_at" in df.columns:
            df["run_at"] = pd.to_datetime(df["run_at"], errors="coerce")
            df = df.sort_values("run_at", ascending=False)
        return df
    except Exception:
        return pd.DataFrame()


def load_checkpoints() -> list[dict]:
    checkpoints = []
    if not RUNS_DIR.exists():
        return checkpoints
    for f in sorted(RUNS_DIR.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            checkpoints.append(data)
        except Exception:
            pass
    return checkpoints


# ---------------------------------------------------------------------------
# Pipeline runner
# ---------------------------------------------------------------------------

def run_pipeline(limit: int, sheet_name: str) -> None:
    state = load_state()
    state["run_limit"] = limit
    state["sheet_name"] = sheet_name
    save_state(state)

    cmd = [
        sys.executable,
        str(ROOT / "pipeline.py"),
        "--limit", str(limit),
    ]
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd=str(ROOT),
        text=True,
    )
    for line in iter(proc.stdout.readline, ""):
        if line:
            st.session_state["log_lines"].append(line.rstrip())


# ---------------------------------------------------------------------------
# Sidebar navigation
# ---------------------------------------------------------------------------

st.sidebar.markdown("## 🏋️ Fitness Prospector")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigate",
    ["📊 Dashboard", "📋 Leads", "▶️ Run", "⚙️ Settings"],
    index=0,
)

st.sidebar.markdown("---")
st.sidebar.caption("Built with Streamlit")

# ---------------------------------------------------------------------------
# Shared state
# ---------------------------------------------------------------------------

if "log_lines" not in st.session_state:
    st.session_state["log_lines"] = []
if "running" not in st.session_state:
    st.session_state["running"] = False
if "selected_sheet" not in st.session_state:
    state = load_state()
    try:
        from config.settings import settings
        st.session_state["selected_sheet"] = state.get("sheet_name") or settings.google_sheet_name
    except Exception:
        st.session_state["selected_sheet"] = "Fitness Coach Leads"


# ---------------------------------------------------------------------------
# PAGE: Dashboard
# ---------------------------------------------------------------------------

if page == "📊 Dashboard":
    st.title("📊 Dashboard")
    st.markdown("**Selected spreadsheet:** " + st.session_state["selected_sheet"])

    data = load_sheet_data(st.session_state["selected_sheet"])

    if "error" in data:
        st.error(f"Could not load sheet: {data['error']}")
        st.stop()

    hot = data.get("Hot_Leads", pd.DataFrame())
    good = data.get("Good_Leads", pd.DataFrame())
    review = data.get("Review_Queue", pd.DataFrame())
    all_leads = data.get("All_Leads", pd.DataFrame())
    run_history = load_run_history(st.session_state["selected_sheet"])

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("🔥 Hot Leads", len(hot))
    col2.metric("✅ Good Leads", len(good))
    col3.metric("👀 Review Queue", len(review))
    col4.metric("📦 All Leads Ever", len(all_leads))

    st.markdown("---")

    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.subheader("Recent Runs")
        if not run_history.empty:
            display = run_history[["run_at", "status", "processed", "hot", "good", "review", "notes"]].head(20).copy()
            display["run_at"] = pd.to_datetime(display["run_at"], errors="coerce").dt.strftime("%b %d %H:%M")
            st.dataframe(display, width='stretch', hide_index=True)
        else:
            st.info("No runs recorded yet. Go to **Run** to start your first pipeline run.")

    with col_right:
        st.subheader("Lead Breakdown")
        tier_counts = {
            "Hot": len(hot),
            "Good": len(good),
            "Review": len(review),
        }
        st.bar_chart(tier_counts)

        st.subheader("Email Status")
        if not all_leads.empty and "email_status" in all_leads.columns:
            email_counts = all_leads["email_status"].value_counts()
            st.bar_chart(email_counts.to_dict())

    st.markdown("---")
    st.subheader("Latest Leads (Hot + Good)")
    recent = pd.concat([hot, good]).head(20)
    if not recent.empty:
        show_cols = [
            c for c in [
                "business_name", "contact_name", "email", "website",
                "instagram_url", "lead_score", "lead_tier",
                "specialty", "offers_online_coaching", "email_status",
            ] if c in recent.columns
        ]
        st.dataframe(
            recent[show_cols],
            width='stretch',
            hide_index=True,
        )
    else:
        st.info("No leads yet. Run the pipeline to generate leads.")


# ---------------------------------------------------------------------------
# PAGE: Leads
# ---------------------------------------------------------------------------

elif page == "📋 Leads":
    st.title("📋 Leads")
    st.markdown("**Selected spreadsheet:** " + st.session_state["selected_sheet"])

    data = load_sheet_data(st.session_state["selected_sheet"])

    if "error" in data:
        st.error(f"Could not load sheet: {data['error']}")
        st.stop()

    tab_obj = st.tabs(["🔥 Hot", "✅ Good", "👀 Review", "📦 All Leads"])

    tab_map = [
        ("🔥 Hot", data.get("Hot_Leads", pd.DataFrame()), tab_obj[0]),
        ("✅ Good", data.get("Good_Leads", pd.DataFrame()), tab_obj[1]),
        ("👀 Review", data.get("Review_Queue", pd.DataFrame()), tab_obj[2]),
        ("📦 All Leads", data.get("All_Leads", pd.DataFrame()), tab_obj[3]),
    ]

    for tab_name, df, tab in tab_map:
            if df.empty:
                st.info(f"No leads in {tab_name}")
                continue

            col_search, col_tier, col_email, col_score_sort = st.columns([2, 1, 1, 1])

            with col_search:
                search = st.text_input("🔍 Search", key=f"search_{tab_name[:2]}", placeholder="Name, email, website...")
            with col_tier:
                if "lead_tier" in df.columns:
                    tier_filter = st.selectbox("Tier", ["All", "Hot", "Good", "Review"], key=f"tier_{tab_name[:2]}")
                else:
                    tier_filter = "All"
            with col_email:
                email_filter = st.selectbox("Email", ["All", "Has Email", "No Email"], key=f"email_{tab_name[:2]}")
            with col_score_sort:
                sort_by = st.selectbox("Sort by", ["Score ↓", "Score ↑", "Name A-Z", "Name Z-A"], key=f"sort_{tab_name[:2]}")

            filtered = df.copy()

            if search:
                mask = filtered.astype(str).apply(
                    lambda col: col.str.contains(search, case=False, na=False)
                ).any(axis=1)
                filtered = filtered[mask]

            if tier_filter != "All" and "lead_tier" in filtered.columns:
                filtered = filtered[filtered["lead_tier"].str.lower() == tier_filter.lower()]

            if email_filter == "Has Email" and "email" in filtered.columns:
                filtered = filtered[filtered["email"].notna() & (filtered["email"].astype(str).str.strip() != "")]
            elif email_filter == "No Email" and "email" in filtered.columns:
                filtered = filtered[filtered["email"].isna() | (filtered["email"].astype(str).str.strip() == "")]

            if sort_by == "Score ↓" and "lead_score" in filtered.columns:
                filtered = filtered.sort_values("lead_score", ascending=False)
            elif sort_by == "Score ↑" and "lead_score" in filtered.columns:
                filtered = filtered.sort_values("lead_score", ascending=True)
            elif sort_by == "Name A-Z" and "business_name" in filtered.columns:
                filtered = filtered.sort_values("business_name", ascending=True)
            elif sort_by == "Name Z-A" and "business_name" in filtered.columns:
                filtered = filtered.sort_values("business_name", ascending=False)

            st.caption(f"**{len(filtered)}** leads shown (of **{len(df)}** total)")

            cols_to_show = [
                "business_name", "contact_name", "email", "website",
                "instagram_url", "lead_score", "lead_tier",
                "specialty", "offers_online_coaching", "email_status",
            ]
            display_cols = [c for c in cols_to_show if c in filtered.columns]

            st.dataframe(
                filtered[display_cols],
                width='stretch',
                hide_index=True,
            )

            if st.download_button(
                f"⬇️ Download {tab_name} CSV",
                data=filtered.to_csv(index=False).encode("utf-8"),
                file=f"leads_{tab_name.replace(' ', '_').lower()}.csv",
                mime="text/csv",
                key=f"dl_{tab_name[:2]}",
            ):
                st.success(f"Downloaded {len(filtered)} leads as CSV")


# ---------------------------------------------------------------------------
# PAGE: Run
# ---------------------------------------------------------------------------

elif page == "▶️ Run":
    st.title("▶️ Run Pipeline")
    st.markdown("**Selected spreadsheet:** " + st.session_state["selected_sheet"])

    state = load_state()
    default_limit = state.get("run_limit", 30)

    col_limit, col_run = st.columns([1, 1])

    with col_limit:
        limit = st.number_input(
            "Number of leads to find",
            min_value=5,
            max_value=200,
            value=default_limit,
            step=5,
            help="How many fresh leads to generate this run. More leads = longer run time.",
        )

    with col_run:
        run_pressed = st.button(
            "🚀 Run Pipeline",
            type="primary",
            use_container_width=True,
            disabled=st.session_state.get("running", False),
        )

    st.markdown("---")

    if run_pressed and not st.session_state.get("running"):
        st.session_state["running"] = True
        st.session_state["log_lines"] = []

        progress_placeholder = st.empty()
        log_placeholder = st.empty()

        progress_placeholder.info("🔄 Pipeline running... This can take 15-30 minutes for 30 leads.")

        thread = threading.Thread(target=run_pipeline, args=(limit, st.session_state["selected_sheet"]), daemon=True)
        thread.start()

        import time
        while thread.is_alive():
            time.sleep(2)
            if st.session_state["log_lines"]:
                recent = st.session_state["log_lines"][-50:]
                log_placeholder.code("\n".join(recent), language=None)

        thread.join()
        st.session_state["running"] = False

        st.session_state["log_lines"].append("✅ Pipeline finished!")
        st.success("✅ Pipeline finished! Refresh the page to see updated lead counts.")
        st.session_state["log_lines"] = []

    if st.session_state.get("log_lines"):
        st.subheader("Pipeline Log")
        st.code("\n".join(st.session_state["log_lines"][-80:]), language=None)

    st.markdown("---")
    st.subheader("Checkpoints from previous runs")

    checkpoints = load_checkpoints()
    if checkpoints:
        for cp in checkpoints[:5]:
            with st.expander(f"Run {cp.get('run_id', 'unknown')} — {cp.get('saved_at', '')[:19]} — {cp.get('lead_count', 0)} leads"):
                leads = cp.get("leads", [])
                if leads:
                    df = pd.DataFrame(leads)
                    cols = [c for c in ["business_name", "email", "website", "lead_score", "lead_tier"] if c in df.columns]
                    st.dataframe(df[cols], width='stretch', hide_index=True)
    else:
        st.info("No checkpoint files found in .cache/runs/")


# ---------------------------------------------------------------------------
# PAGE: Settings
# ---------------------------------------------------------------------------

elif page == "⚙️ Settings":
    st.title("⚙️ Settings")

    try:
        from config.settings import settings
        st.markdown("#### Pipeline Settings")
        settings_data = {
            "Setting": [
                "AI Enabled",
                "Hot Lead Threshold",
                "Good Lead Threshold",
                "Max Discovery Queries / run",
                "Discovery Delay (seconds)",
                "Max Search Results / query",
                "SMTP Workers",
                "Website Delay (seconds)",
                "DDGS Timeout (seconds)",
                "Max Pages / site",
                "Request Timeout (seconds)",
                "Google Sheet",
            ],
            "Value": [
                settings.enable_ai,
                settings.hot_lead_threshold,
                settings.good_lead_threshold,
                settings.max_discovery_queries,
                settings.discovery_delay_seconds,
                settings.max_search_results_per_query,
                5,
                settings.website_delay_seconds,
                settings.ddgs_timeout_seconds,
                settings.max_pages_per_site,
                settings.request_timeout_seconds,
                st.session_state["selected_sheet"],
            ],
        }
        st.dataframe(pd.DataFrame(settings_data), hide_index=True, use_container_width=True)
    except Exception as exc:
        st.error(f"Could not load settings: {exc}")

    st.markdown("---")
    st.markdown("#### Discovery Keywords")
    try:
        from config.keywords import (
            DIGITAL_SELLER_KEYWORDS,
            ONLINE_COACH_KEYWORDS,
            TRANSFORMATION_KEYWORDS,
            NICHE_COACH_KEYWORDS,
            BUSINESS_COACH_KEYWORDS,
            DISCOVERY_MODIFIERS,
            COACH_PLATFORM_DOMAINS,
        )
        kws = {
            "Keyword Tier": [
                "Digital Sellers 🔥",
                "Online Coaches 🌐",
                "Transformation 🔄",
                "Niche Audience 🎯",
                "Business-Minded 💼",
                "Intent Modifiers ✨",
                "Coach Platforms 🏪",
            ],
            "Count": [
                len(DIGITAL_SELLER_KEYWORDS),
                len(ONLINE_COACH_KEYWORDS),
                len(TRANSFORMATION_KEYWORDS),
                len(NICHE_COACH_KEYWORDS),
                len(BUSINESS_COACH_KEYWORDS),
                len(DISCOVERY_MODIFIERS),
                len(COACH_PLATFORM_DOMAINS),
            ],
        }
        st.dataframe(pd.DataFrame(kws), hide_index=True, use_container_width=True)
    except Exception as exc:
        st.error(f"Could not load keywords: {exc}")

    st.markdown("---")
    st.markdown("#### Cache Stats")
    col_smtp, col_runs = st.columns(2)

    with col_smtp:
        smtp_cache = CACHE_DIR / "smtp"
        smtp_count = len(list(smtp_cache.glob("*.json"))) if smtp_cache.exists() else 0
        st.metric("SMTP Cache Entries", smtp_count)

    with col_runs:
        run_count = len(list(RUNS_DIR.glob("*.json"))) if RUNS_DIR.exists() else 0
        st.metric("Checkpoint Files", run_count)

    if st.button("🗑️ Clear SMTP Cache"):
        if smtp_cache.exists():
            for f in smtp_cache.glob("*.json"):
                f.unlink()
            st.success("SMTP cache cleared!")
            st.rerun()

    if st.button("🗑️ Clear Checkpoints"):
        if RUNS_DIR.exists():
            for f in RUNS_DIR.glob("*.json"):
                f.unlink()
            st.success("Checkpoints cleared!")
            st.rerun()

    st.markdown("---")
    st.markdown("#### Discovery State")
    ds_file = CACHE_DIR / "discovery_state.json"
    if ds_file.exists():
        ds = json.loads(ds_file.read_text(encoding="utf-8"))
        st.json(ds)
    else:
        st.info("No discovery state file found.")
