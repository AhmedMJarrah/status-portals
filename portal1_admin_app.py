"""
portal1_admin_app.py

Read-only admin dashboard for Portal 1: overall progress, per-law
status, and every article entered so far — for oversight, not editing.
Password-protected (ADMIN_PASSWORD_HASH, shared with Portal 2's admin
app).

Run:
    streamlit run portal1_admin_app.py
"""

import streamlit as st
from cloud_secrets import bootstrap
bootstrap()

import bcrypt

from config import ADMIN_PASSWORD_HASH
import portal1_data as data
from gsheets_client import is_true
from ui_theme import inject_css, inject_login_layout, hero, badge

st.set_page_config(page_title="لوحة تحكم — المواد", page_icon="📊", layout="wide")
inject_css()


def check_password(password: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), ADMIN_PASSWORD_HASH.encode("utf-8"))


if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False

if not st.session_state.admin_authenticated:
    inject_login_layout()
    with st.container(border=True):
        hero("📊", "لوحة تحكم الأدمن", "متابعة تقدّم تعبئة المواد")
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

progress_rows = data.get_progress_rows()
total = len(progress_rows)
done = sum(1 for r in progress_rows if is_true(r.get("completed")))

st.markdown("<h1 style='color:#142846;'>📊 لوحة تحكم — بوابة المواد</h1>", unsafe_allow_html=True)

m1, m2, m3 = st.columns(3)
m1.metric("الإجمالي", total)
m2.metric("مكتمل", done)
m3.metric("متبقي", total - done)
st.progress(done / total if total else 0)

st.markdown("### تفاصيل كل قانون")
for row in progress_rows:
    rid = int(row["record_id"])
    is_done = is_true(row.get("completed"))
    articles = data.get_articles_for_record(rid)

    st.markdown(f"""
    <div class='{"card done" if is_done else "card"}'>
        <div class='card-title'>{row.get('Leg_Name', '')}</div>
        <div class='card-meta'>
            رقم {row.get('Leg_Number') or '—'} · سنة {row.get('Year', '')}
            &nbsp; {badge(is_done)}
            &nbsp; · {len(articles)} مادة مدخلة
            {"· أنجزه " + str(row.get('completed_by')) + " بتاريخ " + str(row.get('completed_at')) if is_done else ""}
        </div>
    </div>
    """, unsafe_allow_html=True)
