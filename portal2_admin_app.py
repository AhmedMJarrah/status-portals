"""
portal2_admin_app.py

Read-only admin dashboard for Portal 2: aggregated + per-volunteer
progress across all 5 isolated tabs. Password-protected
(ADMIN_PASSWORD_HASH, shared with Portal 1's admin app).

Run:
    streamlit run portal2_admin_app.py
"""

import streamlit as st
from cloud_secrets import bootstrap
bootstrap()

import bcrypt

from config import ADMIN_PASSWORD_HASH, PORTAL2_VOLUNTEER_USERNAMES
import portal2_data as data
from gsheets_client import is_true
from ui_theme import inject_css, inject_login_layout, hero, badge

st.set_page_config(page_title="لوحة تحكم — تعبئة البيانات", page_icon="📊", layout="wide")
inject_css()


def check_password(password: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), ADMIN_PASSWORD_HASH.encode("utf-8"))


if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False

if not st.session_state.admin_authenticated:
    inject_login_layout()
    with st.container(border=True):
        hero("📊", "لوحة تحكم الأدمن", "متابعة تقدّم تعبئة البيانات — 5 متطوعين")
        pw = st.text_input("كلمة مرور الأدمن", type="password", label_visibility="collapsed", placeholder="كلمة المرور")
        if st.button("دخول", use_container_width=True, type="primary"):
            if check_password(pw):
                st.session_state.admin_authenticated = True
                st.rerun()
            else:
                st.error("كلمة المرور غير صحيحة")
    st.stop()

# ------------------------------------------------------------------
# Dashboard
# ------------------------------------------------------------------

if st.button("↻ تحديث البيانات"):
    st.rerun()

st.markdown("<h1 style='color:#142846;'>📊 لوحة تحكم — بوابة البيانات</h1>", unsafe_allow_html=True)

per_volunteer = {u: data.progress_summary(u) for u in PORTAL2_VOLUNTEER_USERNAMES}
total_done = sum(d for d, t in per_volunteer.values())
total_all = sum(t for d, t in per_volunteer.values())

m1, m2, m3 = st.columns(3)
m1.metric("الإجمالي", total_all)
m2.metric("مكتمل", total_done)
m3.metric("متبقي", total_all - total_done)
st.progress(total_done / total_all if total_all else 0)

st.markdown("### التقدّم حسب المتطوع")
cols = st.columns(len(PORTAL2_VOLUNTEER_USERNAMES))
for i, uname in enumerate(PORTAL2_VOLUNTEER_USERNAMES):
    done, total = per_volunteer[uname]
    with cols[i]:
        st.markdown(f"""
        <div class='card' style='text-align:center;'>
            <div class='card-title'>{uname}</div>
            <div class='card-meta'>{done} / {total}</div>
        </div>
        """, unsafe_allow_html=True)
        st.progress(done / total if total else 0)

st.markdown("### السجلات المتبقية (غير مكتملة)")
any_pending = False
for uname in PORTAL2_VOLUNTEER_USERNAMES:
    rows = data.get_rows(uname)
    pending = [r for r in rows if not is_true(r.get("completed"))]
    for row in pending:
        any_pending = True
        st.markdown(f"""
        <div class='card'>
            <div class='card-title'>{row.get('Leg_Name', '')}</div>
            <div class='card-meta'>سنة {row.get('Year', '')} &nbsp; {badge(False)} &nbsp; · المتطوع المكلّف: {uname}</div>
        </div>
        """, unsafe_allow_html=True)

if not any_pending:
    st.success("كل السجلات معبّاة! 🎉")
