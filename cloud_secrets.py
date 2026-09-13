"""
cloud_secrets.py — bridges Streamlit Community Cloud's secrets
(st.secrets) into the same environment variables config.py already
reads from .env locally. config.py itself never changes — it always
just reads os.environ, whether that got populated by python-dotenv
(local) or by this bootstrap (cloud).

Call bootstrap() at the very top of each Streamlit app file, BEFORE
importing config (config.py reads os.environ at import time). CLI
scripts (push_initial_data_to_sheets.py, the merge scripts,
generate_password_hash.py, etc.) never call this — they only ever run
locally, using .env directly.

Locally, st.secrets is empty (no .streamlit/secrets.toml file), so
bootstrap() does nothing and .env keeps working exactly as before.
"""

import json
import os
import tempfile

import streamlit as st

_SIMPLE_KEYS = (
    "SPREADSHEET_ID_PORTAL1", "SPREADSHEET_ID_PORTAL2",
    "PORTAL1_PASSWORD_HASH", "PORTAL2_SHARED_PASSWORD_HASH", "ADMIN_PASSWORD_HASH",
)


def bootstrap() -> None:
    try:
        secrets = st.secrets
        if len(secrets) == 0:
            return  # no secrets.toml / no cloud secrets configured — running locally
    except Exception:
        return  # accessing st.secrets with nothing configured — running locally

    for key in _SIMPLE_KEYS:
        if key in secrets:
            os.environ[key] = secrets[key]

    if "GOOGLE_SERVICE_ACCOUNT_FILE_CONTENT" in secrets:
        key_json = secrets["GOOGLE_SERVICE_ACCOUNT_FILE_CONTENT"]
        # Fail loudly here if it's not valid JSON, rather than a
        # confusing gspread error later.
        json.loads(key_json)
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8")
        tmp.write(key_json)
        tmp.close()
        os.environ["GOOGLE_SERVICE_ACCOUNT_FILE"] = tmp.name
