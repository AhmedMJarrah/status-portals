"""
config.py — centralized configuration for the volunteer portals project
(Phase 4 of the Status project).

Covers both portals:
    Portal 1: zero-article laws        (1 volunteer)
    Portal 2: empty-Status laws        (5 volunteers)

No secrets live here — only structure/naming/schema. Actual credentials
come from environment variables via .env (see .env.example, given in
chat — not generated as a file here).
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ------------------------------------------------------------------
# Paths
# ------------------------------------------------------------------

PROJECT_ROOT = Path(r"C:\Users\user\Desktop\status")
DATA_DIR = PROJECT_ROOT / "outputs"
LOG_DIR = PROJECT_ROOT / "logs"

# Phase-3 export files (source of truth for the initial Sheets population)
ZERO_ARTICLES_SOURCE = DATA_DIR / "laws_zero_articles_20260909_115646.json"
EMPTY_STATUS_SOURCE = DATA_DIR / "laws_empty_status_20260909_115646.json"

# ------------------------------------------------------------------
# Google Sheets — service account
# ------------------------------------------------------------------

GOOGLE_SERVICE_ACCOUNT_FILE = os.environ["GOOGLE_SERVICE_ACCOUNT_FILE"]

# ------------------------------------------------------------------
# Portal 1 — zero-article laws (1 volunteer)
# ------------------------------------------------------------------

SPREADSHEET_ID_PORTAL1 = os.environ["SPREADSHEET_ID_PORTAL1"]  # from the sheet's URL
SPREADSHEET_NAME_PORTAL1 = "status_portal_zero_articles"  # label only, for logs/errors

PORTAL1_ARTICLES_TAB = "articles"      # one row per article the volunteer adds
PORTAL1_PROGRESS_TAB = "progress"      # one row per law (13 rows), completion flag

PORTAL1_ARTICLES_COLUMNS = [
    "record_id", "Leg_Name", "Leg_Number", "Year",
    "article_number", "article_text", "entered_by", "entered_at",
]
PORTAL1_PROGRESS_COLUMNS = [
    "record_id", "Leg_Name", "Leg_Number", "Year",
    "completed", "completed_by", "completed_at",
]

PORTAL1_PASSWORD_HASH = os.environ["PORTAL1_PASSWORD_HASH"]  # bcrypt hash — see .env.example

# ------------------------------------------------------------------
# Portal 2 — empty-Status laws (5 volunteers)
# ------------------------------------------------------------------

SPREADSHEET_ID_PORTAL2 = os.environ["SPREADSHEET_ID_PORTAL2"]  # from the sheet's URL
SPREADSHEET_NAME_PORTAL2 = "status_portal_empty_status"  # label only, for logs/errors

# One Sheet tab per volunteer = fully isolated data, no shared rows.
PORTAL2_VOLUNTEER_USERNAMES = ["v1", "v2", "v3", "v4", "v5"]
PORTAL2_SHARED_PASSWORD_HASH = os.environ["PORTAL2_SHARED_PASSWORD_HASH"]  # bcrypt hash

# Fields that are never shown as editable in the volunteer form (either
# they're the fixed identity of the record, or they're structural/list
# fields outside the scope of this data-entry task). Every OTHER key
# found in the source records becomes a Sheet column, and is rendered
# as an editable input in the app only when its value is empty for that
# specific record — this directly implements "every empty key, not just
# Status/URL" without hard-coding the exact field list.
PORTAL2_EXCLUDED_FROM_EDITING = {"Leg_Name", "Base_Articles", "Mod_Legs", "Reflected_Articles"}

# Fields that should not even become SHEET COLUMNS in the first place —
# structural list fields with no simple display value. Leg_Name is
# deliberately NOT here: it must be a real column (context + the
# merge-back matching key), just never an editable one (see above).
PORTAL2_EXCLUDED_FROM_SHEET = {"Base_Articles", "Mod_Legs", "Reflected_Articles"}

# ------------------------------------------------------------------
# Admin (shared by both admin apps, separate credential from volunteers)
# ------------------------------------------------------------------

ADMIN_PASSWORD_HASH = os.environ["ADMIN_PASSWORD_HASH"]  # bcrypt hash
