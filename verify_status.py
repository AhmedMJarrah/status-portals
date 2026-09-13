import ijson
from pathlib import Path
from collections import defaultdict


# ============================================================
# Configuration
# ============================================================

INPUT_FILE = Path("RefLaws_merged_20260907_132256.json")
REPORT_FILE = Path("law_status_verification.txt")


# ============================================================
# Helpers
# ============================================================

def format_path(prefix: str) -> str:
    """
    Convert ijson prefixes into a more readable JSON path.

    Example:
        item.Mod_Legs.item
    becomes:
        ROOT.[item].Mod_Legs.[item]
    """
    if not prefix:
        return "ROOT"

    parts = prefix.split(".")
    formatted = []

    for part in parts:
        if part == "item":
            formatted.append("[item]")
        else:
            formatted.append(part)

    return ".".join(formatted)


# ============================================================
# Main verification
# ============================================================

def verify_file():

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"File not found:\n{INPUT_FILE.resolve()}"
        )

    print("=" * 70)
    print("Starting JSON verification...")
    print("=" * 70)
    print(f"Input file : {INPUT_FILE}")
    print(f"Report     : {REPORT_FILE}")
    print()

    # --------------------------------------------------------
    # Counters
    # --------------------------------------------------------

    total_law_records = 0
    status_exists = 0
    status_missing = 0

    top_level_objects = 0

    # Status keys that appear in objects WITHOUT Leg_Name
    status_outside_law_records = 0

    # Keep missing Status records for the final report
    missing_records = []

    # --------------------------------------------------------
    # Structure information
    #
    # prefix -> set(event types)
    # --------------------------------------------------------

    structure = defaultdict(set)

    # --------------------------------------------------------
    # Stack of currently open JSON objects
    #
    # Every dictionary represents one JSON object.
    # --------------------------------------------------------

    object_stack = []

    # --------------------------------------------------------
    # Read JSON using streaming parser
    # --------------------------------------------------------

    with INPUT_FILE.open(
        "rb"
    ) as f:

        parser = ijson.parse(f)

        for prefix, event, value in parser:

            # ==================================================
            # Collect structure information
            # ==================================================

            readable_prefix = format_path(prefix)

            structure[readable_prefix].add(event)

            # ==================================================
            # START OBJECT
            # ==================================================

            if event == "start_map":

                # Root-level law object:
                #
                # [
                #   { ... },
                #   { ... }
                # ]
                #
                if prefix == "item":
                    top_level_objects += 1

                object_stack.append({
                    "prefix": prefix,
                    "has_leg_name": False,
                    "has_status": False,
                    "leg_name": None,
                    "leg_number": None,
                    "year": None,
                    "current_key": None,
                })

            # ==================================================
            # OBJECT KEY
            # ==================================================

            elif event == "map_key":

                if object_stack:
                    current_object = object_stack[-1]

                    current_object["current_key"] = value

                    # Important:
                    # We check key existence immediately.
                    # Therefore Status="" or Status=null
                    # still counts as "Status exists".

                    if value == "Leg_Name":
                        current_object["has_leg_name"] = True

                    elif value == "Status":
                        current_object["has_status"] = True

            # ==================================================
            # VALUE
            # ==================================================

            elif event in (
                "string",
                "number",
                "boolean",
                "null",
            ):

                if object_stack:

                    current_object = object_stack[-1]
                    key = current_object["current_key"]

                    # Capture useful identification information
                    # for missing Status records.

                    if key == "Leg_Name":
                        current_object["leg_name"] = value

                    elif key == "Leg_Number":
                        current_object["leg_number"] = value

                    elif key == "Year":
                        current_object["year"] = value

            # ==================================================
            # END OBJECT
            # ==================================================

            elif event == "end_map":

                current_object = object_stack.pop()

                # ------------------------------------------------
                # Is this object a Law Record?
                #
                # Our definition:
                # An object containing Leg_Name.
                # ------------------------------------------------

                if current_object["has_leg_name"]:

                    total_law_records += 1

                    if current_object["has_status"]:

                        status_exists += 1

                    else:

                        status_missing += 1

                        missing_records.append({
                            "number": total_law_records,
                            "path": format_path(
                                current_object["prefix"]
                            ),
                            "Leg_Name": current_object["leg_name"],
                            "Leg_Number": current_object["leg_number"],
                            "Year": current_object["year"],
                        })

                # ------------------------------------------------
                # Status exists in an object that is NOT a
                # Law Record.
                # ------------------------------------------------

                elif current_object["has_status"]:

                    status_outside_law_records += 1

    # ============================================================
    # Verification
    # ============================================================

    expected_total = 4315
    expected_status = 1554
    expected_missing = 2761

    verification_ok = (
        total_law_records == expected_total
        and status_exists == expected_status
        and status_missing == expected_missing
        and status_outside_law_records == 0
    )

    # ============================================================
    # Write report
    # ============================================================

    with REPORT_FILE.open(
        "w",
        encoding="utf-8"
    ) as report:

        report.write("=" * 80 + "\n")
        report.write("JSON LAW STATUS VERIFICATION REPORT\n")
        report.write("=" * 80 + "\n\n")

        report.write(f"Input file:\n{INPUT_FILE}\n\n")

        # --------------------------------------------------------
        # Main results
        # --------------------------------------------------------

        report.write("-" * 80 + "\n")
        report.write("1. MAIN COUNTS\n")
        report.write("-" * 80 + "\n\n")

        report.write(
            f"Top-level objects                 : {top_level_objects:,}\n"
        )

        report.write(
            f"Total Law Records (Leg_Name)      : "
            f"{total_law_records:,}\n"
        )

        report.write(
            f"Law Records with Status           : "
            f"{status_exists:,}\n"
        )

        report.write(
            f"Law Records WITHOUT Status        : "
            f"{status_missing:,}\n"
        )

        report.write(
            f"Status outside Law Records        : "
            f"{status_outside_law_records:,}\n"
        )

        report.write("\n")

        # --------------------------------------------------------
        # Expected values
        # --------------------------------------------------------

        report.write("-" * 80 + "\n")
        report.write("2. EXPECTED VALUES\n")
        report.write("-" * 80 + "\n\n")

        report.write(
            f"Expected Law Records              : "
            f"{expected_total:,}\n"
        )

        report.write(
            f"Expected Status exists            : "
            f"{expected_status:,}\n"
        )

        report.write(
            f"Expected Status missing           : "
            f"{expected_missing:,}\n"
        )

        report.write("\n")

        # --------------------------------------------------------
        # Verification result
        # --------------------------------------------------------

        report.write("-" * 80 + "\n")
        report.write("3. VERIFICATION RESULT\n")
        report.write("-" * 80 + "\n\n")

        if verification_ok:

            report.write(
                "RESULT: PASS\n\n"
            )

            report.write(
                "The numbers match the expected values exactly.\n"
            )

            report.write(
                "All Status keys belong to Law Records containing "
                "Leg_Name.\n"
            )

        else:

            report.write(
                "RESULT: FAIL\n\n"
            )

            report.write(
                "The actual structure/counts do NOT match all "
                "expected values.\n"
            )

        report.write("\n")

        # --------------------------------------------------------
        # Mathematical check
        # --------------------------------------------------------

        report.write("-" * 80 + "\n")
        report.write("4. MATHEMATICAL CHECK\n")
        report.write("-" * 80 + "\n\n")

        report.write(
            f"{status_exists:,} + {status_missing:,} = "
            f"{status_exists + status_missing:,}\n"
        )

        report.write(
            f"Total Law Records = {total_law_records:,}\n"
        )

        if status_exists + status_missing == total_law_records:
            report.write(
                "CHECK: PASS\n"
            )
        else:
            report.write(
                "CHECK: FAIL\n"
            )

        report.write("\n")

        # --------------------------------------------------------
        # Structure
        # --------------------------------------------------------

        report.write("-" * 80 + "\n")
        report.write("5. JSON STRUCTURE / PATHS\n")
        report.write("-" * 80 + "\n\n")

        # Sort by path depth first
        sorted_structure = sorted(
            structure.items(),
            key=lambda x: (
                x[0].count("."),
                x[0]
            )
        )

        for path, events in sorted_structure:

            event_text = ", ".join(
                sorted(events)
            )

            report.write(
                f"{path}\n"
                f"    Events: {event_text}\n"
            )

        report.write("\n")

        # --------------------------------------------------------
        # Missing Status records
        # --------------------------------------------------------

        report.write("-" * 80 + "\n")
        report.write("6. LAW RECORDS MISSING STATUS\n")
        report.write("-" * 80 + "\n\n")

        report.write(
            f"Total missing Status records: "
            f"{len(missing_records):,}\n\n"
        )

        for record in missing_records:

            report.write(
                f"Law Record #{record['number']:,}\n"
            )

            report.write(
                f"JSON Path    : {record['path']}\n"
            )

            report.write(
                f"Leg_Name     : {record['Leg_Name']}\n"
            )

            report.write(
                f"Leg_Number   : {record['Leg_Number']}\n"
            )

            report.write(
                f"Year         : {record['Year']}\n"
            )

            report.write(
                "Status       : MISSING\n"
            )

            report.write("\n")

    # ============================================================
    # Console output
    # ============================================================

    print("=" * 70)
    print("VERIFICATION FINISHED")
    print("=" * 70)

    print(
        f"Top-level objects       : {top_level_objects:,}"
    )

    print(
        f"Total Law Records       : {total_law_records:,}"
    )

    print(
        f"Status exists           : {status_exists:,}"
    )

    print(
        f"Status missing          : {status_missing:,}"
    )

    print(
        f"Status outside records  : "
        f"{status_outside_law_records:,}"
    )

    print()

    if verification_ok:
        print("RESULT: PASS")
    else:
        print("RESULT: FAIL")

    print()
    print(f"Report saved to:")
    print(REPORT_FILE.resolve())


# ============================================================
# Run
# ============================================================

if __name__ == "__main__":
    verify_file()