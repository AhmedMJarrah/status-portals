import re
from pathlib import Path

INPUT_FILE = r"C:\Users\user\Desktop\status\RefLaws_merged_20260907_132256.json"

text = Path(INPUT_FILE).read_text(encoding="utf-8")

print("=" * 60)
print("JSON STRUCTURE DIAGNOSTIC")
print("=" * 60)

# ------------------------------------------------------------
# 1. Count Leg_Name occurrences
# ------------------------------------------------------------

leg_name_count = len(
    re.findall(r'"Leg_Name"\s*:', text)
)

print(f'"Leg_Name" occurrences : {leg_name_count:,}')


# ------------------------------------------------------------
# 2. Count Status occurrences
# ------------------------------------------------------------

status_count = len(
    re.findall(r'"Status"\s*:', text)
)

print(f'"Status" occurrences   : {status_count:,}')


# ------------------------------------------------------------
# 3. Count opening arrays
# ------------------------------------------------------------

array_count = text.count("[")

print(f'Opening "[" characters : {array_count:,}')


# ------------------------------------------------------------
# 4. Count closing arrays
# ------------------------------------------------------------

array_end_count = text.count("]")

print(f'Closing "]" characters : {array_end_count:,}')


# ------------------------------------------------------------
# 5. Count objects
# ------------------------------------------------------------

object_start_count = text.count("{")
object_end_count = text.count("}")

print(f'Opening "{{" characters : {object_start_count:,}')
print(f'Closing "}}" characters : {object_end_count:,}')


# ------------------------------------------------------------
# 6. First non-whitespace character
# ------------------------------------------------------------

first_char = text.lstrip()[0]

print(f"\nFirst JSON character: {repr(first_char)}")


# ------------------------------------------------------------
# 7. Last non-whitespace character
# ------------------------------------------------------------

last_char = text.rstrip()[-1]

print(f"Last JSON character : {repr(last_char)}")


# ------------------------------------------------------------
# 8. File size
# ------------------------------------------------------------

size_mb = Path(INPUT_FILE).stat().st_size / (1024 * 1024)

print(f"\nFile size: {size_mb:,.2f} MB")


print("\n" + "=" * 60)
print("DIAGNOSTIC COMPLETE")
print("=" * 60)