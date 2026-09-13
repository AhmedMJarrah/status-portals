from collections import OrderedDict
from pathlib import Path
import ijson


# ============================================================
# CONFIGURATION
# ============================================================

INPUT_FILE = r"C:\Users\user\Desktop\status\RefLaws_merged_20260907_132256.json"
OUTPUT_FILE = r"C:\Users\user\Desktop\status\json_structure_report.txt"

EXPECTED_STATUS_EXISTS = 1554
EXPECTED_STATUS_MISSING = 2761


# ============================================================
# HELPERS
# ============================================================

def get_type(value):
    """Return a readable JSON-like type name."""
    if isinstance(value, dict):
        return "object"
    elif isinstance(value, list):
        return "array"
    elif isinstance(value, str):
        return "string"
    elif isinstance(value, bool):
        return "boolean"
    elif isinstance(value, int):
        return "integer"
    elif isinstance(value, float):
        return "number"
    elif value is None:
        return "null"
    else:
        return type(value).__name__


def create_node():
    """
    Creates one node in the structure tree.

    types:
        Data types observed for this field.

    children:
        Nested dictionary keys.

    array_item:
        Structure observed inside array elements.
    """
    return {
        "types": set(),
        "children": OrderedDict(),
        "array_item": None,
    }


def analyze_value(value, node):
    """
    Recursively analyze a JSON value without storing its actual content.
    """

    value_type = get_type(value)
    node["types"].add(value_type)

    # --------------------------------------------------------
    # Dictionary / JSON object
    # --------------------------------------------------------
    if isinstance(value, dict):

        for key, child_value in value.items():

            if key not in node["children"]:
                node["children"][key] = create_node()

            analyze_value(
                child_value,
                node["children"][key]
            )

    # --------------------------------------------------------
    # List / JSON array
    # --------------------------------------------------------
    elif isinstance(value, list):

        if node["array_item"] is None:
            node["array_item"] = create_node()

        # Analyze ALL elements because different elements
        # may contain different keys.
        for item in value:
            analyze_value(
                item,
                node["array_item"]
            )


def format_types(types):
    """Format discovered data types."""
    if not types:
        return "unknown"

    return " | ".join(sorted(types))


def write_structure(node, output, indent="", name="ROOT"):
    """
    Recursively write the structure tree.
    """

    output.write(
        f"{indent}{name} [{format_types(node['types'])}]\n"
    )

    # Nested dictionary fields
    for key, child in node["children"].items():
        write_structure(
            child,
            output,
            indent + "    ",
            key
        )

    # Array elements
    if node["array_item"] is not None:
        array_item = node["array_item"]

        output.write(
            f"{indent}    └── ARRAY ITEMS "
            f"[{format_types(array_item['types'])}]\n"
        )

        for key, child in array_item["children"].items():
            write_structure(
                child,
                output,
                indent + "        ",
                key
            )

        # Handle arrays inside arrays
        if array_item["array_item"] is not None:
            write_structure(
                array_item["array_item"],
                output,
                indent + "        ",
                "NESTED ARRAY ITEMS"
            )


# ============================================================
# MAIN
# ============================================================

