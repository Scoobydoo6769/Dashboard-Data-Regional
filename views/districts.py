from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from charts import show, style_fig
from data import CLOSED, DEFAULT, LATE_SET, MEDIATE, RUN, STATUSES, SUE, as_of, be_date, get_data
from filters import fy_widget, in_fy, reset_button
from theme import T, card_head, empty_state, kpi, page_head

STATUS_COLOR = {RUN: "#7898BF", CLOSED: "#388F5F", DEFAULT: "#DBB878", MEDIATE: "#DE9A4A", SUE: "#C24F43"}  # โทนอ่อน: น้ำเงิน=ดำเนินอยู่, เขียว=ปิด, ทอง/ส้ม/แดง=เกินกำหนด

def district_metrics(d: pd.DataFrame) -> pd.DataFrame:
    """ตัวชี้วัดรายอำเภอจากข้อมูลในช่วงปีที่เลือก + คะแนนรวม (เฉลี่ยอันดับเปอร์เซ็นไทล์ของ 3 ตัวชี้วัดหลัก)"""
    late = d["status"].isin(LATE_SET)
    g = d.assign(late=late, closed=d["status"] == CLOSED, late_bal=d["balance"].where(late, 0)).groupby("district").agg(
        n=("status", "size"), approved=("approved", "sum"), members=("members", "sum"), principal=("principal", "sum"),
        late_n=("late", "sum"), closed_n=("closed", "sum"), late_bal=("late_bal", "sum"))
    g["repay"] = g["principal"] / g["approved"]
    g["closed_share"] = g["closed_n"] / g["n"]
    g["late_share"] = g["late_n"] / g["n"]
    g["late_ratio"] = g["late_bal"] / g["approved"]
    pct = lambda s, higher: (s if higher else -s).rank(pct=True)
    g["score"] = (pct(g["repay"], True) + pct(g["late_share"], False) + pct(g["late_ratio"], False)) / 3 * 100
    return g.sort_values(["score", "repay"], ascending=False)  # คะแนนเท่ากัน ตัดสินด้วยอัตราชำระคืน

