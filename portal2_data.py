"""
portal2_data.py — data-access layer for Portal 2 (empty-Status laws).

Each volunteer has their own isolated Sheet tab (config.PORTAL2_VOLUNTEER_USERNAMES) —
no shared rows, so two volunteers can never overwrite each other's work.
Column names are read from each tab's own header row at runtime
(written by push_initial_data_to_sheets.py), not hard-coded here, so
this module and the setup script can never disagree about the schema.
"""

from datetime import datetime

import gspread

from config import SPREADSHEET_ID_PORTAL2, SPREADSHEET_NAME_PORTAL2, PORTAL2_EXCLUDED_FROM_EDITING
from gsheets_client import open_spreadsheet, read_all_rows, upsert_row_by_key, get_header, is_true

# Columns a volunteer is never asked to fill even when blank — identity,
# structural, or bookkeeping fields. Leg_Name IS a real sheet column
# (context + merge-back key), just never offered as an editable input.
_NEVER_FILLABLE = PORTAL2_EXCLUDED_FROM_EDITING | {"record_id", "completed", "entered_by", "entered_at"}


def _spreadsheet():
    return open_spreadsheet(SPREADSHEET_ID_PORTAL2, label=SPREADSHEET_NAME_PORTAL2)


def _tab(username: str):
    try:
        return _spreadsheet().worksheet(username)
    except gspread.WorksheetNotFound:
        raise RuntimeError(
            f"Tab '{username}' not found in the Portal 2 spreadsheet. "
            f"Run push_initial_data_to_sheets.py first to create it."
        )


def get_columns(username: str) -> list:
    return get_header(_tab(username))


def get_rows(username: str) -> list:
    return read_all_rows(_tab(username))


def empty_fields(row: dict) -> list:
    """Keys in this row that are blank AND eligible for a volunteer to fill."""
    return [k for k, v in row.items() if k not in _NEVER_FILLABLE and str(v).strip() == ""]


def save_row(username: str, row: dict, entered_by: str) -> None:
    """Write the full row back (existing values + newly filled ones),
    marking it complete and stamping who/when."""
    columns = get_columns(username)
    row["completed"] = True
    row["entered_by"] = entered_by
    row["entered_at"] = datetime.now().isoformat(timespec="seconds")
    upsert_row_by_key(_tab(username), columns, "record_id", row)


def progress_summary(username: str) -> tuple:
    rows = get_rows(username)
    total = len(rows)
    done = sum(1 for r in rows if is_true(r.get("completed")))
    return done, total