def main():

    input_path = Path(INPUT_FILE)
    output_path = Path(OUTPUT_FILE)

    if not input_path.exists():
        print(f"ERROR: File not found: {input_path}")
        return

    # Structure of one top-level array item
    structure = create_node()
    structure["types"].add("object")

    total_items = 0

    status_exists = 0
    status_missing = 0

    missing_status_records = []

    print("Analyzing JSON...")
    print("This uses streaming, so the whole JSON is not loaded into RAM.")

    # ========================================================
    # STREAM TOP-LEVEL ARRAY
    # ========================================================

    with open(input_path, "rb") as f:

        # Since your JSON looks like:
        #
        # [
        #     {...},
        #     {...},
        #     ...
        # ]
        #
        # "item" means each object inside the root array.
        for index, obj in enumerate(ijson.items(f, "item"), start=1):

            total_items += 1

            # ------------------------------------------------
            # Analyze complete nested structure
            # ------------------------------------------------

            analyze_value(obj, structure)

            # ------------------------------------------------
            # Check Status ONLY at top-level law object
            # ------------------------------------------------

            if "Status" in obj:
                status_exists += 1

            else:
                status_missing += 1

                # Keep only useful identifiers.
                # We are NOT copying full sensitive records.
                missing_status_records.append({
                    "index": index,
                    "Leg_Name": obj.get("Leg_Name", ""),
                    "Leg_Number": obj.get("Leg_Number", ""),
                    "Year": obj.get("Year", ""),
                })

            # ------------------------------------------------
            # Progress
            # ------------------------------------------------

            if total_items % 500 == 0:
                print(
                    f"Processed {total_items:,} top-level objects..."
                )

    # ========================================================
    # CALCULATIONS
    # ========================================================

    if total_items > 0:
        exists_percentage = status_exists / total_items * 100
        missing_percentage = status_missing / total_items * 100
    else:
        exists_percentage = 0
        missing_percentage = 0

    expected_total = (
        EXPECTED_STATUS_EXISTS +
        EXPECTED_STATUS_MISSING
    )

    counts_match = (
        status_exists == EXPECTED_STATUS_EXISTS
        and
        status_missing == EXPECTED_STATUS_MISSING
    )

    # ========================================================
    # WRITE REPORT
    # ========================================================

    with open(
        output_path,
        "w",
        encoding="utf-8"
    ) as output:

        output.write(
            "=" * 80 +
            "\nJSON STRUCTURE REPORT\n" +
            "=" * 80 +
            "\n\n"
        )

        output.write(
            f"Input file: {input_path.name}\n"
        )

        output.write(
            f"Total top-level objects: {total_items:,}\n\n"
        )

        # ----------------------------------------------------
        # STRUCTURE
        # ----------------------------------------------------

        output.write(
            "=" * 80 +
            "\nCOMPLETE JSON STRUCTURE\n" +
            "=" * 80 +
            "\n\n"
        )

        output.write("ROOT [array]\n")
        output.write("    └── ARRAY ITEMS [object]\n")

        for key, child in structure["children"].items():
            write_structure(
                child,
                output,
                indent="        ",
                name=key
            )

        # ----------------------------------------------------
        # STATUS ANALYSIS
        # ----------------------------------------------------

        output.write(
            "\n\n" +
            "=" * 80 +
            "\nSTATUS FIELD ANALYSIS\n" +
            "=" * 80 +
            "\n\n"
        )

        output.write(
            f"Total top-level objects checked : {total_items:,}\n"
        )

        output.write(
            f"Status exists                   : {status_exists:,}\n"
        )

        output.write(
            f"Status missing                  : {status_missing:,}\n\n"
        )

        output.write(
            f"Status present percentage       : "
            f"{exists_percentage:.2f}%\n"
        )

        output.write(
            f"Status missing percentage       : "
            f"{missing_percentage:.2f}%\n\n"
        )

        # ----------------------------------------------------
        # EXPECTED VALUES
        # ----------------------------------------------------

        output.write(
            "-" * 80 +
            "\nEXPECTED COUNTS\n" +
            "-" * 80 +
            "\n\n"
        )

        output.write(
            f"Expected Status exists : "
            f"{EXPECTED_STATUS_EXISTS:,}\n"
        )

        output.write(
            f"Expected Status missing: "
            f"{EXPECTED_STATUS_MISSING:,}\n"
        )

        output.write(
            f"Expected total         : "
            f"{expected_total:,}\n\n"
        )

        if counts_match:

            output.write(
                "VERIFICATION: PASS\n"
                "The Status counts exactly match "
                "the expected values.\n"
            )

        else:

            output.write(
                "VERIFICATION: FAILED\n"
                "The discovered Status counts DO NOT "
                "match the expected values.\n\n"
            )

            output.write(
                f"Difference in existing Status: "
                f"{status_exists - EXPECTED_STATUS_EXISTS:+,}\n"
            )

            output.write(
                f"Difference in missing Status : "
                f"{status_missing - EXPECTED_STATUS_MISSING:+,}\n"
            )

        # ----------------------------------------------------
        # MISSING STATUS RECORDS
        # ----------------------------------------------------

        output.write(
            "\n\n" +
            "=" * 80 +
            "\nOBJECTS MISSING STATUS\n" +
            "=" * 80 +
            "\n\n"
        )

        output.write(
            "The following top-level law objects do not "
            "contain the 'Status' key.\n\n"
        )

        for record in missing_status_records:

            output.write(
                f"Index      : {record['index']}\n"
            )

            output.write(
                f"Leg_Name   : {record['Leg_Name']}\n"
            )

            output.write(
                f"Leg_Number : {record['Leg_Number']}\n"
            )

            output.write(
                f"Year       : {record['Year']}\n"
            )

            output.write("-" * 80 + "\n")

    # ========================================================
    # TERMINAL RESULT
    # ========================================================

    print()
    print("=" * 60)
    print("ANALYSIS COMPLETE")
    print("=" * 60)

    print(f"Total objects : {total_items:,}")
    print(f"Status exists : {status_exists:,}")
    print(f"Status missing: {status_missing:,}")

    if counts_match:
        print(
            "VERIFICATION: PASS - counts match "
            "1554 existing / 2761 missing."
        )
    else:
        print(
            "VERIFICATION: FAILED - investigate before "
            "modifying the JSON."
        )

    print()
    print(f"Report saved to: {output_path.resolve()}")


if __name__ == "__main__":
    main()