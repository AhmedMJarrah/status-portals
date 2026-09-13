"""
portal2_volunteer_app.py

Volunteer interface for Portal 2: 5 volunteers each fill in the empty
fields (Status + URL + anything else still blank) for their assigned
share of the 257 records. Each volunteer's data lives in its own
isolated Sheet tab. Status is a required choice between "ساري" /
"غير ساري" — never free text. Every save writes straight to Google
Sheets.

Run:
    streamlit run portal2_volunteer_app.py
"""

import streamlit as st
from cloud_secrets import bootstrap
bootstrap()

import bcrypt

from config import PORTAL2_VOLUNTEER_USERNAMES, PORTAL2_SHARED_PASSWORD_HASH
import portal2_data as data
from gsheets_client import is_true
from ui_theme import inject_css, inject_login_layout, hero, logout_button

st.set_page_config(page_title="بوابة تعبئة البيانات", page_icon="✨", layout="wide")
inject_css()

STATUS_FIELD = "Status"
STATUS_PLACEHOLDER = "اختر..."
STATUS_OPTIONS = [STATUS_PLACEHOLDER, "ساري", "غير ساري"]

# Fields shown as read-only context (never asked for — Leg_Name is
# already the dropdown's own selected value/heading). Everything else
# that's non-empty becomes its own context card.
CONTEXT_EXCLUDED = {"Leg_Name"}

FIELD_LABELS = {
    "Status": "الحالة", "URL": "الرابط", "Magazine_Date": "تاريخ الجريدة",
    "Magazine_Number": "رقم الجريدة", "Magazine_Page": "رقم الصفحة",
    "Publication": "بيان النشر",
    # ASSUMPTION — best-guess meaning, please correct the wording if the
    # actual direction differs in your schema:
    "Replaced_For": "بديل عن (القانون القديم الذي حلّ هذا القانون محلّه)",
    "Replaced_By": "استُبدل بـ (القانون الجديد الذي حلّ محل هذا القانون لاحقًا)",
    "Canceled_By": "أُلغي بواسطة", "Issue_Date": "تاريخ الإصدار",
    "Active_Date": "تاريخ النفاذ", "End_Date": "تاريخ الانتهاء",
    "Leg_Number": "رقم التشريع", "Article_Count": "عدد المواد",
    "is_amendment": "نوع التشريع", "Year": "السنة",
}

FIELD_ICONS = {
    "Status": "🚦", "URL": "🔗", "Magazine_Date": "🗓️", "Magazine_Number": "📰",
    "Magazine_Page": "📄", "Publication": "📢", "Replaced_For": "🔁", "Replaced_By": "🔀",
    "Canceled_By": "🛑", "Issue_Date": "📅", "Active_Date": "✅", "End_Date": "⏹️",
    "Leg_Number": "🔢", "Article_Count": "📚", "is_amendment": "🏷️", "Year": "📆",
}

# Leg_Number + Year read together naturally ("رقم 31 لسنة 1976"), so
# they're placed side by side; the rest follows a sensible reading
# order instead of whatever order the source JSON happened to have.
FIELD_ORDER = [
    "Leg_Number", "Year", "Status", "Issue_Date", "Active_Date", "End_Date",
    "Magazine_Date", "Magazine_Number", "Magazine_Page", "Publication",
    "Replaced_For", "Replaced_By", "Canceled_By", "Article_Count", "is_amendment", "URL",
]

# The three fields most worth a volunteer's time — shown as a banner
# above the fill-in form.
PRIORITY_FIELDS = ["Status", "Issue_Date", "End_Date"]


def field_label(key: str) -> str:
    return FIELD_LABELS.get(key, key)


def field_icon(key: str) -> str:
    return FIELD_ICONS.get(key, "•")


def sort_by_field_order(keys) -> list:
    return sorted(keys, key=lambda k: FIELD_ORDER.index(k) if k in FIELD_ORDER else len(FIELD_ORDER))


def format_context_value(key: str, value):
    if key == "is_amendment":
        return "تعديل" if str(value).strip().lower() in ("true", "1") else "أساسي"
    return value


AVATAR_ICONS = ["🦋", "🌟", "🌿", "🔥", "🌊"]

