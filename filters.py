"""Shared sidebar/page filters and table formatting."""
from __future__ import annotations

import pandas as pd
import streamlit as st
from data import DATA_FILE, DATES, DISTRICTS, LABELS, LATE_SET, MONEY, as_of, be_date, get_data
from theme import T

def data_note(df: pd.DataFrame):
    st.markdown(f'<div class="note">แหล่งข้อมูล: <b>{DATA_FILE.name}</b> (ข้อมูลที่คลีนแล้ว {len(df):,} สัญญา) · ข้อมูล ณ วันที่ {be_date(as_of(df))}</div>',
                unsafe_allow_html=True)

def _fy_years(df: pd.DataFrame) -> list[int]:
    return sorted(int(y) for y in df["fy"].unique())

def init_filters(df: pd.DataFrame):
    ys = _fy_years(df)
    st.session_state.setdefault("fy_sel", (ys[0], ys[-1]))          # ค่าเริ่มต้น = ทุกปีงบประมาณ
    st.session_state.setdefault("district_sel", "ทั้งจังหวัด")

def global_fy(df: pd.DataFrame):
    """ช่วงปีงบประมาณจากตัวกรองใน sidebar (ใช้ร่วมกันทุกหน้า)"""
    init_filters(df)
    v = st.session_state["fy_sel"]
    lo, hi = (v if isinstance(v, (tuple, list)) and len(v) == 2 else (v, v))
    return int(lo), int(hi)

def global_district(df: pd.DataFrame) -> str:
    init_filters(df)
    return st.session_state["district_sel"]

def fkey(name: str) -> str:
    """คีย์ของตัวกรอง + เลขเวอร์ชัน: กดรีเซ็ตแล้วเลขเวอร์ชันเพิ่ม -> widget ทุกตัวถูกสร้างใหม่ด้วยค่าเริ่มต้น
    (การลบ key ออกจาก session_state ไม่พอ เพราะฝั่งเบราว์เซอร์ยังจำค่าเดิมของ widget ที่ id เดิมไว้)"""
    return f"{name}_v{st.session_state.get('filter_ver', 0)}"

def _on_fy():
    v = st.session_state[fkey("w_fy")]
    st.session_state["fy_sel"] = tuple(v) if isinstance(v, (tuple, list)) and len(v) == 2 else (v, v)

def _on_district():
    st.session_state["district_sel"] = st.session_state[fkey("w_district")]

def reset_all_filters():
    """คืนค่าตัวกรองทุกตัวเป็นค่าเริ่มต้น (ทั้งตัวกรองร่วมและตัวกรองเฉพาะหน้า)"""
    ys = _fy_years(get_data())
    st.session_state["fy_sel"] = (ys[0], ys[-1])
    st.session_state["district_sel"] = "ทั้งจังหวัด"
    st.session_state["filter_ver"] = st.session_state.get("filter_ver", 0) + 1   # เปลี่ยนคีย์ widget ทุกตัวผ่าน fkey()

def reset_button():
    """ปุ่มรีเซ็ตตัวกรอง วางข้างตัวกรองในแต่ละหน้า"""
    st.button("รีเซ็ต", icon=":material/restart_alt:", on_click=reset_all_filters, key="reset_filters", help="คืนตัวกรองทั้งหมดเป็นค่าเริ่มต้น")

def fy_widget(df: pd.DataFrame):
    """แถบเลือกช่วงปีงบประมาณ (วางในหน้าเดิมของแต่ละหน้า) — ค่าที่เลือกใช้ร่วมกันทุกหน้า"""
    ys = _fy_years(df)
    lo, hi = global_fy(df)
    start, end = (lo, hi) if lo in ys and hi in ys else (ys[0], ys[-1])
    # ต้องส่ง value เป็น tuple เสมอ: Streamlit ตัดสินว่าเป็น range slider (2 หัวลาก) จากพารามิเตอร์ value เท่านั้น
    v = st.select_slider("ปีงบประมาณ (พ.ศ.)", options=ys, value=(start, end), key=fkey("w_fy"), on_change=_on_fy)
    return int(v[0]), int(v[1])

def district_widget(df: pd.DataFrame, label: str = "อำเภอ (District)") -> str:
    init_filters(df)
    opts = ["ทั้งจังหวัด"] + [d for d in DISTRICTS if d in set(df["district"])]
    if st.session_state["district_sel"] not in opts:
        st.session_state["district_sel"] = "ทั้งจังหวัด"
    st.session_state[fkey("w_district")] = st.session_state["district_sel"]
    return st.selectbox(label, opts, key=fkey("w_district"), on_change=_on_district)

def prev_years(lo: int, hi: int):
    span = hi - lo + 1
    return lo - span, lo - 1

def in_fy(df, lo, hi):
    return df[(df["fy"] >= lo) & (df["fy"] <= hi)]

def pretty_table(df: pd.DataFrame, cols: list[str]):
    """ตารางแสดงผล: วันที่ พ.ศ., ตัวเลขมีจุลภาค, สถานะค้างชำระเป็นสีแดง"""
    t = df[cols].copy()
    for c in DATES:
        if c in t:
            t[c] = t[c].map(be_date)
    t = t.rename(columns=LABELS)
    fmt = {LABELS[c]: "{:,.0f}" for c in MONEY + ["members"] if c in cols}
    fmt |= {LABELS[c]: "{:g}" for c in ("rate", "rate_late") if c in cols}
    sty = t.style.format(fmt, na_rep="-")
    if "status" in cols:
        sty = sty.map(lambda v: f"color:{T['BAD']};font-weight:600" if v in LATE_SET else "", subset=[LABELS["status"]])
    return sty
