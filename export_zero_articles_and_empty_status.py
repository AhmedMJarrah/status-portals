"""
export_zero_articles_and_empty_status.py

Purpose
-------
Produce two diagnostic JSON files from the current working dataset:

1. laws_zero_articles_<timestamp>.json
   Full records (law + nested amendments) whose article count is
   confirmed to be zero by BOTH signals at once:
       - the "Article_Count" field value == 0
       - len(Base_Articles) + len(Reflected_Articles) == 0
   If the two signals disagree (one says zero, the other doesn't),
   the record is NOT included here — it is logged as a CONFLICT for
   manual review instead, per your instruction to report disagreement
   rather than guess.

2. laws_empty_status_<timestamp>.json
   Full records whose "Status" value is currently "" (still
   unresolved after phase 1 + phase 2).

Both files contain the exact record objects as they appear in the
working file — nothing added or reshaped. Path/location context for
each match is written to the log file only, for traceability, without
altering the output JSON's content.

The working file itself is never modified — this script only reads
and reports.

Usage:
    python export_zero_articles_and_empty_status.py
    python export_zero_articles_and_empty_status.py --input <path>
"""

import argparse
import json
import logging
from datetime import datetime
from pathlib import Path

# ------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------

WORK_DIR = Path(r"C:\Users\user\Desktop\status")
OUTPUT_DIR = WORK_DIR / "outputs"
LOG_DIR = WORK_DIR / "logs"

# Matches both phase-1 (..._filled_...) and phase-2 (..._enriched_...)
# output names — whichever is most recently modified is used.
WORKING_FILE_GLOB = "RefLaws_merged_status_*.json"

TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
ZERO_ARTICLES_FILE = OUTPUT_DIR / f"laws_zero_articles_{TIMESTAMP}.json"
EMPTY_STATUS_FILE = OUTPUT_DIR / f"laws_empty_status_{TIMESTAMP}.json"
LOG_FILE = LOG_DIR / f"export_zero_articles_and_empty_status_{TIMESTAMP}.log"

# Informational only — used for a sanity-check log line, never a hard
# requirement / failure condition.
EXPECTED_ZERO_ARTICLES = 13


# ------------------------------------------------------------------
# Logging setup
# ------------------------------------------------------------------

def setup_logging() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)


# ------------------------------------------------------------------
# Schema-agnostic law-record walker
# (same definition used throughout this project: any dict with a
# "Leg_Name" key is a law record, regardless of nesting depth)
# ------------------------------------------------------------------

def walk_law_records(node, path="root"):
    if isinstance(node, dict):
        if "Leg_Name" in node:
            yield path, node
        for k, v in node.items():
            yield from walk_law_records(v, f"{path}.{k}")
    elif isinstance(node, list):
        for i, item in enumerate(node):
            yield from walk_law_records(item, f"{path}[{i}]")


# ------------------------------------------------------------------
# Article-count logic
# ------------------------------------------------------------------

def parse_int_safe(value):
    """Return int(value) if it cleanly represents a whole number, else None."""
    if value is None:
        return None
    s = str(value).strip()
    if s == "":
        return None
    try:
        return int(s)
    except ValueError:
        return None


def article_counts(record: dict):
    """Return (field_count, list_count) for a record.

    field_count : parsed "Article_Count" value, or None if missing/unparseable.
    list_count  : len(Base_Articles) + len(Reflected_Articles), treating
                  a missing key as an empty list (Reflected_Articles only
                  exists on nested amendment records).
    """
    field_count = parse_int_safe(record.get("Article_Count"))
    list_count = len(record.get("Base_Articles") or []) + len(record.get("Reflected_Articles") or [])
    return field_count, list_count


