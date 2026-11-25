"""ระบบติดตามผลการดำเนินงาน (Dashboard) กองทุนพัฒนาบทบาทสตรี จังหวัดกระบี่

รันด้วย:  streamlit run app.py        เข้าสู่ระบบ: admin / krabi

ข้อมูล (วางในโฟลเดอร์ data/)
  KPI69_clean_only.xlsx  = ข้อมูลที่คลีนแล้ว (1 แถว = 1 สัญญา) -> ใช้ในทุกหน้า
  KPI69_raw_sheets.xlsx  = ข้อมูลดิบรายอำเภอ (ชีตที่ 2 เป็นต้นไป) -> ใช้เทียบก่อน/หลังคลีนในหน้า Audit (ไม่มีไฟล์นี้ก็ใช้งานได้)
อยากเปลี่ยนข้อมูล: วางไฟล์ใหม่ชื่อเดิมทับ (หัวคอลัมน์ต้องตรงกับ RENAME ด้านล่าง)
"""
import html

import streamlit as st

from auth import login_page, logout
from theme import inject_css
from views.actions import page_actions
from views.audit import page_audit
from views.districts import page_districts
from views.explorer import page_explorer
from views.overview import page_overview
from views.whatif import page_whatif

st.set_page_config(page_title="ระบบติดตามผลการดำเนินงาน | กองทุนฯ กระบี่", page_icon=":material/monitoring:", layout="wide")

if not st.session_state.get("auth"):
    login_page()
    st.stop()

inject_css()
nav = st.navigation({
    "แดชบอร์ด": [
        st.Page(page_overview, title="ภาพรวมข้อมูล", icon=":material/dashboard:", url_path="overview", default=True),
        st.Page(page_districts, title="ผลการดำเนินงานรายอำเภอ", icon=":material/leaderboard:", url_path="districts")],
    "ข้อมูล": [
        st.Page(page_audit, title="ข้อมูลดิบ & Audit Log", icon=":material/fact_check:", url_path="audit"),
        st.Page(page_explorer, title="สำรวจข้อมูลเชิงลึก", icon=":material/travel_explore:", url_path="explorer")],
    "วางแผน": [
        st.Page(page_whatif, title="พยากรณ์ & What-If", icon=":material/query_stats:", url_path="whatif"),
        st.Page(page_actions, title="แผนปฏิบัติการ", icon=":material/assignment:", url_path="actions")],
})
with st.sidebar:
    with st.container(key="side_logout"):   # ปักไว้ล่างสุดของ sidebar (ดู CSS .st-key-side_logout)
        st.markdown('<div class="side-rule"></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="user-chip">ผู้ใช้งาน <b>{html.escape(str(st.session_state["auth"]))}</b></div>', unsafe_allow_html=True)
        st.button("ออกจากระบบ", icon=":material/logout:", on_click=logout, key="logout")
nav.run()
