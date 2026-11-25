from __future__ import annotations

import io
import numpy as np
import plotly.graph_objects as go
import streamlit as st
from math import ceil
from charts import show, style_fig
from data import CATEGORIES, DATES, LABELS, LATE_SET, STATUSES, baht_m, get_data
from filters import data_note, fkey, fy_widget, in_fy, pretty_table, reset_button
from theme import T, card_head, empty_state, page_head

def page_explorer():
    df = get_data()
    page_head("สำรวจข้อมูลเชิงลึก (Deep-Dive Explorer)", "กรองได้หลายมิติ ค้นหา เรียงลำดับ และส่งออกข้อมูลที่คลีนแล้วเพื่อตรวจสอบต่อ")
    data_note(df)
    with st.container(key="card_filters"):
        c1, c2, c3, c7 = st.columns([1.3, 1.3, 1.2, .6], vertical_alignment="bottom")
        with c1:
            lo, hi = fy_widget(df)
        with c7:
            reset_button()
        dists = c2.multiselect("อำเภอ", sorted(df["district"].unique()), key=fkey("dd_dist"), placeholder="ทุกอำเภอ")
        cats = c3.multiselect("ประเภทโครงการ", CATEGORIES, key=fkey("dd_cat"), placeholder="ทุกประเภท")
        c4, c5, c6 = st.columns([2.3, 1.2, 1.1])
        status = c4.pills("สถานะ", ["ทั้งหมด"] + STATUSES, default="ทั้งหมด", key=fkey("dd_status"))
        q = c5.text_input("ค้นหา", key=fkey("dd_q"), placeholder="ชื่อโครงการ, ผู้ร่วมโครงการ หรือเลขที่สัญญา")
        hi_bal = c6.slider("ไฮไลต์เมื่อยอดคงเหลือมากกว่า (บาท)", 0, 200_000, 150_000, 10_000, key=fkey("dd_bal"))
    d = in_fy(df, lo, hi)
    if dists: d = d[d["district"].isin(dists)]
    if cats: d = d[d["category"].isin(cats)]
    if status and status != "ทั้งหมด": d = d[d["status"] == status]
    if q:
        qq = q.strip()
        d = d[d["project"].str.contains(qq, case=False, regex=False) | d["proposers"].str.contains(qq, case=False, regex=False)
              | d["contract_id"].str.contains(qq, regex=False)]
    if d.empty:
        empty_state()

    k = st.columns(4)
    k[0].metric("โครงการ", f"{len(d):,}")
    k[1].metric("ยอดอนุมัติ", f"{baht_m(d['approved'].sum())} ล้านบาท")
    k[2].metric("ยอดคงเหลือ", f"{baht_m(d['balance'].sum())} ล้านบาท")
    k[3].metric("เกินกำหนดสัญญา", f"{d['status'].isin(LATE_SET).sum():,} โครงการ", help="ผิดนัดชำระ + ไกล่เกลี่ย + ดำเนินการฟ้อง")

    ca, cb = st.columns(2)
    with ca, st.container(key="card_dd_rate"):
        r = d.groupby("district").agg(n=("status", "size"), late=("status", lambda s: s.isin(LATE_SET).sum()))
        r["p"] = r["late"] / r["n"]
        r = r.sort_values("p")
        card_head(f"{r.index[-1]}มีสัดส่วนโครงการเกินกำหนดสูงสุดที่ {r['p'].iloc[-1]:.0%}", "สัดส่วนโครงการเกินกำหนดรายอำเภอ (ผิดนัด+ไกล่เกลี่ย+ฟ้อง ÷ โครงการทั้งหมด)")
        avg = (d["status"].isin(LATE_SET)).mean()
        fig = go.Figure(go.Bar(x=r["p"], y=r.index, orientation="h", marker_color=[T["BAD"] if v > avg else T["NAVY2"] for v in r["p"]],
                               customdata=np.c_[r["late"], r["n"]], hovertemplate="%{y}: %{x:.1%} (%{customdata[0]} จาก %{customdata[1]})<extra></extra>"))
        fig.update_xaxes(tickformat=".0%")
        fig.add_vline(x=avg, line_dash="dot", line_color=T["MUTED"], annotation_text=f"เฉลี่ย {avg:.0%}", annotation_position="top")
        show(style_fig(fig, 300, legend=False), "dd_rate")
    with cb, st.container(key="card_dd_scatter"):
        od = d[d["status"].isin(LATE_SET)]
        card_head(f"โครงการเกินกำหนด {len(od):,} แห่ง คงเหลือรวม {baht_m(od['balance'].sum())} ล้านบาท",
                  "วันที่สิ้นสุดสัญญา vs ยอดคงเหลือ (Scatter) — สีแดง = เกินกำหนด")
        fig = go.Figure(go.Scatter(x=d["end"], y=d["balance"] / 1e3, mode="markers", text=d["project"],
                                   marker=dict(size=7, opacity=.75, color=np.where(d["status"].isin(LATE_SET), T["BAD"], T["STEEL"])),
                                   hovertemplate="%{text}<br>สิ้นสุด %{x|%d/%m/%Y} · คงเหลือ %{y:,.0f} พันบาท<extra></extra>"))
        fig.update_xaxes(title="วันที่สิ้นสุดสัญญา (ค.ศ.)")
        fig.update_yaxes(title="ยอดคงเหลือ (พันบาท)")
        show(style_fig(fig, 300, legend=False), "dd_scatter")

    with st.container(key="card_dd_table"):
        card_head("ตารางข้อมูลที่คลีนแล้ว", "แถวที่ยอดคงเหลือเกินเกณฑ์จะถูกไฮไลต์สีแดงอ่อน")
        s1, s2, s3, s4 = st.columns([1.4, 1, 1, 1])
        cols = ["contract_id", "district", "subdistrict", "fy", "project", "category", "approved", "principal", "balance", "last", "end", "status"]
        sort_label = s1.selectbox("เรียงตาม", [LABELS[c] for c in cols], index=cols.index("balance"), key="dd_sort")
        asc = s2.toggle("น้อย → มาก", value=False, key="dd_asc")
        size = s3.selectbox("แถวต่อหน้า", [10, 25, 50, 100], index=1, key="dd_size")
        pages = max(1, ceil(len(d) / size))
        page = s4.number_input(f"หน้า (จาก {pages:,})", 1, pages, 1, key=f"dd_page_{len(d)}_{size}")
        inv = {LABELS[c]: c for c in cols}
        view = d.sort_values(inv[sort_label], ascending=asc, na_position="last").iloc[(page - 1) * size: page * size]
        sty = pretty_table(view, cols)
        flags = (view["balance"] > hi_bal).to_numpy()
        sty = sty.apply(lambda col: [f"background-color:{T['BAD_BG']}" if f else "" for f in flags], axis=0)
        st.dataframe(sty, hide_index=True, width="stretch")
        bar = st.container(horizontal=True, gap="small")
        e1, e2 = bar, bar
        export =d.drop(columns=["no"]).assign(**{c: d[c].dt.strftime("%Y-%m-%d") for c in DATES}).rename(columns=LABELS)
        e1.download_button("ดาวน์โหลด CSV", export.to_csv(index=False).encode("utf-8-sig"), "krabi_clean_data.csv", "text/csv",
                           icon=":material/download:", key="dl_csv")

        def _xlsx():
            buf = io.BytesIO()
            export.to_excel(buf, index=False, sheet_name="ข้อมูลที่คลีนแล้ว")
            return buf.getvalue()
        e2.download_button("ดาวน์โหลด Excel", _xlsx, "krabi_clean_data.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", icon=":material/download:", key="dl_xlsx")
