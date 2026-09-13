"""
portal1_volunteer_app.py

Volunteer interface for Portal 1: filling in article text for the 13
laws that currently have zero articles. Single volunteer, password-
protected (PORTAL1_PASSWORD_HASH). Every article added or law marked
complete is written straight to Google Sheets on click — nothing is
held only in the browser session, so nothing is lost on a dropped
connection or a closed tab.

Run:
    streamlit run portal1_volunteer_app.py
"""

import streamlit as st
from cloud_secrets import bootstrap
bootstrap()

import bcrypt

from config import PORTAL1_PASSWORD_HASH
import portal1_data as data
from gsheets_client import is_true
from ui_theme import inject_css, inject_login_layout, hero, badge, logout_button

st.set_page_config(page_title="بوابة تعبئة المواد", page_icon="📜", layout="wide")
inject_css()

VOLUNTEER_NAME = "المتطوع"  # single volunteer for this portal — no separate accounts needed


def check_password(password: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), PORTAL1_PASSWORD_HASH.encode("utf-8"))


# ------------------------------------------------------------------
# Login gate
# ------------------------------------------------------------------

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    inject_login_layout()
    with st.container(border=True):
        hero("📜", "بوابة تعبئة المواد", "13 قانون بانتظار موادها — أدخل كلمة المرور للبدء")
        pw = st.text_input("كلمة المرور", type="password", label_visibility="collapsed", placeholder="كلمة المرور")
        if st.button("دخول", use_container_width=True, type="primary"):
            if check_password(pw):
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("كلمة المرور غير صحيحة")
    st.stop()

# ------------------------------------------------------------------
# Main app
# ------------------------------------------------------------------

progress_rows = data.get_progress_rows()
total = len(progress_rows)
done = sum(1 for r in progress_rows if is_true(r.get("completed")))

st.markdown(f"""
<div style='margin-bottom:0.5rem;'>
    <h1 style='color:#142846; margin-bottom:0.2rem;'>📜 بوابة تعبئة المواد</h1>
    <p style='color:#6B7A90;'>أنجزت {done} من {total} قانون</p>
</div>
""", unsafe_allow_html=True)
logout_button()
st.progress(done / total if total else 0)
st.markdown("<br>", unsafe_allow_html=True)

for row in progress_rows:
    rid = int(row["record_id"])
    is_done = is_true(row.get("completed"))
    card_class = "card done" if is_done else "card"

    st.markdown(f"""
    <div class='{card_class}'>
        <div class='card-title'>{row.get('Leg_Name', '')}</div>
        <div class='card-meta'>رقم {row.get('Leg_Number') or '—'} · سنة {row.get('Year', '')} &nbsp; {badge(is_done)}</div>
    </div>
    """, unsafe_allow_html=True)

    is_open = st.session_state.get("selected_record_id") == rid
    if st.button("إغلاق" if is_open else "فتح لإضافة مواد", key=f"toggle_{rid}"):
        st.session_state.selected_record_id = None if is_open else rid
        st.rerun()

    if st.session_state.get("selected_record_id") == rid:
        with st.container(border=True):
            articles = data.get_articles_for_record(rid)
            if articles:
                st.markdown("**المواد المدخلة حتى الآن:**")
                for a in articles:
                    st.markdown(f"""
                    <div class='subtle-box'>
                        <span class='pill-number'>مادة {a.get('article_number')}</span>
                        {a.get('article_text', '')}
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("ما في مواد مدخلة لسا لهاد القانون.")

            next_num = data.next_article_number(rid)
            st.markdown(f"**إضافة مادة رقم {next_num}:**")
            new_text = st.text_area(
                "نص المادة", key=f"new_text_{rid}",
                label_visibility="collapsed", placeholder="اكتب نص المادة هون...",
            )

            c1, c2 = st.columns(2)
            with c1:
                if st.button("➕ أضف المادة", key=f"add_{rid}", use_container_width=True, type="primary"):
                    if new_text.strip():
                        data.add_article(
                            rid, row.get("Leg_Name", ""), row.get("Leg_Number", ""), row.get("Year", ""),
                            next_num, new_text.strip(), VOLUNTEER_NAME,
                        )
                        st.success("انضافت المادة!")
                        st.rerun()
                    else:
                        st.warning("لازم تكتب نص المادة قبل الإضافة")
            with c2:
                if not is_done:
                    if st.button("✅ علّم القانون كمكتمل", key=f"complete_{rid}", use_container_width=True, type="primary"):
                        data.mark_complete(rid, VOLUNTEER_NAME, True)
                        st.success("تم! انتقل للقانون التالي")
                        st.rerun()
                else:
                    if st.button("↩️ إلغاء الاكتمال", key=f"undo_{rid}", use_container_width=True):
                        data.mark_complete(rid, VOLUNTEER_NAME, False)
                        st.rerun()
