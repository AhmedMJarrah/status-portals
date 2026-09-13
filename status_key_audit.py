"""
status_key_audit.py

Audits the "Status" key across items in a JLexAI legislation JSON file
(RefLaws_merged_*.json).

What it does:
1. Loads the JSON file (top-level LIST of record dicts).
2. Builds a schema report: every key seen anywhere across top-level items,
   how many items have it, and what value type(s) were observed.
3. Checks each top-level item for the presence of a target key (default:
   "Status") and counts items that have it vs. items missing it.
4. Recursively counts a given key (default: "Leg_Name") across BOTH
   top-level items AND nested items inside "Mod_Legs", to reconcile against
   a manual/raw text-search count of that key across the whole file.
5. Compares the set of items missing "Status" against the set missing a
   second key (default: "DetailedName") to check if they're identical.
6. Classifies items missing the target key by whether a marker substring
   (default: "معدل") appears in their Leg_Name.
7. Flags nested Mod_Legs entries that unexpectedly DO carry the target key
   (structural anomaly worth a manual look).
8. Writes ONE .txt report with all of the above, full missing-item list at
   the very end.
9. Only with --insert-status: writes a SEPARATE, isolated copy of the JSON
   with the missing key inserted as an empty string (""). The original
   input file is NEVER modified.

Usage (Windows CMD):
    py -3.11 status_key_audit.py
    py -3.11 status_key_audit.py --insert-status
    py -3.11 status_key_audit.py --key Status --id-field Leg_Name

No third-party dependencies -- standard library only.
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(r"C:\Users\user\Desktop\status")
INPUT_JSON = PROJECT_ROOT / "RefLaws_merged_20260907_132256.json"
LOGS_DIR = PROJECT_ROOT / "logs"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"

NESTED_LIST_KEY = "Mod_Legs"          # key holding nested amendment records
RECURSIVE_COUNT_KEY = "Leg_Name"      # key to reconcile against a manual text-search count
SECOND_KEY = "DetailedName"           # compared against the main target key
SPLIT_MARKER = "معدل"                 # substring used to classify base vs amendment-style names

TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")


def setup_logging() -> logging.Logger:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOGS_DIR / f"status_audit_{TIMESTAMP}.log"

    logger = logging.getLogger("status_audit")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))

    # Console only ever gets English/ASCII summary lines -- Arabic content
    # (item identifiers) is written to the .txt report file only, never
    # printed, to avoid Windows CMD codepage encoding errors.
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter("%(message)s"))

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger


def load_json(path: Path, logger: logging.Logger) -> list:
    if not path.exists():
        logger.error(f"Input file not found: {path}")
        raise FileNotFoundError(path)

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise TypeError(
            f"Expected the JSON top level to be a list (array), got "
            f"{type(data).__name__} instead."
        )

    logger.info(f"Loaded {len(data)} top-level items from {path.name}")
    return data


def build_schema(items: list) -> dict:
    schema: dict = {}
    total = len(items)

    for item in items:
        if not isinstance(item, dict):
            continue
        for key, value in item.items():
            entry = schema.setdefault(key, {"count": 0, "types": set()})
            entry["count"] += 1
            entry["types"].add(type(value).__name__)

    for entry in schema.values():
        entry["percentage"] = round(entry["count"] / total * 100, 1) if total else 0.0

    return dict(sorted(schema.items(), key=lambda kv: kv[1]["count"], reverse=True))


def audit_key(items: list, key_name: str, id_field: str):
    """Returns (missing_list, present_indices). missing_list = [(index, identifier), ...]."""
    missing = []
    present_indices = set()

    for i, item in enumerate(items):
        if not isinstance(item, dict):
            missing.append((i, f"<non-dict item, type={type(item).__name__}>"))
            continue
        if key_name in item:
            present_indices.add(i)
        else:
            identifier = item.get(id_field, f"<no {id_field}, index {i}>")
            missing.append((i, str(identifier)))

    return missing, present_indices


def recursive_key_count(items: list, key_name: str, nested_list_key: str):
    """
    Counts occurrences of key_name at the top level AND inside each item's
    nested_list_key list (one level deep). Used to reconcile against a raw
    text-search count over the whole file.
    """
    top_count = sum(1 for it in items if isinstance(it, dict) and key_name in it)

    nested_total = 0
    nested_with_key = 0

    for it in items:
        nested_list = it.get(nested_list_key)
        if not isinstance(nested_list, list):
            continue
        for sub in nested_list:
            if not isinstance(sub, dict):
                continue
            nested_total += 1
            if key_name in sub:
                nested_with_key += 1

    return {
        "top_count": top_count,
        "nested_total": nested_total,
        "nested_with_key": nested_with_key,
        "grand_total": top_count + nested_with_key,
    }


def find_nested_anomalies(items: list, nested_list_key: str, target_key: str, second_key: str):
    """Flags nested (Mod_Legs-style) entries that unexpectedly DO carry target_key/second_key."""
    hits = []
    for i, it in enumerate(items):
        nested_list = it.get(nested_list_key)
        if not isinstance(nested_list, list):
            continue
        for j, sub in enumerate(nested_list):
            if isinstance(sub, dict) and (target_key in sub or second_key in sub):
                hits.append((i, j, sub.get("Leg_Name", "<no Leg_Name>")))
    return hits


def classify_by_marker(items: list, indices, marker: str):
    with_marker = sum(1 for i in indices if marker in str(items[i].get("Leg_Name", "")))
    without_marker = len(indices) - with_marker
    return with_marker, without_marker


def write_report(
    schema, missing, present_count, total_items, key_name,
    recursive_stats, set_compare, marker_stats, anomalies,
    output_path: Path,
):
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        f.write("=" * 70 + "\nJSON STRUCTURE (SCHEMA)\n" + "=" * 70 + "\n")
        f.write(f"Total top-level items: {total_items}\n\n")
        for key, info in schema.items():
            types_str = ", ".join(sorted(info["types"]))
            f.write(f"- {key}: present in {info['count']}/{total_items} items "
                     f"({info['percentage']}%) | types: {types_str}\n")

        f.write("\n" + "=" * 70 + f"\n\"{key_name}\" KEY AUDIT SUMMARY\n" + "=" * 70 + "\n")
        f.write(f"Items WITH '{key_name}':    {present_count}\n")
        f.write(f"Items MISSING '{key_name}': {len(missing)}\n")
        f.write(f"Total:                      {total_items}\n")

        f.write("\n" + "=" * 70 + f"\nRECURSIVE '{RECURSIVE_COUNT_KEY}' COUNT (reconciles manual text-search count)\n" + "=" * 70 + "\n")
        f.write(f"Top-level occurrences:                       {recursive_stats['top_count']}\n")
        f.write(f"Nested items inside '{NESTED_LIST_KEY}':               {recursive_stats['nested_total']}\n")
        f.write(f"Nested occurrences of '{RECURSIVE_COUNT_KEY}':             {recursive_stats['nested_with_key']}\n")
        f.write(f"GRAND TOTAL (top + nested):                  {recursive_stats['grand_total']}\n")

        f.write("\n" + "=" * 70 + f"\nSET COMPARISON: missing '{key_name}' vs missing '{SECOND_KEY}'\n" + "=" * 70 + "\n")
        f.write(f"Identical sets: {set_compare['identical']}\n")
        f.write(f"In '{key_name}'-missing only:    {set_compare['only_a']}\n")
        f.write(f"In '{SECOND_KEY}'-missing only:  {set_compare['only_b']}\n")

        f.write("\n" + "=" * 70 + f"\nMARKER CLASSIFICATION ('{SPLIT_MARKER}' in Leg_Name)\n" + "=" * 70 + "\n")
        f.write(f"Missing-{key_name} items WITH marker:    {marker_stats['missing_with']}\n")
        f.write(f"Missing-{key_name} items WITHOUT marker: {marker_stats['missing_without']}\n")
        f.write(f"Present-{key_name} items WITH marker:    {marker_stats['present_with']}\n")
        f.write(f"Present-{key_name} items WITHOUT marker: {marker_stats['present_without']}\n")

        f.write("\n" + "=" * 70 + f"\nSTRUCTURAL ANOMALIES: nested '{NESTED_LIST_KEY}' entries carrying '{key_name}' or '{SECOND_KEY}'\n" + "=" * 70 + "\n")
        if anomalies:
            for parent_idx, sub_idx, name in anomalies:
                f.write(f"- parent index {parent_idx}, {NESTED_LIST_KEY}[{sub_idx}]: {name}\n")
        else:
            f.write("(none found)\n")

        f.write("\n" + "=" * 70 + f"\nITEMS MISSING '{key_name}' (index, identifier) -- full list\n" + "=" * 70 + "\n")
        for idx, identifier in missing:
            f.write(f"[{idx}] {identifier}\n")

    logging.getLogger("status_audit").info(f"Report written to: {output_path}")


def insert_empty_key(items: list, missing_indices: set, key_name: str) -> list:
    result = []
    for i, item in enumerate(items):
        if isinstance(item, dict) and i in missing_indices:
            item = dict(item)
            item[key_name] = ""
        result.append(item)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit a key's presence across a JSON array of records.")
    parser.add_argument("--input", type=Path, default=INPUT_JSON)
    parser.add_argument("--key", type=str, default="Status")
    parser.add_argument("--id-field", type=str, default="Leg_Name")
    parser.add_argument("--insert-status", action="store_true")
    args = parser.parse_args()

    logger = setup_logging()

    try:
        items = load_json(args.input, logger)
        schema = build_schema(items)

        logger.info("")
        logger.info("--- Schema (key: count/total (%) | types) ---")
        for key, info in schema.items():
            types_str = ", ".join(sorted(info["types"]))
            logger.info(f"- {key}: {info['count']}/{len(items)} ({info['percentage']}%) | {types_str}")

        missing, present_indices = audit_key(items, args.key, args.id_field)
        present_count = len(present_indices)

        logger.info("")
        logger.info(f"'{args.key}' present in {present_count} items, missing in {len(missing)} items "
                    f"(total {len(items)})")

        # Recursive Leg_Name reconciliation
        recursive_stats = recursive_key_count(items, RECURSIVE_COUNT_KEY, NESTED_LIST_KEY)
        logger.info("")
        logger.info(f"Recursive '{RECURSIVE_COUNT_KEY}' count -- top: {recursive_stats['top_count']}, "
                    f"nested: {recursive_stats['nested_with_key']}, "
                    f"grand total: {recursive_stats['grand_total']}")

        # Set comparison Status vs DetailedName
        _, second_present_indices = audit_key(items, SECOND_KEY, args.id_field)
        missing_a = {i for i, _ in missing}
        missing_b = set(range(len(items))) - second_present_indices
        set_compare = {
            "identical": missing_a == missing_b,
            "only_a": len(missing_a - missing_b),
            "only_b": len(missing_b - missing_a),
        }
        logger.info(f"Missing-'{args.key}' vs missing-'{SECOND_KEY}' identical sets: {set_compare['identical']}")

        # Marker classification
        mw, mwo = classify_by_marker(items, missing_a, SPLIT_MARKER)
        pw, pwo = classify_by_marker(items, present_indices, SPLIT_MARKER)
        marker_stats = {"missing_with": mw, "missing_without": mwo, "present_with": pw, "present_without": pwo}
        logger.info(f"Missing items with '{SPLIT_MARKER}': {mw}, without: {mwo}")

        # Structural anomalies
        anomalies = find_nested_anomalies(items, NESTED_LIST_KEY, args.key, SECOND_KEY)
        if anomalies:
            logger.warning(f"{len(anomalies)} nested {NESTED_LIST_KEY} entries unexpectedly carry '{args.key}' or '{SECOND_KEY}' -- see report.")

        report_path = OUTPUTS_DIR / f"structure_report_{TIMESTAMP}.txt"
        write_report(schema, missing, present_count, len(items), args.key,
                     recursive_stats, set_compare, marker_stats, anomalies, report_path)

        if args.insert_status:
            missing_indices = missing_a
            updated_items = insert_empty_key(items, missing_indices, args.key)
            out_json_path = OUTPUTS_DIR / f"{args.input.stem}_with_{args.key}{args.input.suffix}"
            with out_json_path.open("w", encoding="utf-8") as f:
                json.dump(updated_items, f, ensure_ascii=False, indent=2)
            logger.info(f"Isolated copy with inserted '{args.key}' written to: {out_json_path}")
            logger.info("Original input file was NOT modified.")

    except Exception:
        logger.exception("Audit failed")
        raise


if __name__ == "__main__":
    main()
