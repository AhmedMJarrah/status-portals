"""
merge_portal2_status.py

Pulls what all 5 volunteers entered in Portal 2 (Status, URL, and any
other field they filled in) and merges it into the master laws JSON.

Run this AFTER merge_portal1_articles.py so the final file has both
the articles and the status fixes together — this script auto-detects
whichever master file is newest, so running them in that order chains
correctly with no manual file-juggling.

Matching: each of the 257 records is located in the master file by
(Leg_Name, Leg_Number, Year) — see merge_common.py. A record that
doesn't match uniquely is skipped and logged, never guessed. Only
fields the volunteer actually filled in are written — anything they
left blank is left exactly as it was.

The master file is never modified in place — a new file is written.

Usage:
    python merge_portal2_status.py
    python merge_portal2_status.py --input <path to master json>
"""

import argparse
import json
import logging
from datetime import datetime
from pathlib import Path

from config import DATA_DIR, LOG_DIR, PORTAL2_VOLUNTEER_USERNAMES, PORTAL2_EXCLUDED_FROM_EDITING
import portal2_data as data
from gsheets_client import is_true
from merge_common import find_in_master

WORKING_FILE_GLOB = "RefLaws_merged*.json"

TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT_FILE = DATA_DIR / f"RefLaws_merged_final_{TIMESTAMP}.json"
LOG_FILE = LOG_DIR / f"merge_portal2_status_{TIMESTAMP}.log"

# Sheet bookkeeping columns that were never part of the master schema —
# these never get written into a master record.
_SHEET_ONLY_COLUMNS = {"record_id", "completed", "entered_by", "entered_at"}


def setup_logging() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8"), logging.StreamHandler()],
    )


def find_latest_master_file() -> Path:
    candidates = sorted(DATA_DIR.glob(WORKING_FILE_GLOB), key=lambda p: p.stat().st_mtime)
    if not candidates:
        raise FileNotFoundError(f"No master file found matching {WORKING_FILE_GLOB!r} in {DATA_DIR}.")
    return candidates[-1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=None,
                         help=f"Master JSON to merge into. Defaults to the most recent file "
                              f"matching {WORKING_FILE_GLOB!r} in {DATA_DIR}.")
    args = parser.parse_args()

    setup_logging()

    master_path = args.input or find_latest_master_file()
    logging.info("Master file: %s", master_path)

    with master_path.open("r", encoding="utf-8-sig") as f:
        master_data = json.load(f)

    stats = {"merged": 0, "not_found": 0, "not_completed_skipped": 0, "no_fields_filled": 0}

    for username in PORTAL2_VOLUNTEER_USERNAMES:
        rows = data.get_rows(username)
        logging.info("Volunteer %s: %s assigned records", username, len(rows))

        for row in rows:
            if not is_true(row.get("completed")):
                stats["not_completed_skipped"] += 1
                logging.info("Not marked complete, skipped | record_id=%s | Leg_Name=%s | volunteer=%s",
                             row.get("record_id"), row.get("Leg_Name"), username)
                continue

            master_record = find_in_master(master_data, row, log_context=f"(portal 2 / {username})")
            if master_record is None:
                stats["not_found"] += 1
                continue

            filled_any = False
            for key, value in row.items():
                if key in _SHEET_ONLY_COLUMNS or key in PORTAL2_EXCLUDED_FROM_EDITING:
                    continue
                # Only ever fill what was actually blank in the master record —
                # never overwrite a value that was already there.
                if str(master_record.get(key, "")).strip() == "" and str(value).strip() != "":
                    master_record[key] = value
                    filled_any = True

            if filled_any:
                stats["merged"] += 1
                logging.info("Merged fields | Leg_Name=%s | volunteer=%s", row.get("Leg_Name"), username)
            else:
                stats["no_fields_filled"] += 1

    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(master_data, f, ensure_ascii=False, indent=2)

    logging.info("=" * 60)
    logging.info("SUMMARY")
    logging.info("Merged successfully       : %s", stats["merged"])
    logging.info("Not found in master file  : %s", stats["not_found"])
    logging.info("Skipped (not completed)   : %s", stats["not_completed_skipped"])
    logging.info("Completed but nothing new : %s", stats["no_fields_filled"])
    logging.info("=" * 60)
    logging.info("Previous master file untouched : %s", master_path)
    logging.info("Final merged file written to   : %s", OUTPUT_FILE)


if __name__ == "__main__":
    main()