# ------------------------------------------------------------------
# Login — pick your slot, tell us your name, then your password
# ------------------------------------------------------------------

if "username" not in st.session_state:
    st.session_state.username = None
if "display_name" not in st.session_state:
    st.session_state.display_name = ""
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    inject_login_layout()
    with st.container(border=True):
        hero("✨", "بوابة تعبئة البيانات", "اختر حسابك وابدأ")

        cols = st.columns(len(PORTAL2_VOLUNTEER_USERNAMES))
        for i, uname in enumerate(PORTAL2_VOLUNTEER_USERNAMES):
            with cols[i]:
                selected = st.session_state.username == uname
                border = "3px solid #2E86AB" if selected else "1px solid #EAEFF4"
                st.markdown(f"""
                <div style='text-align:center; background:#fff; border-radius:16px; padding:1.1rem 0.4rem;
                            box-shadow:0 2px 10px rgba(20,40,70,0.08); border:{border};
                            transition: all 0.2s ease;'>
                    <div style='font-size:2.2rem;'>{AVATAR_ICONS[i % len(AVATAR_ICONS)]}</div>
                    <div style='font-weight:700; color:#142846; margin-top:0.3rem;'>{uname}</div>
                </div>
                """, unsafe_allow_html=True)
                if st.button("اختيار", key=f"pick_{uname}", use_container_width=True):
                    st.session_state.username = uname
                    st.rerun()

        if st.session_state.username:
            saved_name = data.get_saved_name(st.session_state.username)

            if saved_name:
                st.markdown(
                    f"<p style='text-align:center; margin-top:1.2rem; font-size:1.05rem;'>"
                    f"أهلاً {saved_name} 👋 — بس اكتب كلمة المرور</p>",
                    unsafe_allow_html=True,
                )
                pw = st.text_input("كلمة المرور", type="password", label_visibility="collapsed", placeholder="كلمة المرور")
                if st.button("دخول", use_container_width=True, type="primary"):
                    if bcrypt.checkpw(pw.encode("utf-8"), PORTAL2_SHARED_PASSWORD_HASH.encode("utf-8")):
                        st.session_state.authenticated = True
                        st.session_state.display_name = saved_name
                        st.rerun()
                    else:
                        st.error("كلمة المرور غير صحيحة")
            else:
                st.markdown(
                    "<p style='text-align:center; margin-top:1.2rem; font-size:1.05rem;'>"
                    "تمام ✅ — أول مرة بس، شو اسمك؟</p>",
                    unsafe_allow_html=True,
                )
                display_name_input = st.text_input(
                    "اسمك", label_visibility="collapsed", placeholder="اكتب اسمك هون...",
                )
                pw = st.text_input("كلمة المرور", type="password", label_visibility="collapsed", placeholder="كلمة المرور")
                if st.button("دخول", use_container_width=True, type="primary"):
                    if not display_name_input.strip():
                        st.warning("لازم تكتب اسمك قبل الدخول")
                    elif bcrypt.checkpw(pw.encode("utf-8"), PORTAL2_SHARED_PASSWORD_HASH.encode("utf-8")):
                        st.session_state.authenticated = True
                        st.session_state.display_name = display_name_input.strip()
                        data.save_name(st.session_state.username, display_name_input.strip())
                        st.rerun()
                    else:
                        st.error("كلمة المرور غير صحيحة")
    st.stop()

username = st.session_state.username
display_name = st.session_state.display_name

# ------------------------------------------------------------------
# Main app
# ------------------------------------------------------------------

rows = data.get_rows(username)
done, total = data.progress_summary(username)

st.markdown(f"""
<div style='margin-bottom:0.5rem;'>
    <h1 style='color:#142846; margin-bottom:0.2rem;'>✨ أهلاً {display_name}</h1>
    <p style='color:#6B7A90;'>أنجزت {done} من {total} سجل</p>
</div>
""", unsafe_allow_html=True)
logout_button()
st.progress(done / total if total else 0)
st.markdown("<br>", unsafe_allow_html=True)

DROPDOWN_PLACEHOLDER = "— اختر قانون —"
row_by_id = {r.get("record_id"): r for r in rows}