def page_districts():
    df = get_data()
    head, f1, f2 = st.columns([2.3, 1.4, .7], vertical_alignment="bottom")
    with head:
        page_head("ผลการดำเนินงานรายอำเภอ", f"เปรียบเทียบ {df['district'].nunique()} อำเภอจากข้อมูลสัญญาเงินกู้ · ข้อมูล ณ วันที่ {be_date(as_of(df))}")
    with f1:
        lo, hi = fy_widget(df)
    with f2:
        reset_button()
    d = in_fy(df, lo, hi)
    if d.empty:
        empty_state()
    g = district_metrics(d)
    best, worst = g.index[0], g.index[-1]
    prov_rate, prov_late = d["principal"].sum() / d["approved"].sum(), d["status"].isin(LATE_SET).mean()

    k = [kpi("อำเภอที่คะแนนรวมสูงสุด", best, "", f"คะแนน {g['score'].iloc[0]:.0f} / 100", "good", "up"),
         kpi("อำเภอที่คะแนนรวมต่ำสุด", worst, "", f"คะแนน {g['score'].iloc[-1]:.0f} / 100", "bad", "down"),
         kpi("อัตราชำระคืนเงินต้นทั้งจังหวัด", f"{prov_rate:.1%}", "", f"สูงสุด {g['repay'].idxmax()} {g['repay'].max():.1%}"),
         kpi("สัดส่วนโครงการเกินกำหนดทั้งจังหวัด", f"{prov_late:.1%}", "", f"สูงสุด {g['late_share'].idxmax()} {g['late_share'].max():.1%}", "bad", "flat")]
    st.markdown('<div class="kpi-row">' + "".join(k) + "</div>", unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1, st.container(key="card_dt_score"):
        card_head(f"{best}ได้คะแนนรวมสูงสุด ส่วน{worst}ต่ำสุด", "คะแนนรวมรายอำเภอ (0–100) — สูง = ผลดำเนินงานดีกว่าเมื่อเทียบกันเอง")
        gs = g.iloc[::-1]
        cols = [T["GOOD"] if i in g.index[:3] else (T["BAD"] if i in g.index[-3:] else T["STEEL"]) for i in gs.index]
        fig = go.Figure(go.Bar(x=gs["score"], y=gs.index, orientation="h", marker_color=cols, text=gs["score"].round(0), textposition="outside",
                               hovertemplate="%{y}: %{x:.0f} คะแนน<extra></extra>"))
        fig.update_xaxes(range=[0, 112])
        show(style_fig(fig, 330, legend=False), "dt_score")
    with c2, st.container(key="card_dt_scatter"):
        card_head("อำเภอที่ชำระคืนดีมักมีสัดส่วนเกินกำหนดต่ำ", "สัดส่วนโครงการเกินกำหนด (แกนนอน) vs อัตราชำระคืนเงินต้น (แกนตั้ง) · ขนาดวงกลม = ยอดอนุมัติ")
        fig = go.Figure(go.Scatter(x=g["late_share"], y=g["repay"], mode="markers+text", text=g.index, textposition="top center",
                                   marker=dict(size=np.sqrt(g["approved"] / g["approved"].max()) * 42, color=T["STEEL"], opacity=.75,
                                               line=dict(color="#fff", width=1)),
                                   hovertemplate="%{text}<br>เกินกำหนด %{x:.1%} · ชำระคืน %{y:.1%}<extra></extra>"))
        fig.add_vline(x=prov_late, line_dash="dot", line_color=T["MUTED"]); fig.add_hline(y=prov_rate, line_dash="dot", line_color=T["MUTED"])
        fig.update_xaxes(title="สัดส่วนโครงการเกินกำหนด", tickformat=".0%", showgrid=True, gridcolor="#E8ECF1")
        fig.update_yaxes(title="อัตราชำระคืนเงินต้น", tickformat=".0%")
        show(style_fig(fig, 330, legend=False), "dt_scatter")

    with st.container(key="card_dt_mix"):
        mix = d.groupby(["district", "status"]).size().unstack(fill_value=0).reindex(columns=STATUSES, fill_value=0).loc[g.index[::-1]]
        pctmix = mix.div(mix.sum(axis=1), axis=0)
        card_head("สัดส่วนสถานะโครงการรายอำเภอ", "เรียงตามคะแนนรวม (บนสุด = ดีที่สุด) — สีแดง/ส้ม/ทอง = เกินกำหนด")
        fig = go.Figure([go.Bar(y=pctmix.index, x=pctmix[s], name=s, orientation="h", marker_color=STATUS_COLOR[s],
                                customdata=mix[s], hovertemplate="%{y} · " + s + ": %{x:.1%} (%{customdata} โครงการ)<extra></extra>") for s in STATUSES])
        fig.update_layout(barmode="stack")
        fig.update_xaxes(tickformat=".0%")
        show(style_fig(fig, 340), "dt_mix")

    with st.container(key="card_dt_table"):
        card_head("ตารางผลการดำเนินงานรายอำเภอ", "คะแนนรวม = ค่าเฉลี่ยอันดับเปอร์เซ็นไทล์ของ 3 ตัวชี้วัด: อัตราชำระคืนเงินต้น (สูงดี), สัดส่วนโครงการเกินกำหนด (ต่ำดี), ยอดคงเหลือเกินกำหนดต่อวงเงิน (ต่ำดี)")
        t = pd.DataFrame({"อันดับ": range(1, len(g) + 1), "อำเภอ": g.index, "คะแนนรวม": g["score"].round(0).to_numpy(),
                          "โครงการ": g["n"].to_numpy(), "ยอดอนุมัติ (ล้านบาท)": g["approved"].to_numpy() / 1e6,
                          "ชำระคืนเงินต้น": g["repay"].to_numpy(), "ปิดโครงการ": g["closed_share"].to_numpy(),
                          "เกินกำหนด": g["late_share"].to_numpy(), "คงเหลือเกินกำหนด (ล้านบาท)": g["late_bal"].to_numpy() / 1e6,
                          "คงเหลือเกินกำหนด ÷ วงเงิน": g["late_ratio"].to_numpy()})
        good, bad = {"ชำระคืนเงินต้น", "ปิดโครงการ"}, {"เกินกำหนด", "คงเหลือเกินกำหนด (ล้านบาท)", "คงเหลือเกินกำหนด ÷ วงเงิน"}
        def hl(col):
            if col.name in good:
                return [f"color:{T['GOOD']};font-weight:700" if v == col.max() else (f"color:{T['BAD']}" if v == col.min() else "") for v in col]
            if col.name in bad:
                return [f"color:{T['GOOD']};font-weight:700" if v == col.min() else (f"color:{T['BAD']};font-weight:700" if v == col.max() else "") for v in col]
            return [""] * len(col)
        sty = (t.style.format({"ยอดอนุมัติ (ล้านบาท)": "{:,.1f}", "คงเหลือเกินกำหนด (ล้านบาท)": "{:,.1f}", "ชำระคืนเงินต้น": "{:.1%}",
                               "ปิดโครงการ": "{:.1%}", "เกินกำหนด": "{:.1%}", "คงเหลือเกินกำหนด ÷ วงเงิน": "{:.1%}", "โครงการ": "{:,}"})
               .apply(hl, axis=0))
        st.dataframe(sty, hide_index=True, width="stretch")
        st.download_button("ดาวน์โหลดตาราง (CSV)", t.to_csv(index=False).encode("utf-8-sig"), "district_performance.csv", "text/csv",
                           icon=":material/download:", key="dl_dist")
    st.caption("เป็นการเปรียบเทียบผลลัพธ์รายพื้นที่จากข้อมูลสัญญา ไม่ใช่การประเมินการทำงานของเจ้าหน้าที่หรือหน่วยงาน "
               "เพราะผลการชำระคืนขึ้นกับปัจจัยอื่น เช่น ประเภทโครงการ อายุสัญญา และสภาพเศรษฐกิจในพื้นที่")
