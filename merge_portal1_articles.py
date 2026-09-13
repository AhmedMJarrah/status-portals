"""
merge_portal1_articles.py

Pulls the articles volunteers entered in Portal 1 (Google Sheets) and
merges them into the master laws JSON — filling in Base_Articles and
Article_Count for the 13 previously-zero-article records.

ASSUMPTION (please confirm before trusting the output): each merged
article is written as {"article_number": <int>, "text": <string>}.
This matches how the volunteer app stores them, but I have never seen
a REAL populated Base_Articles entry from your master schema to
confirm the expected key names/casing there. If your schema expects
different field names, tell me and this is a one-line change.

Matching: each of the 13 records is located in the master file by
(Leg_Name, Leg_Number, Year) — see merge_common.py. A record that
doesn't match uniquely is skipped and logged, never guessed.

The master file is never modified in place — a new file is written.

Usage:
    python merge_portal1_articles.py
    python merge_portal1_articles.py --input <path to master json>
"""

import argparse
import json
import logging
from datetime import datetime
from pathlib import Path

from config import DATA_DIR, LOG_DIR
import portal1_data as data
from gsheets_client import is_true
from merge_common import find_in_master

WORKING_FILE_GLOB = "RefLaws_merged*.json"

TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT_FILE = DATA_DIR / f"RefLaws_merged_with_articles_{TIMESTAMP}.json"
LOG_FILE = LOG_DIR / f"merge_portal1_articles_{TIMESTAMP}.log"


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

    progress_rows = data.get_progress_rows()
    logging.info("Portal 1 progress sheet: %s laws", len(progress_rows))

    stats = {"merged": 0, "not_found": 0, "no_articles_yet": 0, "not_completed": 0}

    for row in progress_rows:
        record_id = row.get("record_id")
        articles = data.get_articles_for_record(record_id)

        if not is_true(row.get("completed")):
            stats["not_completed"] += 1
            logging.info("Not marked complete yet — merging whatever exists | record_id=%s | Leg_Name=%s",
                         record_id, row.get("Leg_Name"))

        if not articles:
            stats["no_articles_yet"] += 1
            logging.warning("No articles entered yet, skipping | record_id=%s | Leg_Name=%s",
                             record_id, row.get("Leg_Name"))
            continue

        master_record = find_in_master(master_data, row, log_context="(portal 1 / articles)")
        if master_record is None:
            stats["not_found"] += 1
            continue

        new_articles = [
            {"article_number": int(a.get("article_number") or 0), "text": a.get("article_text", "")}
            for a in sorted(articles, key=lambda a: int(a.get("article_number") or 0))
        ]
        master_record["Base_Articles"] = new_articles
        master_record["Article_Count"] = str(len(new_articles))
        stats["merged"] += 1
        logging.info("Merged %s articles | Leg_Name=%s", len(new_articles), row.get("Leg_Name"))

    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(master_data, f, ensure_ascii=False, indent=2)

    logging.info("=" * 60)
    logging.info("SUMMARY")
    logging.info("Merged successfully      : %s", stats["merged"])
    logging.info("Not found in master file : %s", stats["not_found"])
    logging.info("No articles entered yet  : %s", stats["no_articles_yet"])
    logging.info("Not marked complete      : %s (merged anyway if articles existed)", stats["not_completed"])
    logging.info("=" * 60)
    logging.info("Original master file untouched : %s", master_path)
    logging.info("Merged copy written to         : %s", OUTPUT_FILE)


if __name__ == "__main__":
    main()
