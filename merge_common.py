"""
merge_common.py — shared logic for merging volunteer-entered data back
into the master laws JSON.

Both merge scripts need to find the ORIGINAL record inside the big
master file that corresponds to a row pulled from Google Sheets. The
Phase-3 export files never attached a stable master-file id to each
record (there wasn't one to attach), so matching has to happen on
content: (Leg_Name, Leg_Number, Year) is treated as the identifying
key. This is verified — not assumed — unique against the actual master
file at merge time; if a key matches zero or more-than-one records,
that record is skipped and logged rather than guessed at.
"""

import logging


def walk_law_records(node, path="root"):
    """Yield (path, record) for every dict anywhere in the JSON
    structure that has a "Leg_Name" key — the same definition used
    throughout this project, regardless of nesting depth."""
    if isinstance(node, dict):
        if "Leg_Name" in node:
            yield path, node
        for k, v in node.items():
            yield from walk_law_records(v, f"{path}.{k}")
    elif isinstance(node, list):
        for i, item in enumerate(node):
            yield from walk_law_records(item, f"{path}[{i}]")


def identity_key(record: dict) -> tuple:
    return (
        str(record.get("Leg_Name", "")).strip(),
        str(record.get("Leg_Number", "")).strip(),
        str(record.get("Year", "")).strip(),
    )


def find_in_master(master_data, sheet_row: dict, log_context: str = ""):
    """Find the single master-file record matching sheet_row's
    (Leg_Name, Leg_Number, Year). Returns the record dict on a unique
    match, or None if the match is missing or ambiguous (logged either
    way — never guesses)."""
    target_key = identity_key(sheet_row)
    matches = [rec for _, rec in walk_law_records(master_data) if identity_key(rec) == target_key]

    if len(matches) == 1:
        return matches[0]

    if len(matches) == 0:
        logging.warning(
            "NOT FOUND in master file %s | key=%s | record_id=%s",
            log_context, target_key, sheet_row.get("record_id"),
        )
    else:
        logging.warning(
            "AMBIGUOUS: %s records in master file share key %s %s | record_id=%s — skipped, resolve manually",
            len(matches), target_key, log_context, sheet_row.get("record_id"),
        )
    return None
