"""
gsheets_client.py — shared Google Sheets access layer for both volunteer
portals.

Uses a service account (no interactive OAuth — correct for a
server-side Streamlit app). Credentials path comes from the
GOOGLE_SERVICE_ACCOUNT_FILE environment variable (see config.py).

This module knows nothing about either portal's specific schema — it's
a thin, reusable wrapper around gspread for:
    - opening/creating a spreadsheet and worksheet (tab)
    - reading all rows as a list of dicts (header row = keys)
    - overwriting a whole sheet (initial setup only)
    - upserting a single row by a key column (used by the live apps,
      so one volunteer's submit never touches another row — safe for
      concurrent remote users)
"""

import logging
from functools import lru_cache

import gspread
from google.oauth2.service_account import Credentials

from config import GOOGLE_SERVICE_ACCOUNT_FILE

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


@lru_cache(maxsize=1)
def get_client() -> gspread.Client:
    creds = Credentials.from_service_account_file(GOOGLE_SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    return gspread.authorize(creds)


def open_spreadsheet(spreadsheet_id: str, label: str = "") -> gspread.Spreadsheet:
    """Open an EXISTING spreadsheet by its ID (the long string in its
    URL: docs.google.com/spreadsheets/d/<ID>/edit).

    ID, not name: a name can be changed or duplicated later and would
    silently break/misdirect a script that runs unattended; the ID is
    fixed for the life of the file.

    Deliberately does NOT create the spreadsheet. A service account
    outside a Google Workspace Shared Drive has no Drive storage quota
    of its own — calling client.create() fails with a 403
    storageQuotaExceeded error, not just an invisibility problem.

    You must create the spreadsheet yourself (in your own Google
    Drive) and share it with the service account's email — Editor
    access — before running this. Find that email by running
    show_service_account_email.py.
    """
    client = get_client()
    try:
        return client.open_by_key(spreadsheet_id)
    except gspread.SpreadsheetNotFound:
        raise RuntimeError(
            f"Spreadsheet{' ' + label if label else ''} (id={spreadsheet_id}) "
            f"was not found, or isn't shared with the service account yet. "
            f"Create it yourself in Google Sheets, share it — Editor access — "
            f"with the service account's email (run "
            f"show_service_account_email.py to see it), then put its ID "
            f"(from the URL) in .env."
        )


def open_or_create_worksheet(spreadsheet: gspread.Spreadsheet, tab_name: str, columns: list) -> gspread.Worksheet:
    try:
        ws = spreadsheet.worksheet(tab_name)
    except gspread.WorksheetNotFound:
        logging.info("Worksheet %r not found in %r — creating it.", tab_name, spreadsheet.title)
        ws = spreadsheet.add_worksheet(title=tab_name, rows=2000, cols=max(len(columns), 10))
        ws.append_row(columns)
    return ws


def read_all_rows(worksheet: gspread.Worksheet) -> list:
    """Return every data row as a dict keyed by the header row."""
    return worksheet.get_all_records()


def write_all_rows(worksheet: gspread.Worksheet, columns: list, rows: list) -> None:
    """Overwrite the ENTIRE sheet: header + all rows.

    Only for one-time initial setup (push_initial_data_to_sheets.py).
    Never call this from a live volunteer app — it would erase
    everyone else's work. Live apps use upsert_row_by_key instead.
    """
    worksheet.clear()
    values = [columns] + [[str(row.get(col, "")) for col in columns] for row in rows]
    worksheet.update(values)


def get_header(worksheet) -> list:
    """Return the header row (column names, in sheet order)."""
    return worksheet.row_values(1)


def is_true(value) -> bool:
    """Normalize a Sheets cell value (always read back as a plain
    string) into a bool. Used for the 'completed' columns."""
    return str(value).strip().lower() in ("true", "1", "yes")


def upsert_row_by_key(worksheet: gspread.Worksheet, columns: list, key_column: str, row: dict) -> None:
    """Update the row where row[key_column] matches an existing row, or
    append a new row if no match is found. This is what the live
    volunteer apps call on submit — it only ever touches the one row
    being edited."""
    key_value = str(row.get(key_column, ""))
    key_col_index = columns.index(key_column) + 1

    try:
        cell = worksheet.find(key_value, in_column=key_col_index)
    except gspread.exceptions.CellNotFound:
        cell = None

    values = [str(row.get(col, "")) for col in columns]

    if cell:
        worksheet.update(f"A{cell.row}", [values])
        logging.debug("Updated row %s (key=%s)", cell.row, key_value)
    else:
        worksheet.append_row(values)
        logging.debug("Appended new row (key=%s)", key_value)
