from __future__ import annotations

import numpy as np
import plotly.graph_objects as go
import streamlit as st
from charts import LINE_COLORS, MAP_ANCHORS, MAP_LABEL_POS, MAP_OUTSIDE, MAP_SCALE, MAP_TWEAK, gradient_colors, hex_rgb, load_map, map_data_uri, show, style_fig
from data import CLOSED, LATE_SET, SUE, as_of, baht_m, be_date, get_data
from filters import district_widget, fkey, fy_widget, in_fy, pretty_table, prev_years, reset_button
from theme import FONT, PALETTE, T, card_head, delta_pct, empty_state, insight, page_head, sk_card

def page_overview():
    df = get_data()
    head, f1, f2, f3 = st.columns([2.6, 1.4, 1.1, .7], vertical_alignment="bottom")
    with head:
        page_head("ภาพรวมสถานะการกู้ยืมเงิน กองทุนฯ จ.กระบี่",
                  f"ข้อมูล ณ วันที่ {be_date(as_of(df))} (ข้อมูลที่ผ่านการตรวจสอบแล้ว)")
    with f1:
        lo, hi = fy_widget(df)
    with f2:
        dist = district_widget(df)
    with f3:
        reset_button()
    sel = df if dist == "ทั้งจังหวัด" else df[df["district"] == dist]
    cur, prev = in_fy(sel, lo, hi), in_fy(sel, *prev_years(lo, hi))
    if cur.empty:
        empty_state()
    allp = in_fy(df, lo, hi)

    # ── ข้อค้นพบสำคัญ (ระดับจังหวัดในช่วงปีที่เลือก) 4 ข้อ
    rate = lambda d: d["principal"].sum() / d["approved"].sum() if d["approved"].sum() else 0
    by_d = allp.groupby("district")["approved"].sum().sort_values(ascending=False)
    prev_d = in_fy(df, *prev_years(lo, hi)).groupby("district")["approved"].sum()
    growth = ((by_d - prev_d) / prev_d).replace([np.inf, -np.inf], np.nan).dropna().sort_values(ascending=False)
    per_d = allp.groupby("district").agg(n=("status", "size"), late=("status", lambda s: s.isin(LATE_SET).sum()), appr=("approved", "sum"), pr=("principal", "sum"))
    per_d["p"] = per_d["late"] / per_d["n"]
    per_d["rate"] = per_d["pr"] / per_d["appr"]
    big = per_d[per_d["n"] >= 5]
    n_all, n_late_all = len(allp), int(allp["status"].isin(LATE_SET).sum())
    bal_all, bal_late = allp["balance"].sum(), allp.loc[allp["status"].isin(LATE_SET), "balance"].sum()
    ins = [insight(f"{by_d.iloc[0] / by_d.sum():.0%}", "blue", f"{by_d.index[0]}รับอนุมัติสูงสุด",
                   f"{baht_m(by_d.iloc[0])} ล้านบาท จากวงเงินทั้งจังหวัด {baht_m(by_d.sum())} ล้านบาท")]
    if len(growth):
        ins.append(insight(f"{growth.iloc[0]:+.0%}", "pos", f"{growth.index[0]}เติบโตเร็วที่สุด",
                           f"เทียบกับช่วงก่อนหน้าที่ยาวเท่ากัน (ปีงบประมาณ {prev_years(lo, hi)[0]}–{prev_years(lo, hi)[1]})"))
    else:
        ins.append(insight(f"{rate(allp):.1%}", "blue", "อัตราชำระคืนเงินต้นทั้งจังหวัด",
                           f"สูงสุด {per_d['rate'].idxmax()} {per_d['rate'].max():.1%} · ต่ำสุด {per_d['rate'].idxmin()} {per_d['rate'].min():.1%}"))
    w = big.sort_values("p", ascending=False).iloc[0] if len(big) else None
    ins.append(insight(f"{n_late_all / n_all:.1%}", "neg", "สัดส่วนโครงการเกินกำหนด",
                       f"{n_late_all:,} จาก {n_all:,} โครงการ" + (f" · สูงสุดที่{w.name} ({w['p']:.1%})" if w is not None else "")))
    n_sue = int((allp["status"] == SUE).sum())
    ins.append(insight(f"{baht_m(bal_late)}<small> ล้านบาท</small>", "neg", "ยอดคงเหลือของโครงการเกินกำหนด",
                       f"คิดเป็น {bal_late / bal_all:.0%} ของยอดคงเหลือทั้งหมด · อยู่ในขั้นดำเนินการฟ้อง {n_sue:,} โครงการ" if bal_all else ""))
    st.markdown('<div class="ins-card"><div class="ins-title">ข้อค้นพบสำคัญ</div><div class="ins-sub">สรุปจากข้อมูลจริงในช่วงที่เลือก อ่านจบใน 10 วินาที</div>'
                '<div class="ins-grid">' + "".join(ins) + "</div></div>", unsafe_allow_html=True)

    # ── กราฟแนวโน้ม (แท็บ) + การ์ดตัวชี้วัดด้านข้าง
    left, right = st.columns([2.15, 1])
    with left, st.container(key="card_trend"):
        tab = st.segmented_control("มุมมอง", ["รวม", "แยกอำเภอ", "แยกประเภท", "จำนวนโครงการ"], default="รวม", key="ov_tab", label_visibility="collapsed") or "รวม"
        g = sel.groupby("fy").agg(approved=("approved", "sum"), principal=("principal", "sum"), n=("status", "size"),
                                  late=("status", lambda s: s.isin(LATE_SET).sum()))
        x = [str(y) for y in g.index]
        if tab == "แยกอำเภอ" or tab == "แยกประเภท":
            key_col = "district" if tab == "แยกอำเภอ" else "category"
            base = df if tab == "แยกอำเภอ" else sel
            pv = base.pivot_table(index="fy", columns=key_col, values="approved", aggfunc="sum", fill_value=0)
            order = pv.sum().sort_values(ascending=False).index
            top = order[0]
            card_head(f"{top}มียอดอนุมัติรวมสูงสุด {baht_m(pv[top].sum())} ล้านบาท",
                      f"ยอดอนุมัติรายปีงบประมาณ {'แยกรายอำเภอ (ทุกอำเภอ)' if tab == 'แยกอำเภอ' else 'แยกตามประเภทโครงการ'} (ล้านบาท)")
            fig = go.Figure([go.Scatter(x=[str(y) for y in pv.index], y=pv[c] / 1e6, name=c, mode="lines+markers",
                                        line=dict(color=LINE_COLORS[i % len(LINE_COLORS)], width=2.2), marker=dict(size=5))
                             for i, c in enumerate(order)])
            fig.update_yaxes(title="ล้านบาท", rangemode="tozero")
        elif tab == "จำนวนโครงการ":
            pk = g["n"].idxmax()
            card_head(f"ปีงบประมาณ {pk} มีโครงการมากที่สุด {int(g.loc[pk, 'n']):,} โครงการ", "จำนวนโครงการรายปีงบประมาณ และส่วนที่เกินกำหนด (ผิดนัด/ไกล่เกลี่ย/ฟ้อง)")
            fig = go.Figure([go.Bar(x=x, y=g["n"], name="โครงการทั้งหมด", marker_color=T["STEEL"]),
                             go.Bar(x=x, y=g["late"], name="เกินกำหนด", marker_color=T["BAD"])])
            fig.update_layout(barmode="overlay")
            fig.update_yaxes(title="โครงการ")
        else:
            peak = g["approved"].idxmax()
            card_head(f"ปีงบประมาณ {peak} อนุมัติสูงสุด {baht_m(g.loc[peak, 'approved'])} ล้านบาท",
                      "แนวโน้มการอนุมัติเงินกู้รายปีงบประมาณ (Loan Dispersal Trend) เทียบกับเงินต้นที่ชำระแล้ว — แสดงทุกปี")
            fig = go.Figure([
                go.Scatter(x=x, y=g["approved"] / 1e6, name="เงินอนุมัติ", mode="lines+markers", line=dict(color=T["NAVY2"], width=2.5),
                           marker=dict(size=6), fill="tozeroy", fillcolor="rgba(107,148,189,.14)"),
                go.Scatter(x=x, y=g["principal"] / 1e6, name="เงินต้นที่ชำระแล้ว", mode="lines+markers",
                           line=dict(color=T["SAND"], width=2, dash="dash"), marker=dict(size=5))])
            fig.update_yaxes(title="ล้านบาท", rangemode="tozero")
        fig.update_xaxes(type="category", title="ปีงบประมาณ (พ.ศ.)")
        show(style_fig(fig, 392), "ov_trend")
    with right:
        yr = cur.groupby("fy")
        ser = lambda s: s.tail(7).tolist()
        d1 = delta_pct(cur["approved"].sum(), prev["approved"].sum(), "จากช่วงก่อน")
        d2 = delta_pct(cur["members"].sum(), prev["members"].sum(), "จากช่วงก่อน")
        n_late, n_closed = int(cur["status"].isin(LATE_SET).sum()), int((cur["status"] == CLOSED).sum())
        pts = (rate(cur) - rate(prev)) * 100 if len(prev) else None
        d4 = ("ไม่มีช่วงก่อนหน้า", "flat", "flat") if pts is None else (
            f"{pts:+.1f} จุด จากช่วงก่อน", "flat" if abs(pts) < .05 else ("good" if pts > 0 else "bad"), "up" if pts >= 0 else "down")
        d1 = (d1[0].replace("ไม่มีช่วงก่อนหน้าให้เทียบ", "ไม่มีช่วงก่อนหน้า"),) + d1[1:]
        d2 = (d2[0].replace("ไม่มีช่วงก่อนหน้าให้เทียบ", "ไม่มีช่วงก่อนหน้า"),) + d2[1:]
        st.markdown('<div class="sk-col">' + "".join([
            sk_card("ยอดอนุมัติรวม", baht_m(cur["approved"].sum()), "ล้านบาท", *d1, ser(yr["approved"].sum())),
            sk_card("จำนวนสมาชิกที่ได้รับอนุมัติ", f"{cur['members'].sum():,.0f}", "ราย", *d2, ser(yr["members"].sum())),
            sk_card("สถานะโครงการ", f"{len(cur):,}", "โครงการ", f"เกินกำหนด {n_late:,} · ปิด {n_closed:,}", "bad" if n_late else "good", "flat", ser(yr.size())),
            sk_card("อัตราการชำระคืนเงินต้น", f"{rate(cur):.1%}", "", *d4, ser(yr["principal"].sum() / yr["approved"].sum())),
        ]) + "</div>", unsafe_allow_html=True)

    # ── เปรียบเทียบอำเภอ (คลิกแท่งเพื่อกรอง) + สัดส่วนประเภทโครงการ
    c2, c3 = st.columns([1.25, 1])
    with c2, st.container(key="card_bar"):
        card_head(f"{by_d.index[0]}นำทุกอำเภอ ด้วยยอดอนุมัติ {baht_m(by_d.iloc[0])} ล้านบาท",
                  "แผนที่ผลการดำเนินงานตามอำเภอ (ยอดอนุมัติ) — ยิ่งสีเข้ม ยอดยิ่งมาก · คลิกอำเภอเพื่อกรองทั้งหน้า")
        names = list(MAP_ANCHORS)
        vals = np.array([float(by_d.get(n, 0.0)) for n in names])
        colors = dict(zip(names, gradient_colors(vals)))            # น้อยสุด = อ่อนสุด → มากสุด = เข้มสุด
        fade = {n: (1.0 if dist in ("ทั้งจังหวัด", n) else .35) for n in names}   # เมื่อเลือกอำเภอ พื้นที่อื่นจางลง
        map_key = f"ov_map_{dist}"
        def _pick():
            pts = st.session_state[map_key]["selection"]["points"]
            if pts:
                y = names[pts[0]["point_index"]]
                new = "ทั้งจังหวัด" if y == st.session_state.get("district_sel") else y
                st.session_state["district_sel"] = new
                st.session_state[fkey("w_district")] = new
        W2, H2 = load_map()["size"]
        lum = lambda h: float(hex_rgb(h) @ np.array([.299, .587, .114]))
        txt_color = ["#16202E" if (n in MAP_OUTSIDE or lum(colors[n]) > 150) else "#FFFFFF" for n in names]
        spots, avail = {}, {}
        for n in names:
            lx, ly, aw = load_map()["labels"][n]
            dx, dy, _ = MAP_TWEAK.get(n, (0, 0, 0))
            spots[n] = MAP_LABEL_POS[n] if n in MAP_OUTSIDE else (lx + dx, ly + dy)
            avail[n] = 90 if n in MAP_OUTSIDE else aw
        thai_chars = lambda t: sum(1 for c in t if c not in "ัิีึืุู็่้๊๋์ํ")
        # ขนาดตัวอักษรพอดีความกว้างพื้นที่ (กว้างตัวอักษรไทย ≈ 0.52 ของขนาดฟอนต์; ตัวเลขแบบ 15.8M ≈ 5 ตัว) ไม่เล็กกว่า 10 ไม่ใหญ่กว่า 15
        font_px = [max(9.0, float(np.clip(avail[n] * .92 / max(.52 * thai_chars(n), .58 * 5), 10, 15)) + MAP_TWEAK.get(n, (0, 0, 0))[2]) for n in names]
        font_px[names.index("เกาะลันตา")] = 11.0
        fig = go.Figure()
        fig.add_layout_image(dict(source=map_data_uri(colors, fade), xref="x", yref="y", x=0, y=0, sizex=W2, sizey=H2,
                                  sizing="stretch", layer="below"))
        fig.add_trace(go.Scatter(
            x=[spots[n][0] * MAP_SCALE for n in names], y=[spots[n][1] * MAP_SCALE for n in names], mode="markers+text",
            text=[f"<b>{n}</b><br>{v / 1e6:.1f}M" for n, v in zip(names, vals)], textposition="middle center",
            textfont=dict(color=txt_color, size=font_px, family=FONT), marker=dict(size=64, color="rgba(0,0,0,0)"), customdata=vals,
            hovertemplate="%{text}<br>%{customdata:,.0f} บาท<extra></extra>", showlegend=False))
        fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers", showlegend=False, hoverinfo="skip", marker=dict(
            colorscale=[[0, "#CFDDF0"], [1, "#14264A"]], cmin=vals.min() / 1e6, cmax=vals.max() / 1e6, showscale=True,
            colorbar=dict(title=dict(text="ล้านบาท (M)", side="right"), thickness=12, len=.55, y=.5, tickformat=".0f", ticksuffix="M"))))
        fig.update_xaxes(range=[0, W2], visible=False, fixedrange=True)
        fig.update_yaxes(range=[H2, 0], visible=False, scaleanchor="x", fixedrange=True)
        style_fig(fig, 560, legend=False)
        fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), clickmode="event+select", dragmode="zoom")   # แกนล็อกไว้ จึงไม่ซูม แต่คลิกเลือกได้
        show(fig, map_key, on_select=_pick, selection_mode="points")
    with c3, st.container(key="card_pie"):
        by_b = cur.groupby("category")["approved"].sum().sort_values(ascending=False)
        card_head(f"{by_b.index[0]}เป็นประเภทโครงการหลัก {by_b.iloc[0] / by_b.sum():.0%} ของยอดอนุมัติ",
                  "โครงการแบ่งตามประเภท (จัดกลุ่มจากคำในชื่อโครงการ)")
        fig = go.Figure(go.Pie(labels=by_b.index, values=by_b.values, hole=.58, sort=False, marker_colors=PALETTE[:len(by_b)],
                               marker_line=dict(color="#fff", width=2), textinfo="percent", textposition="inside",
                               textfont=dict(color="#fff", size=13),
                               hovertemplate="%{label}: %{value:,.0f} บาท (%{percent})<extra></extra>"))
        style_fig(fig, 340)
        fig.update_layout(legend=dict(orientation="h", y=-0.05, x=0.5, xanchor="center", yanchor="top"))
        show(fig, "ov_pie")

    # เงินอนุมัติ vs ยอดคงเหลือ รายอำเภอ (ระดับจังหวัดในช่วงปีที่เลือก)
    with st.container(key="card_dist_money"):
        gm = allp.groupby("district")[["approved", "balance"]].sum().sort_values("approved", ascending=False)  # เรียงตามเงินอนุมัติ มาก → น้อย
        gap = (gm["balance"] / gm["approved"]).idxmax()
        card_head(f"{gap}มียอดคงเหลือสูงสุดเมื่อเทียบกับเงินอนุมัติ ({gm.loc[gap, 'balance'] / gm.loc[gap, 'approved']:.0%})",
                  "เงินอนุมัติ vs ยอดเงินคงเหลือ แยกรายอำเภอ (หน่วย M = ล้านบาท) — ตามช่วงปีงบประมาณที่เลือก")
        top = max(16_000_000, int(np.ceil(gm.to_numpy().max() / 2e6)) * 2_000_000)
        ticks = list(range(0, top + 1, 2_000_000))
        fig = go.Figure([
            go.Bar(x=gm.index, y=gm["approved"], name="เงินอนุมัติ", text=[f"{v / 1e6:.1f}M" for v in gm["approved"]], textposition="outside", textfont=dict(size=11), cliponaxis=False, marker_color=T["NAVY2"],
                   hovertemplate="%{x} · เงินอนุมัติ: %{y:,.0f} บาท<extra></extra>"),
            go.Bar(x=gm.index, y=gm["balance"], name="ยอดเงินคงเหลือ", text=[f"{v / 1e6:.1f}M" for v in gm["balance"]], textposition="outside", textfont=dict(size=11), cliponaxis=False, marker_color=T["SAND"],
                   hovertemplate="%{x} · ยอดเงินคงเหลือ: %{y:,.0f} บาท<extra></extra>")])
        fig.update_layout(barmode="group", bargap=.25, bargroupgap=.06)
        fig.update_xaxes(title=dict(text="อำเภอ", standoff=10), type="category")
        fig.update_yaxes(title=dict(text="จำนวนเงิน (บาท)", standoff=10), range=[0, top], tickvals=ticks,
                         ticktext=[f"{t // 1_000_000}M" for t in ticks])
        show(style_fig(fig, 360), "ov_money")

    with st.container(key="card_table"):
        card_head("รายการรับชำระเงินกู้ล่าสุด", f"การชำระเงินกู้ (Loan Repayment) — แสดง 8 จาก {len(cur):,} โครงการในช่วงที่เลือก")
        tbl = cur.sort_values("last", ascending=False).head(8)
        st.dataframe(pretty_table(tbl, ["last", "district", "project", "approved", "principal", "balance", "status"]),
                     hide_index=True, width="stretch")
        st.caption("ดูและส่งออกข้อมูลทั้งหมดได้ที่เมนู ‘สำรวจข้อมูลเชิงลึก’")
