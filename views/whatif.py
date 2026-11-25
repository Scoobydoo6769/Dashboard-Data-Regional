from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from charts import show, style_fig
from data import LATE_SET, RUN, TH_ABBR, as_of, baht_m, be_date, get_data
from filters import data_note, district_widget, fkey, reset_button
from theme import FONT, T, card_head, delta_pct, empty_state, kpi, page_head

def forecast(years: np.ndarray, y: np.ndarray, new_years: np.ndarray, method: str) -> np.ndarray:
    if method == "Linear Regression":
        b, a = np.polyfit(years, y, 1)
        return np.maximum(a + b * new_years, 0)
    return np.full(len(new_years), y[-3:].mean())

SIM_DEFAULTS = {"wi_pace": 100, "wi_rec": 30}

def _reset_sim():
    st.session_state.update(SIM_DEFAULTS)

def page_whatif():
    df = get_data()
    page_head("พยากรณ์แนวโน้ม & ตัวจำลองสถานการณ์ (What-If)", "คาดการณ์ยอดอนุมัติรายปี และลองปรับตัวแปรเพื่อดูผลการเก็บคืนเงินกู้ใน 12 เดือนข้างหน้า")
    data_note(df)
    # ── ก) แนวโน้มยอดอนุมัติรายปีงบประมาณ
    with st.container(key="card_wi_trend"):
        c0, c1 = st.columns([1, 1.4], vertical_alignment="bottom")
        with c0:
            dist = district_widget(df, "อำเภอ")
        method = c1.segmented_control("วิธีพยากรณ์", ["Linear Regression", "Moving Average (3 ปี)"], default="Linear Regression", key=fkey("wi_method")) or "Linear Regression"
        sel = df if dist == "ทั้งจังหวัด" else df[df["district"] == dist]
        g = sel.groupby("fy")["approved"].sum()
        if len(g) < 4:
            empty_state("ข้อมูลน้อยกว่า 4 ปีงบประมาณ ยังพยากรณ์แนวโน้มไม่ได้")
        all_years = [int(y) for y in g.index]
        c2, c3, c4, _ = st.columns([1.6, .56, .4, .44], gap="xsmall", vertical_alignment="bottom")
        h0, h1 = c2.select_slider("ใช้ข้อมูลย้อนหลังช่วงปีงบประมาณ (พ.ศ.)", options=all_years, value=(all_years[0], all_years[-1]), key=fkey(f"wi_hist_{dist}"))
        horizon = c3.segmented_control("พยากรณ์ล่วงหน้า (ปี)", [1, 2, 3, 4, 5], default=3, key=fkey("wi_h")) or 3
        with c4:
            reset_button()
        fit = g[(g.index >= h0) & (g.index <= h1)]
        if len(fit) < 3:
            st.info("เลือกช่วงปีย้อนหลังอย่างน้อย 3 ปีงบประมาณ (ที่มีข้อมูล) จึงจะพยากรณ์ได้", icon=":material/date_range:")
            st.stop()
        yrs = fit.index.to_numpy()
        new = np.arange(yrs.max() + 1, yrs.max() + 1 + horizon)
        f = forecast(yrs, fit.to_numpy(float), new, method)
        card_head(f"แนวโน้มชี้ว่ายอดอนุมัติ {horizon} ปีงบประมาณข้างหน้า (พ.ศ. {new[0]}–{new[-1]}) เฉลี่ย {baht_m(f.mean())} ล้านบาท/ปี",
                  f"ยอดอนุมัติรายปีงบประมาณ (ล้านบาท) · เส้นประหนา = พยากรณ์ด้วย {method} จากข้อมูลปี {yrs.min()}–{yrs.max()}")
        fig = go.Figure([
            go.Scatter(x=[str(y) for y in g.index], y=g / 1e6, name="ข้อมูลจริง", mode="lines+markers", line=dict(color=T["NAVY2"], width=2.5), marker=dict(size=6)),
            go.Scatter(x=[str(yrs.max())] + [str(y) for y in new], y=np.r_[fit.iloc[-1], f] / 1e6, name="พยากรณ์", mode="lines+markers+text",
                       text=[""] + [f"{v / 1e6:.1f}M" for v in f], textposition="top center", textfont=dict(color="#8A4300", size=17, family=FONT),
                       line=dict(color="#B35C00", width=4.5, dash="dash"), marker=dict(size=10, color="#B35C00", line=dict(color="#fff", width=1.5)))])
        fig.update_xaxes(type="category")
        fig.update_yaxes(title="ล้านบาท", rangemode="tozero")
        show(style_fig(fig, 320), "wi_trend")
        gaps = sorted(set(range(int(yrs.min()), int(yrs.max()) + 1)) - set(yrs.tolist()))
        st.caption("พยากรณ์ด้วยการต่อเส้นแนวโน้มอย่างง่ายจากข้อมูลย้อนหลังในช่วงปีที่เลือก ไม่คำนึงถึงนโยบายหรือปัจจัยภายนอก"
                   + (f" · ไม่มีข้อมูลปีงบประมาณ {', '.join(map(str, gaps))}" if gaps else ""))

    # ── ข) จำลองการเก็บคืนเงินกู้ 12 เดือน
    cut = as_of(df)
    act, late = df[df["status"] == RUN], df[df["status"].isin(LATE_SET)]
    with st.container(key="card_wi_ctrl"):
        card_head("จำลองการเก็บคืนเงินกู้ใน 12 เดือนข้างหน้า",
                  "โครงการที่ยังดำเนินการ: ยอดคงเหลือทยอยชำระเท่ากันทุกเดือนจนสิ้นสุดสัญญา · โครงการค้างชำระ: ฐานคือเก็บคืนไม่ได้เลย")
        for k_, v_ in SIM_DEFAULTS.items():
            st.session_state.setdefault(k_, v_)
        s1, s2, s3 = st.columns([1, 1, .25], vertical_alignment="bottom")
        pace = s1.slider("ความเร็วการชำระของโครงการที่ยังดำเนินการ (% ของกำหนด)", 50, 120, key="wi_pace")
        rec = s2.slider("ติดตามเก็บคืนยอดค้างชำระได้ (% ของยอดคงเหลือ)", 0, 100, key="wi_rec")
        s3.button("รีเซ็ต", icon=":material/restart_alt:", on_click=_reset_sim, key="reset_sim", help="คืนค่าตัวจำลองเป็นค่าเริ่มต้น (100% / 30%)")
    months = 12
    rem = np.maximum(1, (act["end"].dt.year - cut.year) * 12 + (act["end"].dt.month - cut.month)).to_numpy()
    bal = act["balance"].to_numpy()
    k = np.arange(1, months + 1)[:, None]
    cum = lambda m: np.minimum(k * bal / rem * m, bal).sum(axis=1)
    late_bal = late["balance"].sum()
    base_cum = cum(1.0)
    scen_cum = cum(pace / 100) + late_bal * rec / 100 * k.ravel() / months
    month_lab = [f"{TH_ABBR[p.month - 1]} {str(p.year + 543)[2:]}" for p in pd.period_range(cut.to_period("M") + 1, periods=months, freq="M")]
    tot_bal = act["balance"].sum() + late_bal
    cards = [
        kpi("เก็บคืนได้ใน 12 เดือน", baht_m(scen_cum[-1]), "ล้านบาท", *delta_pct(scen_cum[-1], base_cum[-1], "จากฐาน")),
        kpi("ยอดคงเหลือรวมหลัง 12 เดือน", baht_m(tot_bal - scen_cum[-1]), "ล้านบาท", *delta_pct(tot_bal - scen_cum[-1], tot_bal - base_cum[-1], "จากฐาน", good_up=False)),
        kpi("เก็บคืนจากโครงการค้างชำระ", baht_m(late_bal * rec / 100), "ล้านบาท", f"จากยอดค้าง {baht_m(late_bal)} ล้านบาท", "flat", "flat"),
        kpi("สัดส่วนของยอดคงเหลือทั้งพอร์ต", f"{scen_cum[-1] / tot_bal:.1%}", "", f"ฐาน {base_cum[-1] / tot_bal:.1%}", "flat", "flat"),
    ]
    st.markdown('<div class="kpi-row">' + "".join(cards) + "</div>", unsafe_allow_html=True)
    with st.container(key="card_wi_chart"):
        gain = scen_cum[-1] - base_cum[-1]
        card_head(f"ตามสถานการณ์จำลองจะเก็บคืนได้{'เพิ่ม' if gain >= 0 else 'ลด'}จากฐาน {abs(gain) / 1e6:,.1f} ล้านบาทใน 12 เดือน",
                  "ยอดเก็บคืนสะสม (ล้านบาท) · ฐาน = ตามกำหนดสัญญา และไม่เก็บคืนยอดค้างชำระ")
        fig = go.Figure([
            go.Scatter(x=month_lab, y=base_cum / 1e6, name="ฐาน (ตามกำหนด)", mode="lines", line=dict(color=T["SAND"], width=2.5, dash="dash")),
            go.Scatter(x=month_lab, y=scen_cum / 1e6, name="สถานการณ์จำลอง", mode="lines+markers", line=dict(color=T["NAVY2"], width=2.5), marker=dict(size=5))])
        fig.update_yaxes(title="ล้านบาท", rangemode="tozero")
        show(style_fig(fig, 320), "wi_chart")
    st.caption(f"คำนวณจากยอดคงเหลือ ณ {be_date(cut)} ของโครงการที่ยังดำเนินการ {len(act):,} โครงการ และค้างชำระ {len(late):,} โครงการ "
               "เป็นการประมาณอย่างง่ายเพื่อประกอบการตัดสินใจ ไม่ใช่ตัวเลขทางบัญชี")
