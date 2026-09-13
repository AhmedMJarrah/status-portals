"""
generate_password_hash.py

Prints a bcrypt hash for a password you type in (input is hidden, not
echoed to the terminal). Paste the result into .env — you need one for
each of: PORTAL1_PASSWORD_HASH, PORTAL2_SHARED_PASSWORD_HASH,
ADMIN_PASSWORD_HASH. Run it once per password (3 times total, or fewer
if you want to reuse one password for more than one of them).

Usage:
    python generate_password_hash.py
"""

import bcrypt
from getpass import getpass

password = getpass("Password to hash: ")
confirm = getpass("Type it again to confirm: ")

if password != confirm:
    raise SystemExit("Passwords didn't match — nothing was generated. Try again.")

hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
print("\nAdd this to .env:")
print(hashed.decode("utf-8"))
