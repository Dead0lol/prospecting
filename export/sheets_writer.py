from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, List

import gspread
from gspread.exceptions import WorksheetNotFound

from config.settings import settings
from models.lead import Lead, SHEET_COLUMNS


TAB_NAMES = ["Hot_Leads", "Good_Leads", "Review_Queue", "All_Leads", "Run_Log", "Config"]


class SheetsWriter:
    def __init__(self) -> None:
        self.client = gspread.service_account(filename=str(settings.google_service_account_file))
        self.sheet = self.client.open(settings.google_sheet_name)

    def ensure_tabs(self) -> None:
        for tab_name in TAB_NAMES:
            try:
                self.sheet.worksheet(tab_name)
            except WorksheetNotFound:
                worksheet = self.sheet.add_worksheet(title=tab_name, rows=1000, cols=50)
                if tab_name in {"Hot_Leads", "Good_Leads", "Review_Queue", "All_Leads"}:
                    worksheet.append_row(SHEET_COLUMNS)
                elif tab_name == "Run_Log":
                    worksheet.append_row(["run_at", "status", "country", "processed", "hot", "good", "review", "notes"])
                elif tab_name == "Config":
                    worksheet.append_row(["key", "value"])

    def clear_priority_tabs(self) -> None:
        """Clear priority tabs so they only show the latest run's leads.

        NOTE: All leads are always appended to All_Leads (never cleared),
        so no data is lost.  Priority tabs are snapshots of the most recent run.
        """
        for tab_name in ["Hot_Leads", "Good_Leads", "Review_Queue"]:
            ws = self.sheet.worksheet(tab_name)
            ws.clear()
            ws.append_row(SHEET_COLUMNS)

    def ensure_all_leads_header(self) -> None:
        ws = self.sheet.worksheet("All_Leads")
        values = ws.get_all_values()
        if not values:
            ws.append_row(SHEET_COLUMNS)
            return
        if values[0] != SHEET_COLUMNS:
            ws.delete_rows(1)
            ws.insert_row(SHEET_COLUMNS, 1)

    def write_leads(self, tab_name: str, leads: Iterable[Lead]) -> None:
        rows: List[List[str]] = []
        for lead in leads:
            payload = lead.to_dict()
            rows.append([payload.get(column, "") for column in SHEET_COLUMNS])

        if not rows:
            return

        self.sheet.worksheet(tab_name).append_rows(rows, value_input_option="USER_ENTERED")

    def log_run(self, status: str, country: str, processed: int, hot: int, good: int, review: int, notes: str = "") -> None:
        self.sheet.worksheet("Run_Log").append_row([
            datetime.now(timezone.utc).isoformat(),
            status,
            country,
            processed,
            hot,
            good,
            review,
            notes,
        ])
