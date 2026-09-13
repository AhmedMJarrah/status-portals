import ijson

INPUT_FILE = r"C:\Users\user\Desktop\status\RefLaws_merged_20260907_132256.json"

status_values = {}

with open(INPUT_FILE, "rb") as f:
    for index, obj in enumerate(ijson.items(f, "item"), start=1):

        if "Status" in obj:
            value = obj["Status"]

            status_values[value] = status_values.get(value, 0) + 1

print("\nStatus values:")
print("=" * 50)

for value, count in sorted(
    status_values.items(),
    key=lambda x: x[1],
    reverse=True
):
    print(f"{repr(value)} : {count}")

print("\nTotal with Status:", sum(status_values.values()))