# When two+ records share the exact same Leg_Name, Streamlit's own
# selectbox loses track of which one is selected across reruns (it
# appears to match by rendered text internally) — confirmed directly,
# not a guess. The fix is an invisible zero-width space appended to
# repeats: it disambiguates them for Streamlit's own bookkeeping while
# staying 100% invisible on screen. It's never part of what gets
# copied — the dedicated copy box below always reads the record's real
# Leg_Name straight from the row, untouched.
_seen_name_counts: dict = {}
_dropdown_label_by_id: dict = {}
for _r in rows:
    _base_name = _r.get("Leg_Name", "")
    _n = _seen_name_counts.get(_base_name, 0)
    _seen_name_counts[_base_name] = _n + 1
    _dropdown_label_by_id[_r.get("record_id")] = _base_name + ("\u200b" * _n)


def option_label(record_id) -> str:
    return _dropdown_label_by_id.get(record_id, DROPDOWN_PLACEHOLDER)


# The selectbox's VALUE is the unique record_id (a plain string), not
# the row dict itself, so lookups are always exact regardless of
# duplicate names.
selected_id = st.selectbox(
    "اختر القانون يلي بدك تشتغل عليه",
    options=list(row_by_id.keys()),
    index=0 if rows else None,  # land on the first record immediately, not an empty placeholder
    format_func=option_label,
    label_visibility="collapsed",
    key="law_select",
)
selected_row = row_by_id.get(selected_id)

if selected_row is not None:
    row = selected_row
    rid = row.get("record_id")
    empties = data.empty_fields(row)
    row_is_done = is_true(row.get("completed"))

    st.markdown(
        f"<span class='badge {'badge-done' if row_is_done else 'badge-pending'}'>"
        f"{'مكتمل ✓' if row_is_done else 'قيد الانتظار'}</span>",
        unsafe_allow_html=True,
    )
    st.code(row.get("Leg_Name", ""), language=None)

    st.markdown("<div class='section-title'>📋 بيانات القانون</div>", unsafe_allow_html=True)
    context_keys = [
        k for k, v in row.items()
        if k not in empties and k not in ("record_id", "completed", "entered_by", "entered_at")
        and k not in CONTEXT_EXCLUDED and str(v).strip()
    ]
    context_keys = sort_by_field_order(context_keys)
    if context_keys:
        chips = "".join(
            f"<div class='context-item'><span class='context-label'>{field_icon(k)} {field_label(k)}</span>"
            f"<span class='context-value'>{format_context_value(k, row.get(k))}</span></div>"
            for k in context_keys
        )
        st.markdown(f"<div class='context-grid'>{chips}</div>", unsafe_allow_html=True)

    filled_values = {}
    if not empties:
        st.info("كل الحقول معبّاة بهاد السجل.")
    else:
        st.markdown("<div class='section-title'>✏️ عبّي الحقول الناقصة</div>", unsafe_allow_html=True)
        st.info("⭐ أهم شي تعبيه: **الحالة**، و**تاريخ الإصدار**، و**تاريخ الانتهاء** (لو كانت الحالة غير ساري).")
        for field in sort_by_field_order(empties):
            with st.container(border=True):
                star = "⭐ " if field in PRIORITY_FIELDS else ""
                if field == STATUS_FIELD:
                    filled_values[field] = st.radio(
                        f"{star}{field_icon(field)} {field_label(field)}", STATUS_OPTIONS,
                        key=f"{rid}_{field}", horizontal=True,
                    )
                else:
                    filled_values[field] = st.text_input(
                        f"{star}{field_icon(field)} {field_label(field)}", key=f"{rid}_{field}",
                        placeholder=f"أدخل {field_label(field)}...",
                    )

    if st.button("💾 حفظ", key=f"save_{rid}", use_container_width=True, type="primary"):
        if filled_values.get(STATUS_FIELD) == STATUS_PLACEHOLDER:
            st.warning("لازم تختار الحالة: ساري أو غير ساري")
        else:
            updated_row = dict(row)
            updated_row.update(filled_values)
            data.save_row(username, updated_row, display_name)
            st.success("تم الحفظ!")
            st.rerun()
