from __future__ import annotations

import os
import socket
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def _get_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _default_smtp_probe_host() -> str:
    host = socket.getfqdn().strip() or socket.gethostname().strip() or "localhost"
    return host if "." in host else f"{host}.localdomain"


@dataclass(slots=True)
class Settings:
    root: Path = ROOT
    enable_ai: bool = _get_bool(os.getenv("ENABLE_AI"), False)
    openrouter_api_key: str = os.getenv("OPENROUTER_API_KEY", "")
    openrouter_model: str = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
    google_sheet_name: str = os.getenv("GOOGLE_SHEET_NAME", "Fitness Coach Leads")
    google_service_account_file: Path = Path(
        os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", ROOT / "service_account.json.json")
    )
    target_country: str = os.getenv("TARGET_COUNTRY", "US")
    discovery_delay_seconds: float = float(os.getenv("DISCOVERY_DELAY_SECONDS", "3"))
    website_delay_seconds: float = float(os.getenv("WEBSITE_DELAY_SECONDS", "2"))
    openrouter_delay_seconds: float = float(os.getenv("OPENROUTER_DELAY_SECONDS", "4"))
    request_timeout_seconds: int = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "20"))
    max_search_results_per_query: int = int(
        os.getenv("MAX_SEARCH_RESULTS_PER_QUERY", "20")
    )
    ddgs_timeout_seconds: int = int(os.getenv("DDGS_TIMEOUT_SECONDS", "15"))
    max_discovery_queries: int = int(os.getenv("MAX_DISCOVERY_QUERIES", "40"))
    max_pages_per_site: int = int(os.getenv("MAX_PAGES_PER_SITE", "5"))
    user_agent: str = os.getenv(
        "USER_AGENT",
        (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
    )
    smtp_probe_helo_name: str = os.getenv(
        "SMTP_PROBE_HELO_NAME", _default_smtp_probe_host()
    )
    smtp_probe_mail_from: str = os.getenv(
        "SMTP_PROBE_MAIL_FROM", f"postmaster@{_default_smtp_probe_host()}"
    )
    hot_lead_threshold: int = int(os.getenv("HOT_LEAD_THRESHOLD", "65"))
    good_lead_threshold: int = int(os.getenv("GOOD_LEAD_THRESHOLD", "45"))
    icebreaker_tone: str = os.getenv("ICEBREAKER_TONE", "professional and respectful")
    icebreaker_length: int = int(os.getenv("ICEBREAKER_LENGTH", "2"))
    output_cache_dir: Path = ROOT / ".cache"


settings = Settings()
settings.output_cache_dir.mkdir(exist_ok=True)
