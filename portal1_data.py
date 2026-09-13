"""
portal1_data.py — data-access layer for Portal 1 (zero-article laws).

Wraps the generic gsheets_client helpers with the schema of this
portal's two tabs ("progress", "articles"). The Streamlit apps import
only this module — never gspread directly — so the Sheets schema lives
in exactly one place.
"""

from datetime import datetime

from config import (
    SPREADSHEET_ID_PORTAL1, SPREADSHEET_NAME_PORTAL1,
    PORTAL1_ARTICLES_TAB, PORTAL1_PROGRESS_TAB,
    PORTAL1_ARTICLES_COLUMNS, PORTAL1_PROGRESS_COLUMNS,
)
from gsheets_client import open_spreadsheet, open_or_create_worksheet, read_all_rows, upsert_row_by_key


def _spreadsheet():
    return open_spreadsheet(SPREADSHEET_ID_PORTAL1, label=SPREADSHEET_NAME_PORTAL1)


def _progress_ws():
    return open_or_create_worksheet(_spreadsheet(), PORTAL1_PROGRESS_TAB, PORTAL1_PROGRESS_COLUMNS)


def _articles_ws():
    return open_or_create_worksheet(_spreadsheet(), PORTAL1_ARTICLES_TAB, PORTAL1_ARTICLES_COLUMNS)


def get_progress_rows() -> list:
    """All 13 laws with their completion status, in sheet order."""
    return read_all_rows(_progress_ws())


def get_articles_for_record(record_id: int) -> list:
    """Articles already entered for one law, sorted by article number."""
    rows = read_all_rows(_articles_ws())
    matching = [r for r in rows if str(r.get("record_id")) == str(record_id)]
    matching.sort(key=lambda r: int(r.get("article_number") or 0))
    return matching


def next_article_number(record_id: int) -> int:
    existing = get_articles_for_record(record_id)
    if not existing:
        return 1
    return max(int(r.get("article_number") or 0) for r in existing) + 1


def add_article(record_id: int, leg_name: str, leg_number: str, year: str,
                 article_number: int, article_text: str, entered_by: str) -> None:
    """Append one article row. Never overwrites — each article is its
    own row, so concurrent adds (unlikely with one volunteer, but
    still) can never clobber each other."""
    row = {
        "record_id": record_id, "Leg_Name": leg_name, "Leg_Number": leg_number, "Year": year,
        "article_number": article_number, "article_text": article_text,
        "entered_by": entered_by, "entered_at": datetime.now().isoformat(timespec="seconds"),
    }
    _articles_ws().append_row([str(row.get(c, "")) for c in PORTAL1_ARTICLES_COLUMNS])


def mark_complete(record_id: int, by: str, completed: bool = True) -> None:
    rows = get_progress_rows()
    target = next((r for r in rows if str(r.get("record_id")) == str(record_id)), None)
    if target is None:
        raise ValueError(f"record_id {record_id} not found in the progress sheet")

    target["completed"] = completed
    target["completed_by"] = by if completed else ""
    target["completed_at"] = datetime.now().isoformat(timespec="seconds") if completed else ""
    upsert_row_by_key(_progress_ws(), PORTAL1_PROGRESS_COLUMNS, "record_id", target)
