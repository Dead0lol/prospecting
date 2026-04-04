from export.sheets_writer import SheetsWriter
from gspread.exceptions import WorksheetNotFound
from models.lead import Lead, SHEET_COLUMNS


class _FakeWorksheet:
    def __init__(self, title: str, values=None):
        self.title = title
        self.values = values or []
        self.appended_rows = []
        self.cleared = False
        self.deleted_rows = []
        self.inserted_rows = []

    def append_row(self, row):
        self.appended_rows.append(row)

    def append_rows(self, rows, value_input_option=None):
        self.appended_rows.extend(rows)
        self.value_input_option = value_input_option

    def clear(self):
        self.cleared = True

    def get_all_values(self):
        return self.values

    def delete_rows(self, index):
        self.deleted_rows.append(index)

    def insert_row(self, row, index):
        self.inserted_rows.append((row, index))


class _FakeSheet:
    def __init__(self, worksheets=None):
        self._worksheets = worksheets or {}
        self.added = []

    def worksheet(self, name: str):
        if name not in self._worksheets:
            raise WorksheetNotFound(name)
        return self._worksheets[name]

    def add_worksheet(self, title: str, rows: int, cols: int):
        worksheet = _FakeWorksheet(title)
        self._worksheets[title] = worksheet
        self.added.append((title, rows, cols))
        return worksheet


def _make_writer(sheet: _FakeSheet) -> SheetsWriter:
    writer = SheetsWriter.__new__(SheetsWriter)
    writer.sheet = sheet
    writer.client = None
    return writer


def test_ensure_tabs_creates_missing_tabs_with_expected_headers() -> None:
    sheet = _FakeSheet()
    writer = _make_writer(sheet)

    writer.ensure_tabs()

    assert {title for title, _, _ in sheet.added} == {
        "Hot_Leads",
        "Good_Leads",
        "Review_Queue",
        "All_Leads",
        "Run_Log",
        "Config",
    }
    assert sheet._worksheets["Hot_Leads"].appended_rows == [SHEET_COLUMNS]
    assert sheet._worksheets["Run_Log"].appended_rows == [
        ["run_at", "status", "country", "processed", "hot", "good", "review", "notes"]
    ]
    assert sheet._worksheets["Config"].appended_rows == [["key", "value"]]


def test_ensure_all_leads_header_replaces_incorrect_header() -> None:
    worksheet = _FakeWorksheet("All_Leads", values=[["wrong", "header"]])
    writer = _make_writer(_FakeSheet({"All_Leads": worksheet}))

    writer.ensure_all_leads_header()

    assert worksheet.deleted_rows == [1]
    assert worksheet.inserted_rows == [(SHEET_COLUMNS, 1)]


def test_write_leads_serializes_rows_in_sheet_column_order() -> None:
    worksheet = _FakeWorksheet("Hot_Leads")
    writer = _make_writer(_FakeSheet({"Hot_Leads": worksheet}))
    lead = Lead(
        business_name="Coach Example",
        email="hello@example.com",
        services_found=["online coaching", "nutrition coaching"],
    )

    writer.write_leads("Hot_Leads", [lead])

    assert len(worksheet.appended_rows) == 1
    row = worksheet.appended_rows[0]
    assert len(row) == len(SHEET_COLUMNS)
    assert row[SHEET_COLUMNS.index("business_name")] == "Coach Example"
    assert row[SHEET_COLUMNS.index("email")] == "hello@example.com"
    assert row[SHEET_COLUMNS.index("services_found")] == (
        "online coaching, nutrition coaching"
    )
    assert worksheet.value_input_option == "USER_ENTERED"
