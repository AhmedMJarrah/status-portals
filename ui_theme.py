"""
ui_theme.py — shared visual identity for every Streamlit app in this
project (both volunteer portals + both admin dashboards).

One shared module = one consistent visual language across all four
screens, and one place to tune colors/fonts instead of four. Import
inject_css() at the top of every app, right after st.set_page_config().
"""

import streamlit as st

ACCENT = "#2E86AB"
SUCCESS = "#1E9C55"
WARNING = "#C97A0C"


def inject_css() -> None:
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;900&display=swap');

    /* ---- Global RTL --------------------------------------------- */
    html, body, [class*="css"], .stApp {{
        direction: rtl;
        text-align: right;
        font-family: 'Tajawal', sans-serif !important;
    }}
    .stApp {{ background: linear-gradient(180deg, #F4F8FB 0%, #FFFFFF 45%); }}
    .block-container {{ direction: rtl; }}

    /* Streamlit renders form widgets LTR internally by default --
       flip the ones that carry visible text/alignment. */
    .stTextInput > div > div > input,
    .stTextArea textarea,
    .stNumberInput input,
    .stSelectbox > div > div,
    .stRadio > div {{
        text-align: right;
        direction: rtl;
    }}
    label, .stMarkdown, .stAlert, .stMetric {{ text-align: right; }}

    /* Native Streamlit tables/dataframes only partially honor CSS
       (they render inside an internal component) — for anything
       where RTL fidelity matters, this project renders plain HTML
       cards instead (see .card below), which are fully controllable. */

    /* ---- Buttons ----------------------------------------------------
       Real Streamlit buttons (secondary style) render with a border and
       white background by default. The previous version set
       border:none without an explicit background/border replacement,
       which left the button with no visible boundary at all — that's
       why it looked like plain blue link text instead of a button.
       Covering both the classic and current data-testid selectors
       since the exact internal markup varies by Streamlit version. */
    .stButton > button,
    button[data-testid="stBaseButton-secondary"],
    button[data-testid="baseButton-secondary"] {{
        background-color: #FFFFFF !important;
        color: {ACCENT} !important;
        border: 2px solid {ACCENT} !important;
        border-radius: 12px !important;
        font-weight: 700 !important;
        padding: 0.55rem 1.4rem !important;
        transition: all 0.2s ease !important;
    }}
    .stButton > button:hover,
    button[data-testid="stBaseButton-secondary"]:hover,
    button[data-testid="baseButton-secondary"]:hover {{
        background-color: {ACCENT} !important;
        color: #FFFFFF !important;
        transform: translateY(-2px);
        box-shadow: 0 6px 18px rgba(46, 134, 171, 0.25);
    }}
    /* Primary buttons (main call-to-action: login, save, add) — solid fill */
    button[kind="primary"],
    button[data-testid="stBaseButton-primary"],
    button[data-testid="baseButton-primary"] {{
        background-color: {ACCENT} !important;
        color: #FFFFFF !important;
        border: 2px solid {ACCENT} !important;
        border-radius: 12px !important;
        font-weight: 700 !important;
        padding: 0.55rem 1.4rem !important;
    }}
    button[kind="primary"]:hover,
    button[data-testid="stBaseButton-primary"]:hover,
    button[data-testid="baseButton-primary"]:hover {{
        opacity: 0.9;
        transform: translateY(-2px);
        box-shadow: 0 6px 18px rgba(46, 134, 171, 0.35);
    }}

    /* ---- Cards ------------------------------------------------- */
    .card {{
        background: #FFFFFF;
        border-radius: 18px;
        padding: 1.4rem 1.8rem;
        margin-bottom: 1rem;
        box-shadow: 0 2px 14px rgba(20, 40, 70, 0.06);
        border-right: 6px solid {ACCENT};
        transition: box-shadow 0.2s ease;
    }}
    .card:hover {{ box-shadow: 0 8px 24px rgba(20, 40, 70, 0.10); }}
    .card.done {{ border-right-color: {SUCCESS}; opacity: 0.92; }}

    .card-title {{ font-weight: 900; font-size: 1.05rem; color: #142846; margin-bottom: 0.3rem; }}
    .card-meta  {{ color: #6B7A90; font-size: 0.85rem; }}

    .badge {{ display:inline-block; padding:0.15rem 0.7rem; border-radius:999px; font-size:0.75rem; font-weight:700; }}
    .badge-done    {{ background:#E4F8ED; color:{SUCCESS}; }}
    .badge-pending {{ background:#FFF4E5; color:{WARNING}; }}

    .pill-number {{
        display:inline-block; background:{ACCENT}; color:white;
        border-radius:8px; padding:0.1rem 0.6rem; font-weight:700; margin-left:0.5rem;
    }}
    .subtle-box {{ background:#F7FAFC; border-radius:10px; padding:0.6rem 1rem; margin-bottom:0.5rem; font-size:0.92rem; }}

    /* ---- Context grid (record details shown for reference) --------- */
    .context-grid {{
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 0.7rem;
        margin-bottom: 0.8rem;
    }}
    .context-item {{
        display: flex;
        flex-direction: column;
        gap: 0.15rem;
        background: #FFFFFF;
        border-radius: 12px;
        padding: 0.6rem 0.9rem;
        box-shadow: 0 1px 6px rgba(20, 40, 70, 0.06);
        border-right: 4px solid {ACCENT};
    }}
    .context-label {{ font-size: 0.75rem; color: #6B7A90; font-weight: 700; }}
    .context-value {{ font-size: 0.92rem; color: #142846; }}
    @media (max-width: 640px) {{
        .context-grid {{ grid-template-columns: 1fr; }}
    }}

    .section-title {{
        font-weight: 900; font-size: 1rem; color: #142846;
        margin: 1.1rem 0 0.6rem; padding-right: 0.6rem;
        border-right: 4px solid {ACCENT};
    }}

    header[data-testid="stHeader"] {{ background: transparent; }}
    #MainMenu, footer {{ visibility: hidden; }}
    </style>
    """, unsafe_allow_html=True)


def inject_login_layout() -> None:
    """Extra CSS applied ONLY on login screens — vertically centers the
    login card in the viewport and gives it a real visible boundary
    (shadow + rounded corners), instead of floating in empty white
    space. Call this in addition to inject_css(), only inside the
    `if not authenticated:` branch — the main app's own long card lists
    should NOT be vertically centered, only the login screen."""
    st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] > .main .block-container {
        display: flex;
        flex-direction: column;
        justify-content: center;
        min-height: 82vh;
        max-width: 480px;
    }
    [data-testid="stVerticalBlockBorderWrapper"] {
        background: #FFFFFF;
        border-radius: 22px;
        padding: 2.2rem 2rem 1.6rem;
        box-shadow: 0 12px 40px rgba(20, 40, 70, 0.12);
        border: 1px solid #EEF2F6 !important;
    }
    </style>
    """, unsafe_allow_html=True)


def hero(icon: str, title: str, subtitle: str) -> None:
    """Centered header block — used on login screens and page tops."""
    st.markdown(f"""
    <div style='text-align:center; margin: 1.5rem 0 1.5rem;'>
        <div style='font-size: 3rem;'>{icon}</div>
        <h2 style='margin:0; color:#142846;'>{title}</h2>
        <p style='color:#6B7A90;'>{subtitle}</p>
    </div>
    """, unsafe_allow_html=True)


def badge(is_done: bool) -> str:
    return (
        "<span class='badge badge-done'>مكتمل ✓</span>" if is_done
        else "<span class='badge badge-pending'>قيد الانتظار</span>"
    )


def logout_button(label: str = "🚪 تسجيل خروج") -> None:
    """Clears all session state and reruns — a clean slate identical
    to a fresh page load, so the next person can log in as themselves."""
    if st.button(label, key="logout_btn"):
        st.session_state.clear()
        st.rerun()
