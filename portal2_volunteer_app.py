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
from ui_theme import inject_css, inject_login_layout, hero, badge

st.set_page_config(page_title="بوابة تعبئة البيانات", page_icon="✨", layout="wide")
inject_css()

STATUS_FIELD = "Status"
STATUS_PLACEHOLDER = "اختر..."
STATUS_OPTIONS = [STATUS_PLACEHOLDER, "ساري", "غير ساري"]

FIELD_LABELS = {
    "Status": "الحالة", "URL": "الرابط", "Magazine_Date": "تاريخ الجريدة",
    "Magazine_Number": "رقم الجريدة", "Magazine_Page": "رقم الصفحة",
    "Publication": "بيان النشر", "Replaced_For": "بديل عن",
    "Canceled_By": "أُلغي بواسطة", "Issue_Date": "تاريخ الإصدار",
    "Active_Date": "تاريخ النفاذ", "End_Date": "تاريخ الانتهاء",
    "Replaced_By": "استُبدل بـ", "Leg_Number": "رقم التشريع",
    "Article_Count": "عدد المواد",
}


def field_label(key: str) -> str:
    return FIELD_LABELS.get(key, key)


AVATAR_ICONS = ["🦋", "🌟", "🌿", "🔥", "🌊"]

# ------------------------------------------------------------------
# Login — pick your avatar, then your password
# ------------------------------------------------------------------

if "username" not in st.session_state:
    st.session_state.username = None
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    inject_login_layout()
    with st.container(border=True):
        hero("✨", "بوابة تعبئة البيانات", "اختر اسمك وابدأ")

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
            st.markdown(
                f"<p style='text-align:center; margin-top:1.2rem; font-size:1.05rem;'>"
                f"أهلاً <b>{st.session_state.username}</b> 👋</p>",
                unsafe_allow_html=True,
            )
            pw = st.text_input("كلمة المرور", type="password", label_visibility="collapsed", placeholder="كلمة المرور")
            if st.button("دخول", use_container_width=True, type="primary"):
                if bcrypt.checkpw(pw.encode("utf-8"), PORTAL2_SHARED_PASSWORD_HASH.encode("utf-8")):
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("كلمة المرور غير صحيحة")
    st.stop()

username = st.session_state.username

# ------------------------------------------------------------------
# Main app
# ------------------------------------------------------------------

rows = data.get_rows(username)
done, total = data.progress_summary(username)

st.markdown(f"""
<div style='margin-bottom:0.5rem;'>
    <h1 style='color:#142846; margin-bottom:0.2rem;'>✨ أهلاً {username}</h1>
    <p style='color:#6B7A90;'>أنجزت {done} من {total} سجل</p>
</div>
""", unsafe_allow_html=True)
st.progress(done / total if total else 0)
st.markdown("<br>", unsafe_allow_html=True)

for row in rows:
    rid = row.get("record_id")
    row_is_done = is_true(row.get("completed"))
    empties = data.empty_fields(row)

    st.markdown(f"""
    <div class='{"card done" if row_is_done else "card"}'>
        <div class='card-title'>{row.get('Leg_Name', '')}</div>
        <div class='card-meta'>سنة {row.get('Year', '')} &nbsp; {badge(row_is_done)} &nbsp; · {len(empties)} حقل فاضي</div>
    </div>
    """, unsafe_allow_html=True)

    is_open = st.session_state.get("selected_record_id") == rid
    if st.button("إغلاق" if is_open else "فتح للتعبئة", key=f"toggle_{rid}"):
        st.session_state.selected_record_id = None if is_open else rid
        st.rerun()

    if st.session_state.get("selected_record_id") == rid:
        with st.container(border=True):
            context_items = [
                (k, v) for k, v in row.items()
                if k not in empties and k not in ("record_id", "completed", "entered_by", "entered_at")
                and str(v).strip()
            ]
            if context_items:
                context_html = " · ".join(f"<b>{field_label(k)}:</b> {v}" for k, v in context_items)
                st.markdown(f"<div class='subtle-box'>{context_html}</div>", unsafe_allow_html=True)

            filled_values = {}
            if not empties:
                st.info("كل الحقول معبّاة بهاد السجل.")
            else:
                st.markdown("**عبّي الحقول الناقصة:**")
                for field in empties:
                    if field == STATUS_FIELD:
                        filled_values[field] = st.radio(
                            field_label(field), STATUS_OPTIONS, key=f"{rid}_{field}", horizontal=True,
                        )
                    else:
                        filled_values[field] = st.text_input(
                            field_label(field), key=f"{rid}_{field}", placeholder=f"أدخل {field_label(field)}...",
                        )

            if st.button("💾 حفظ", key=f"save_{rid}", use_container_width=True, type="primary"):
                if filled_values.get(STATUS_FIELD) == STATUS_PLACEHOLDER:
                    st.warning("لازم تختار الحالة: ساري أو غير ساري")
                else:
                    updated_row = dict(row)
                    updated_row.update(filled_values)
                    data.save_row(username, updated_row, username)
                    st.success("تم الحفظ!")
                    st.rerun()
