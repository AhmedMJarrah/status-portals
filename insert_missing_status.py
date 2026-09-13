"""
insert_missing_status.py

Purpose
-------
Add a missing "Status" key to law records in the JLexAI RefLaws JSON
dataset, without modifying any record that already has the key.

Definition of a "law record" (matches the diagnostic in
verify_status.py): any JSON object that contains a "Leg_Name" key.
This includes:
    - top-level items in the root array
    - nested amendment records inside each item's "Mod_Legs" array

Field order: the correct position for "Status" is learned from the
file itself (the first existing record of each kind — top-level vs.
nested — that already has a Status key), not hard-coded. Status is
inserted right before whichever key normally follows it, and every
other existing key in the record keeps its original order untouched.

The original input file is never modified. A new file is written to
the outputs/ folder.

Usage (Windows CMD):
    py -3.11 insert_missing_status.py
"""

import json
import logging
from datetime import datetime
from pathlib import Path

# ------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------

INPUT_FILE = Path(r"C:\Users\user\Desktop\status\RefLaws_merged_20260907_132256.json")
OUTPUT_DIR = Path(r"C:\Users\user\Desktop\status\outputs")
LOG_DIR = Path(r"C:\Users\user\Desktop\status\logs")

# ASSUMPTION: matches the earlier decision for this project — insert an
# empty string as a placeholder, to be filled in manually afterward.
# Change this single constant if you want a different default value
# (e.g. None for JSON null, or a specific status string).
STATUS_PLACEHOLDER = ""

TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT_FILE = OUTPUT_DIR / f"RefLaws_merged_status_filled_{TIMESTAMP}.json"
LOG_FILE = LOG_DIR / f"insert_missing_status_{TIMESTAMP}.log"

# From your verification report (law_status_verification.txt).
# Used only as a sanity check on this run — not a hard requirement.
EXPECTED_TOTAL_RECORDS = 4315
EXPECTED_INITIAL_MISSING = 2761


# ------------------------------------------------------------------
# Logging setup
# ------------------------------------------------------------------

def setup_logging() -> None:
    """Console shows summary-level info; the log file also gets the
    per-record detail (DEBUG) for every Status key that gets added."""
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
# Core logic
# ------------------------------------------------------------------

def get_reference_order(records) -> list | None:
    """
    Return the key order (list of key names, in original file order)
    of the first record in `records` that already has both Leg_Name
    and Status. This is the canonical schema template used to decide
    where a missing Status key belongs.

    Returns None if no such record exists (nothing to learn from).
    """
    for record in records:
        if "Leg_Name" in record and "Status" in record:
            return list(record.keys())
    return None


def insert_status_at_position(
    record: dict, template_order: list | None, path: str, stats: dict
) -> None:
    """
    Add Status=STATUS_PLACEHOLDER to `record` at the position matching
    template_order, WITHOUT reordering any other key already in the
    record. If Status is already present, the record is left completely
    untouched.
    """
    stats["total_records"] += 1

    if "Status" in record:
        stats["already_present"] += 1
        return

    stats["added"] += 1

    insert_before_key = None
    if template_order and "Status" in template_order:
        status_idx = template_order.index("Status")
        for k in template_order[status_idx + 1:]:
            if k in record:
                insert_before_key = k
                break

    new_record = {}
    inserted = False
    for k, v in record.items():
        if k == insert_before_key and not inserted:
            new_record["Status"] = STATUS_PLACEHOLDER
            inserted = True
        new_record[k] = v

    if not inserted:
        # No known "comes after Status" key was found in this specific
        # record — append at the end and flag it so it can be checked.
        new_record["Status"] = STATUS_PLACEHOLDER
        logging.warning(
            "No anchor key found for positioning — appended at end | path=%s | Leg_Name=%s",
            path, record.get("Leg_Name"),
        )

    record.clear()
    record.update(new_record)

    logging.debug(
        "Added Status | path=%s | before_key=%s | Leg_Name=%s | Leg_Number=%s | Year=%s",
        path, insert_before_key or "(end)",
        record.get("Leg_Name"), record.get("Leg_Number"), record.get("Year"),
    )


def process_laws(data: list, stats: dict) -> None:
    """Walk top-level items and their nested Mod_Legs, fixing Status."""
    top_level_template = get_reference_order(data)
    if top_level_template is None:
        logging.warning("No top-level record with an existing Status found — "
                         "cannot determine field order for top-level items.")

    all_amendments = [a for item in data for a in item.get("Mod_Legs", [])]
    nested_template = get_reference_order(all_amendments)
    if nested_template is None:
        logging.warning("No Mod_Legs record with an existing Status found — "
                         "cannot determine field order for nested amendments.")

    logging.info("Top-level field order template : %s", top_level_template)
    logging.info("Nested Mod_Legs field order template : %s", nested_template)

    for i, item in enumerate(data):
        insert_status_at_position(item, top_level_template, f"[{i}]", stats)

        for j, amendment in enumerate(item.get("Mod_Legs", [])):
            insert_status_at_position(
                amendment, nested_template, f"[{i}].Mod_Legs[{j}]", stats
            )


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------

def main() -> None:
    setup_logging()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    logging.info("Input file : %s", INPUT_FILE)
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Input file not found: {INPUT_FILE}")

    with INPUT_FILE.open("r", encoding="utf-8") as f:
        data = json.load(f)

    stats = {"total_records": 0, "added": 0, "already_present": 0}
    process_laws(data, stats)

    logging.info("Writing output: %s", OUTPUT_FILE)
    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    logging.info("=" * 60)
    logging.info("SUMMARY")
    logging.info("Total law records processed : %s", stats["total_records"])
    logging.info("Status already present       : %s", stats["already_present"])
    logging.info("Status added                 : %s", stats["added"])
    logging.info("=" * 60)

    checks_passed = True
    if stats["total_records"] != EXPECTED_TOTAL_RECORDS:
        logging.warning(
            "Total records (%s) does not match your diagnostic report (%s).",
            stats["total_records"], EXPECTED_TOTAL_RECORDS,
        )
        checks_passed = False

    if stats["added"] != EXPECTED_INITIAL_MISSING:
        logging.warning(
            "Records fixed (%s) does not match your report's missing count (%s).",
            stats["added"], EXPECTED_INITIAL_MISSING,
        )
        checks_passed = False

    if checks_passed:
        logging.info("Verification PASSED — counts match your diagnostic report.")
    else:
        logging.info("Verification FAILED — investigate before trusting the output.")

    logging.info("Original file untouched : %s", INPUT_FILE)
    logging.info("Fixed copy written to   : %s", OUTPUT_FILE)
    logging.info("Log written to          : %s", LOG_FILE)


if __name__ == "__main__":
    main()
