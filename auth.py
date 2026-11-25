"""Login gate and logout."""
from __future__ import annotations

import base64
import hmac
import streamlit as st
from data import BASE
from theme import inject_css

# เปลี่ยนรหัสผ่านได้ที่ .streamlit/secrets.toml  ->  [auth] user="..." password="..."
def _credentials() -> tuple[str, str]:
    try:
        return st.secrets["auth"]["user"], st.secrets["auth"]["password"]
    except Exception:
        return "", ""  # ไม่มี secrets -> ปฏิเสธการเข้าสู่ระบบ

# ─────────────────────────────── เข้าสู่ระบบ ───────────────────────────────
def login_page():
    inject_css(hide_sidebar=True)
    _, mid, _ = st.columns([1, 1.6, 1])
    with mid:
        seal = BASE / "assets" / "krabi_seal.png"
        if seal.exists():
            b64 = base64.b64encode(seal.read_bytes()).decode()
            st.markdown(f'<div style="text-align:center;margin:.5rem 0 .6rem"><img alt="ตราเมืองกระบี่" width="128" height="128" '
                        f'src="data:image/png;base64,{b64}"></div>', unsafe_allow_html=True)
        st.markdown('<div class="login-brand">กองทุนพัฒนาบทบาทสตรี จังหวัดกระบี่</div>'
                    '<div class="login-sub">ระบบติดตามผลการดำเนินงาน (Dashboard)</div>', unsafe_allow_html=True)
        with st.container(border=True, key="card_login"):
            with st.form("login_form", border=False):
                user = st.text_input("ชื่อผู้ใช้ (User)", key="login_user")
                pw = st.text_input("รหัสผ่าน (Password)", type="password", key="login_pw")
                ok = st.form_submit_button("เข้าสู่ระบบ", type="primary", width="stretch")
            if ok:
                u, p = _credentials()
                if u and p and hmac.compare_digest(user.encode(), u.encode()) & hmac.compare_digest(pw.encode(), p.encode()):
                    st.session_state["auth"] = user
                    st.rerun()
                st.error("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง กรุณาตรวจสอบแล้วลองอีกครั้ง", icon=":material/lock:")

def logout():
    for k in list(st.session_state):
        del st.session_state[k]