def classify_articles(record: dict, path: str, zero_list: list, stats: dict) -> None:
    field_count, list_count = article_counts(record)

    if field_count is None:
        stats["count_unparseable"] += 1
        logging.warning(
            "Article_Count missing/unparseable | path=%s | value=%r | Leg_Name=%s",
            path, record.get("Article_Count"), record.get("Leg_Name"),
        )
        return

    if field_count == 0 and list_count == 0:
        zero_list.append(record)
        stats["zero_confirmed"] += 1
        logging.debug("Zero-article match | path=%s | Leg_Name=%s", path, record.get("Leg_Name"))
    elif field_count == 0 or list_count == 0:
        stats["conflict"] += 1
        logging.warning(
            "Article count CONFLICT (not included in output) | path=%s | "
            "Article_Count field=%s | Base+Reflected article list length=%s | Leg_Name=%s",
            path, field_count, list_count, record.get("Leg_Name"),
        )
    else:
        stats["nonzero"] += 1


def classify_status(record: dict, path: str, empty_list: list, stats: dict) -> None:
    if record.get("Status") == "":
        empty_list.append(record)
        stats["status_empty"] += 1
        logging.debug("Empty Status | path=%s | Leg_Name=%s", path, record.get("Leg_Name"))
    else:
        stats["status_nonempty"] += 1


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------

def find_latest_working_file() -> Path:
    candidates = sorted(
        OUTPUT_DIR.glob(WORKING_FILE_GLOB), key=lambda p: p.stat().st_mtime
    )
    if not candidates:
        raise FileNotFoundError(
            f"No working file found matching {WORKING_FILE_GLOB!r} in {OUTPUT_DIR}. "
            f"Pass --input explicitly."
        )
    return candidates[-1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input", type=Path, default=None,
        help="Working JSON to scan. Defaults to the most recently modified file "
             f"matching {WORKING_FILE_GLOB!r} in {OUTPUT_DIR}.",
    )
    args = parser.parse_args()

    setup_logging()

    input_file = args.input or find_latest_working_file()
    logging.info("Scanning: %s", input_file)

    if not input_file.exists():
        raise FileNotFoundError(f"Working file not found: {input_file}")

    with input_file.open("r", encoding="utf-8-sig") as f:
        data = json.load(f)

    article_stats = {"zero_confirmed": 0, "conflict": 0, "count_unparseable": 0, "nonzero": 0}
    status_stats = {"status_empty": 0, "status_nonempty": 0}

    zero_articles = []
    empty_status = []

    for path, record in walk_law_records(data):
        classify_articles(record, path, zero_articles, article_stats)
        classify_status(record, path, empty_status, status_stats)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with ZERO_ARTICLES_FILE.open("w", encoding="utf-8") as f:
        json.dump(zero_articles, f, ensure_ascii=False, indent=2)

    with EMPTY_STATUS_FILE.open("w", encoding="utf-8") as f:
        json.dump(empty_status, f, ensure_ascii=False, indent=2)

    logging.info("=" * 60)
    logging.info("SUMMARY — Article count")
    logging.info("Confirmed zero articles (both signals agree) : %s", article_stats["zero_confirmed"])
    logging.info("Conflicts (signals disagree, excluded)        : %s", article_stats["conflict"])
    logging.info("Article_Count missing/unparseable             : %s", article_stats["count_unparseable"])
    logging.info("Non-zero articles                             : %s", article_stats["nonzero"])
    if article_stats["zero_confirmed"] != EXPECTED_ZERO_ARTICLES:
        logging.warning(
            "Confirmed zero-article count (%s) differs from the expected %s — worth a manual look.",
            article_stats["zero_confirmed"], EXPECTED_ZERO_ARTICLES,
        )
    logging.info("-" * 60)
    logging.info("SUMMARY — Status")
    logging.info("Still empty      : %s", status_stats["status_empty"])
    logging.info("Has a value      : %s", status_stats["status_nonempty"])
    logging.info("=" * 60)

    logging.info("Zero-articles file : %s (%s records)", ZERO_ARTICLES_FILE, len(zero_articles))
    logging.info("Empty-status file  : %s (%s records)", EMPTY_STATUS_FILE, len(empty_status))
    logging.info("Log written to     : %s", LOG_FILE)


if __name__ == "__main__":
    main()
