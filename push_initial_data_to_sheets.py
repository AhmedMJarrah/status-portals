"""
push_initial_data_to_sheets.py

One-time setup script: reads the two phase-3 export files and populates
the two Google Sheets spreadsheets the volunteer portals will use.

Portal 1 (zero articles):
    - "articles" tab: header only (volunteers add article rows live via
      the app — nothing to pre-fill here).
    - "progress" tab: one row per law (13 rows), completed=False.

Portal 2 (empty status):
    - 257 records split round-robin across 5 tabs, one per volunteer,
      fully isolated (no record appears in more than one tab).
    - Sheet columns = every key found in ANY record across the file,
      except the small excluded set in config.PORTAL2_EXCLUDED_FROM_SHEET
      — so the sheet adapts to the real data instead of a hard-coded
      field list. (Leg_Name is kept as a column — it's excluded from
      EDITING, not from the sheet, since it's needed for context and
      as the merge-back matching key.)

WARNING: this OVERWRITES both spreadsheets from the source JSON. Run it
once, before volunteers start. Do not re-run it after they've begun
entering data — that would erase their work.

PREREQUISITE: create two blank Google Sheets yourself first, share each
with the service account's email (Editor access — run
show_service_account_email.py to get that address), then put each
sheet's ID (the long string in its URL) into .env as
SPREADSHEET_ID_PORTAL1 / SPREADSHEET_ID_PORTAL2. This script only opens
existing, shared spreadsheets; it does not create them (a bare service
account has no Drive storage quota of its own to create files with).

Usage:
    python push_initial_data_to_sheets.py
"""

import json
import logging
from datetime import datetime
from pathlib import Path

from config import (
    ZERO_ARTICLES_SOURCE, EMPTY_STATUS_SOURCE, LOG_DIR,
    SPREADSHEET_ID_PORTAL1, SPREADSHEET_ID_PORTAL2,
    SPREADSHEET_NAME_PORTAL1, SPREADSHEET_NAME_PORTAL2,
    PORTAL1_ARTICLES_TAB, PORTAL1_PROGRESS_TAB,
    PORTAL1_ARTICLES_COLUMNS, PORTAL1_PROGRESS_COLUMNS,
    PORTAL2_VOLUNTEER_USERNAMES, PORTAL2_EXCLUDED_FROM_SHEET,
)
from gsheets_client import open_spreadsheet, open_or_create_worksheet, write_all_rows

TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_FILE = LOG_DIR / f"push_initial_data_to_sheets_{TIMESTAMP}.log"


def setup_logging() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8"), logging.StreamHandler()],
    )


def load_json(path: Path):
    with path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def setup_portal1(records: list) -> None:
    spreadsheet = open_spreadsheet(SPREADSHEET_ID_PORTAL1, label=SPREADSHEET_NAME_PORTAL1)

    articles_ws = open_or_create_worksheet(spreadsheet, PORTAL1_ARTICLES_TAB, PORTAL1_ARTICLES_COLUMNS)
    write_all_rows(articles_ws, PORTAL1_ARTICLES_COLUMNS, [])  # header only

    progress_rows = [
        {
            "record_id": i,
            "Leg_Name": r.get("Leg_Name", ""),
            "Leg_Number": r.get("Leg_Number", ""),
            "Year": r.get("Year", ""),
            "completed": False,
            "completed_by": "",
            "completed_at": "",
        }
        for i, r in enumerate(records)
    ]
    progress_ws = open_or_create_worksheet(spreadsheet, PORTAL1_PROGRESS_TAB, PORTAL1_PROGRESS_COLUMNS)
    write_all_rows(progress_ws, PORTAL1_PROGRESS_COLUMNS, progress_rows)

    logging.info(
        "Portal 1: %s laws loaded into tabs %r (empty) and %r (%s rows)",
        len(records), PORTAL1_ARTICLES_TAB, PORTAL1_PROGRESS_TAB, len(progress_rows),
    )


def build_portal2_columns(records: list) -> list:
    """Union of every key across all records, preserving first-seen
    order, minus only the structural/list fields that can't sensibly
    become a spreadsheet column. Leg_Name IS kept as a column here —
    it must never be edited, but it must exist for context and for
    the merge-back matching key (see PORTAL2_EXCLUDED_FROM_EDITING,
    which is the separate, narrower exclusion used for that)."""
    columns = []
    seen = set()
    for r in records:
        for k in r.keys():
            if k not in seen and k not in PORTAL2_EXCLUDED_FROM_SHEET:
                seen.add(k)
                columns.append(k)
    return ["record_id"] + columns + ["completed", "entered_by", "entered_at"]


def setup_portal2(records: list) -> None:
    columns = build_portal2_columns(records)
    spreadsheet = open_spreadsheet(SPREADSHEET_ID_PORTAL2, label=SPREADSHEET_NAME_PORTAL2)

    n_volunteers = len(PORTAL2_VOLUNTEER_USERNAMES)
    buckets = {u: [] for u in PORTAL2_VOLUNTEER_USERNAMES}

    for i, r in enumerate(records):
        username = PORTAL2_VOLUNTEER_USERNAMES[i % n_volunteers]
        row = {"record_id": i, "completed": False, "entered_by": "", "entered_at": ""}
        for col in columns:
            if col not in row:
                row[col] = r.get(col, "")
        buckets[username].append(row)

    for username, rows in buckets.items():
        ws = open_or_create_worksheet(spreadsheet, username, columns)
        write_all_rows(ws, columns, rows)
        logging.info("Portal 2: %s records assigned to tab %r", len(rows), username)


def main() -> None:
    setup_logging()

    logging.info("Loading source files")
    zero_articles = load_json(ZERO_ARTICLES_SOURCE)
    empty_status = load_json(EMPTY_STATUS_SOURCE)
    logging.info("Zero-articles source : %s records", len(zero_articles))
    logging.info("Empty-status source  : %s records", len(empty_status))

    setup_portal1(zero_articles)
    setup_portal2(empty_status)

    logging.info("Done. Both spreadsheets are populated and ready for the volunteer apps.")


if __name__ == "__main__":
    main()
