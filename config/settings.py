from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def _split_csv(value: str | None, default: List[str]) -> List[str]:
    if not value:
        return default
    return [item.strip() for item in value.split(",") if item.strip()]


def _get_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(slots=True)
class Settings:
    root: Path = ROOT
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    enable_ai: bool = _get_bool(os.getenv("ENABLE_AI"), False)
    ig_username: str = os.getenv("IG_USERNAME", "")
    ig_password: str = os.getenv("IG_PASSWORD", "")
    google_sheet_name: str = os.getenv("GOOGLE_SHEET_NAME", "Fitness Coach Leads")
    google_service_account_file: Path = Path(
        os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", ROOT / "service_account.json.json")
    )
    target_country: str = os.getenv("TARGET_COUNTRY", "US")
    target_cities: List[str] = field(
        default_factory=lambda: _split_csv(os.getenv("TARGET_CITIES"), [])
    )
    discovery_delay_seconds: float = float(os.getenv("DISCOVERY_DELAY_SECONDS", "3"))
    instagram_delay_seconds: float = float(os.getenv("INSTAGRAM_DELAY_SECONDS", "4"))
    website_delay_seconds: float = float(os.getenv("WEBSITE_DELAY_SECONDS", "2"))
    smtp_delay_seconds: float = float(os.getenv("SMTP_DELAY_SECONDS", "3"))
    gemini_delay_seconds: float = float(os.getenv("GEMINI_DELAY_SECONDS", "4"))
    profile_batch_size: int = int(os.getenv("PROFILE_BATCH_SIZE", "50"))
    request_timeout_seconds: int = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "20"))
    max_search_results_per_query: int = int(os.getenv("MAX_SEARCH_RESULTS_PER_QUERY", "20"))
    ddgs_timeout_seconds: int = int(os.getenv("DDGS_TIMEOUT_SECONDS", "15"))
    max_discovery_queries: int = int(os.getenv("MAX_DISCOVERY_QUERIES", "20"))
    max_pages_per_site: int = int(os.getenv("MAX_PAGES_PER_SITE", "5"))
    user_agent: str = os.getenv(
        "USER_AGENT",
        (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
    )
    hot_lead_threshold: int = int(os.getenv("HOT_LEAD_THRESHOLD", "65"))
    good_lead_threshold: int = int(os.getenv("GOOD_LEAD_THRESHOLD", "45"))
    output_cache_dir: Path = ROOT / ".cache"


settings = Settings()
settings.output_cache_dir.mkdir(exist_ok=True)
