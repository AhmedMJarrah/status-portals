"""
enrich_status_from_reference.py

Purpose
-------
Phase 2 of the Status fix: fill in the real Status value for records
that currently have Status == "" (the placeholder inserted in phase 1),
by matching them against a reference dataset via the "URL" key.

Matching rule (as specified):
    URL is treated as a unique key. A record's Status is filled ONLY if:
        - its current Status is exactly "" (empty string), AND
        - it has a non-empty URL, AND
        - that URL is found in the reference dataset with a non-empty
          Status value there.

Records whose Status is already non-empty are left completely
untouched. Records with an empty/missing URL cannot be matched by this
method (this is expected for the ~246 recently-added laws that have no
URL yet) — they are left as-is and reported separately so they can be
handled by a different method later (e.g. Leg_Number + Year matching).

Schema-agnostic by design: instead of assuming the exact nesting of
the reference file (top-level items vs. nested Mod_Legs, or something
else entirely), this script recursively scans BOTH the reference file
and the working file for any JSON object that has a "URL" key,
wherever it appears in the structure. This avoids hard-coding an
assumption about a file we have not inspected directly.

The original phase-1 output is never modified. A new enriched file is
written to the outputs/ folder.

Usage:
    python enrich_status_from_reference.py
    python enrich_status_from_reference.py --input <path> --reference <path>
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

REFERENCE_FILE_DEFAULT = Path(
    r"C:\Users\user\Desktop\status\RefLaws_v07_CorrMeta\RefLaws_v07_CorrMeta.json"
)
# Phase-1 output naming pattern (see insert_missing_status.py)
PHASE1_GLOB = "RefLaws_merged_status_filled_*.json"

TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT_FILE = OUTPUT_DIR / f"RefLaws_merged_status_enriched_{TIMESTAMP}.json"
LOG_FILE = LOG_DIR / f"enrich_status_from_reference_{TIMESTAMP}.log"


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
# Generic, schema-agnostic record walker
# ------------------------------------------------------------------

def walk_url_records(node, path="root"):
    """
    Yield (path, record) for every dict anywhere in the JSON structure
    that has a "URL" key — regardless of nesting depth or surrounding
    schema. Works the same way for the reference file and the working
    file, so no assumption about the reference file's exact shape is
    required.
    """
    if isinstance(node, dict):
        if "URL" in node:
            yield path, node
        for k, v in node.items():
            yield from walk_url_records(v, f"{path}.{k}")
    elif isinstance(node, list):
        for i, item in enumerate(node):
            yield from walk_url_records(item, f"{path}[{i}]")


# ------------------------------------------------------------------
# Reference map
# ------------------------------------------------------------------

def build_reference_map(reference_data) -> dict:
    """
    Build {url: status} from the reference dataset. Only URLs with a
    non-empty Status value are included (nothing else is useful to
    donate). Logs a warning for any URL seen twice with conflicting
    Status values — the first one encountered wins.
    """
    url_status_map = {}
    conflicts = 0
    usable_records = 0

    for path, record in walk_url_records(reference_data):
        url = (record.get("URL") or "").strip()
        status = record.get("Status")

        if not url or not status:
            continue

        usable_records += 1

        if url in url_status_map and url_status_map[url] != status:
            conflicts += 1
            logging.warning(
                "Conflicting Status for the same URL in reference file | url=%s | kept=%r | ignored=%r | path=%s",
                url, url_status_map[url], status, path,
            )
            continue

        url_status_map[url] = status

    logging.info(
        "Reference map built: %s usable (url, status) records -> %s unique URLs (%s conflicts skipped)",
        usable_records, len(url_status_map), conflicts,
    )
    return url_status_map


# ------------------------------------------------------------------
# Enrichment
# ------------------------------------------------------------------

def enrich_records(work_data, url_status_map: dict, stats: dict) -> None:
    for path, record in walk_url_records(work_data):
        status = record.get("Status")

        if status != "":
            # Already has a real value (or has no Status key at all,
            # which should not happen after phase 1) — never touched.
            stats["already_has_value"] += 1
            continue

        url = (record.get("URL") or "").strip()

        if not url:
            stats["no_url"] += 1
            logging.debug(
                "No URL to match on | path=%s | Leg_Name=%s | Leg_Number=%s | Year=%s",
                path, record.get("Leg_Name"), record.get("Leg_Number"), record.get("Year"),
            )
            continue

        matched_status = url_status_map.get(url)

        if matched_status:
            record["Status"] = matched_status
            stats["matched"] += 1
            logging.debug(
                "Matched | path=%s | url=%s | Status<-%r | Leg_Name=%s",
                path, url, matched_status, record.get("Leg_Name"),
            )
        else:
            stats["unmatched_url"] += 1
            logging.warning(
                "URL present but not found in reference | path=%s | url=%s | Leg_Name=%s | Leg_Number=%s | Year=%s",
                path, url, record.get("Leg_Name"), record.get("Leg_Number"), record.get("Year"),
            )


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------

def find_latest_phase1_output() -> Path:
    candidates = sorted(
        OUTPUT_DIR.glob(PHASE1_GLOB), key=lambda p: p.stat().st_mtime
    )
    if not candidates:
        raise FileNotFoundError(
            f"No phase-1 output found matching {PHASE1_GLOB!r} in {OUTPUT_DIR}. "
            f"Pass --input explicitly."
        )
    return candidates[-1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=None,
                         help="Phase-1 output JSON to enrich. Defaults to the most recent "
                              f"file matching {PHASE1_GLOB!r} in {OUTPUT_DIR}.")
    parser.add_argument("--reference", type=Path, default=REFERENCE_FILE_DEFAULT,
                         help="Reference JSON containing authoritative Status values.")
    args = parser.parse_args()

    setup_logging()

    input_file = args.input or find_latest_phase1_output()
    reference_file = args.reference

    logging.info("Working file : %s", input_file)
    logging.info("Reference file : %s", reference_file)

    if not input_file.exists():
        raise FileNotFoundError(f"Working file not found: {input_file}")
    if not reference_file.exists():
        raise FileNotFoundError(f"Reference file not found: {reference_file}")

    # utf-8-sig transparently strips a leading BOM if present, and
    # behaves identically to utf-8 if there is none — safe either way.
    # The reference file (RefLaws_v07_CorrMeta.json) was saved with a
    # BOM, likely by a non-Python tool.
    with reference_file.open("r", encoding="utf-8-sig") as f:
        reference_data = json.load(f)
    with input_file.open("r", encoding="utf-8-sig") as f:
        work_data = json.load(f)

    url_status_map = build_reference_map(reference_data)

    stats = {"already_has_value": 0, "matched": 0, "no_url": 0, "unmatched_url": 0}
    enrich_records(work_data, url_status_map, stats)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(work_data, f, ensure_ascii=False, indent=2)

    logging.info("=" * 60)
    logging.info("SUMMARY")
    logging.info("Already had a Status (untouched)  : %s", stats["already_has_value"])
    logging.info("Enriched via URL match             : %s", stats["matched"])
    logging.info("Still empty — no URL to match on    : %s", stats["no_url"])
    logging.info("Still empty — URL not found in ref  : %s", stats["unmatched_url"])
    logging.info("=" * 60)

    if stats["unmatched_url"]:
        logging.warning(
            "%s records had a URL but no match in the reference file — "
            "see WARNING lines above / in the log file for details.",
            stats["unmatched_url"],
        )
    logging.info(
        "%s records remain unresolved due to missing URL (expected around 246 "
        "for the recently-added laws) — these need a different matching method.",
        stats["no_url"],
    )

    logging.info("Phase-1 file untouched : %s", input_file)
    logging.info("Enriched copy written to : %s", OUTPUT_FILE)
    logging.info("Log written to : %s", LOG_FILE)


if __name__ == "__main__":
    main()
