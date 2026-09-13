import ijson

INPUT_FILE = r"C:\Users\user\Desktop\status\RefLaws_merged_20260907_132256.json"

count = 0
first_keys = None
last_keys = None

with open(INPUT_FILE, "rb") as f:
    for obj in ijson.items(f, "item"):
        count += 1

        if first_keys is None:
            first_keys = list(obj.keys())

        last_keys = list(obj.keys())

print("Number of top-level objects:", count)

print("\nFirst object keys:")
print(first_keys)

print("\nLast object keys:")
print(last_keys)