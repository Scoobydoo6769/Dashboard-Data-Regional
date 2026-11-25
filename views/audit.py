from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from charts import show, style_fig
from data import BASE, CHECK, DATES, FIX, LABELS, MONEY, NOTE, RAW_FILE, RENAME, _s, be_date, get_data, get_raw
from filters import data_note, pretty_table
from quality import ALIAS_, CHANGED_, FILL_, PREFIX_, SOFT_LABELS, SPACE_, STILL_LABELS, audit_rank, raw_audit
from theme import T, card_head, page_head

def _disp(v, col):
    if pd.isna(v):
        return "(ว่าง)"
    if col in DATES:
        return be_date(v) if hasattr(v, "year") else str(v)
    if col in MONEY or col in ("approved",):
        try:
            return f"{float(v):,.0f}"
        except (TypeError, ValueError):
            return str(v)
    if col in ("rate", "rate_late"):
        return f"{float(v):g}"
    if col in ("contract_id", "fy", "no") and isinstance(v, (int, float)) and float(v).is_integer():
        return str(int(v))
    return str(v).replace("\n", " ⏎ ")

PAINT_BAD = f"background-color:{T['BAD_BG']};color:{T['BAD']};font-weight:600"
PAINT_DUP = f"background-color:{T['WARN_BG']}"
PAINT_SKIP = "background-color:#EEF0F4;color:#6B7686"

def _checks_tab(df, rules, rank):
    """ตรวจซ้ำข้อมูลที่คลีนแล้ว (ชีตแรก) ด้วยกฎคุณภาพข้อมูล"""
    row_level = rank.max(axis=1)
    n_fix, n_chk = int((row_level == 3).sum()), int((row_level == 2).sum())
    n_note, n_pass = int((row_level == 1).sum()), int((row_level == 0).sum())
    src_cols = list(RENAME.values())
    miss = int(df[src_cols].isna().sum().sum())
    cells = len(df) * len(src_cols)

    st.markdown('<div class="flow">' + '<div class="sep"></div>'.join([
        f'<div class="step"><b>{len(df):,}</b><span>สัญญาในไฟล์ Excel ({len(src_cols)} คอลัมน์)</span></div>',
        f'<div class="step"><b>{1 - miss / cells:.1%}</b><span>ความสมบูรณ์ของข้อมูล (ค่าว่าง {miss:,} จาก {cells:,} ช่อง)</span></div>',
        f'<div class="step minus"><b>{n_fix:,}</b><span>แถวที่ควรแก้ไข</span></div>',
        f'<div class="step"><b>{n_chk:,}</b><span>แถวที่ควรตรวจสอบ</span></div>',
        f'<div class="step final"><b>{n_pass + n_note:,}</b><span>แถวที่ไม่พบปัญหาร้ายแรง (มีข้อสังเกต {n_note:,})</span></div>',
    ]) + "</div>", unsafe_allow_html=True)

    log = pd.DataFrame([{
        "ผลตรวจ": "ผ่าน" if not m.any() else f"พบ {int(m.sum()):,} แถว", "ระดับ": lv, "กฎที่ตรวจ": name, "จำนวนแถว": int(m.sum()),
        "% ของทั้งหมด": m.mean() * 100,
        "ตัวอย่างเลขที่สัญญา": ", ".join(df.loc[m, "contract_id"].head(3)) if m.any() else "",
        "ความหมาย / แนวทางตรวจ": note} for _, name, lv, m, _, note in rules])
    lv_order = {FIX: 0, CHECK: 1, NOTE: 2}
    log = log.assign(_k=log["จำนวนแถว"].eq(0), _l=log["ระดับ"].map(lv_order)).sort_values(["_k", "_l", "จำนวนแถว"], ascending=[True, True, False]).drop(columns=["_k", "_l"])
    with st.container(key="card_rule_table"):
        card_head("ผลการตรวจคุณภาพข้อมูล (Data Quality Checks)", "ตรวจซ้ำบนข้อมูลที่คลีนแล้ว — กฎที่ไม่พบปัญหาแสดงว่า ‘ผ่าน’")
        st.dataframe(log, hide_index=True, width="stretch", height=480, column_config={
            "จำนวนแถว": st.column_config.NumberColumn(format="%d"),
            "% ของทั้งหมด": st.column_config.NumberColumn(format="%.1f%%"),
            "ความหมาย / แนวทางตรวจ": st.column_config.TextColumn(width="large"),
            "กฎที่ตรวจ": st.column_config.TextColumn(width="large")})
        st.download_button("ดาวน์โหลดผลตรวจ (CSV)", log.to_csv(index=False).encode("utf-8-sig"), "audit_log.csv", "text/csv",
                           icon=":material/download:", key="dl_rules")
    with st.container(key="card_rule_chart"):
        found = log[log["จำนวนแถว"] > 0].sort_values("จำนวนแถว")
        card_head("กฎที่พบปัญหามากที่สุด", "จำนวนแถวที่เข้าข่ายแต่ละกฎ (สีแดง = ควรแก้ไข, ทอง = ควรตรวจสอบ, เทา = ข้อสังเกต)")
        col = {FIX: T["BAD"], CHECK: T["GOLD"], NOTE: T["SLATE"]}
        fig = go.Figure(go.Bar(x=found["จำนวนแถว"], y=found["กฎที่ตรวจ"], orientation="h",
                               marker_color=[col[v] for v in found["ระดับ"]], hovertemplate="%{y}: %{x:,} แถว<extra></extra>"))
        fig.update_yaxes(showgrid=False, automargin=True)
        show(style_fig(fig, max(220, 52 * len(found)), legend=False), "au_rule_bar")


    st.markdown('<div class="legend"><span class="bad">แดง</span> = ควรแก้ไข &nbsp; <span class="dup">ทอง</span> = ควรตรวจสอบ / ข้อสังเกต</div>',
                unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1.6, 1.4])
    only = c1.toggle("เฉพาะแถวที่มีข้อสังเกต", value=True, key="au_only")
    names = [n for _, n, _, m, _, _ in rules if m.any()]
    pick = c2.multiselect("กฎที่ต้องการดู", names, key="au_rules", placeholder="ทุกกฎ")
    q = c3.text_input("ค้นหา (เลขที่สัญญา / ชื่อโครงการ)", key="au_q")
    mask = pd.Series(True, index=df.index)
    if only:
        mask = row_level > 0
    if pick:
        mask &= pd.concat([m for _, n, _, m, _, _ in rules if n in pick], axis=1).any(axis=1)
    if q:
        mask &= df["contract_id"].str.contains(q, regex=False) | df["project"].str.contains(q, case=False, regex=False)
    view = df[mask]
    show_cols = ["contract_id", "district", "subdistrict", "fy", "project", "approved", "rate", "rate_late", "start", "end", "last",
                 "principal", "balance", "status"]
    st.caption(f"แสดง {len(view):,} จาก {len(df):,} แถว")
    css_rank = rank.loc[view.index, show_cols]

    def paint(_):
        out = pd.DataFrame("", index=view.index, columns=[LABELS[c] for c in show_cols])
        for c in show_cols:
            out.loc[css_rank[c] == 3, LABELS[c]] = f"background-color:{T['BAD_BG']};color:{T['BAD']};font-weight:600"
            out.loc[(css_rank[c] > 0) & (css_rank[c] < 3), LABELS[c]] = f"background-color:{T['WARN_BG']};font-weight:600"
        return out
    t = view[show_cols].copy()
    for c in DATES:
        t[c] = t[c].map(be_date)
    t = t.rename(columns=LABELS)
    fmt = {LABELS[c]: "{:,.0f}" for c in ("approved", "principal", "balance")} | {LABELS["rate"]: "{:g}", LABELS["rate_late"]: "{:g}"}
    st.dataframe(t.style.format(fmt, na_rep="(ว่าง)").apply(paint, axis=None), hide_index=True, width="stretch", height=500)


def _dictionary_tab(df):
    desc = {
        "no": "ลำดับในไฟล์", "district": "อำเภอของโครงการ", "subdistrict": "ตำบลของโครงการ", "fy": "ปีงบประมาณ (พ.ศ.)",
        "contract_id": "เลขที่สัญญา (ใช้เป็นรหัสโครงการ)", "project": "ชื่อโครงการ", "proposers": "รายชื่อผู้เสนอ/ผู้ร่วมโครงการ",
        "approved": "วงเงินที่อนุมัติ", "rate": "อัตราดอกเบี้ยตามสัญญา", "rate_late": "อัตราดอกเบี้ยกรณีผิดนัด",
        "start": "วันที่เริ่มต้นสัญญา (ค.ศ. ในไฟล์ แสดงผลเป็น พ.ศ.)", "end": "วันที่สิ้นสุดสัญญา", "last": "วันที่รับชำระล่าสุด",
        "principal": "เงินต้นที่ชำระแล้ว (ตีความจากข้อมูล: ปิดบัญชี = เงินอนุมัติเต็มจำนวน)", "interest": "ดอกเบี้ยโครงการที่ชำระ",
        "interest_late": "ดอกเบี้ยผิดนัดที่ชำระ", "total": "รวมที่ชำระ = เงินต้น + ดอกเบี้ยโครงการ + ดอกเบี้ยผิดนัด",
        "balance": "ยอดเงินกู้คงเหลือ", "source_sheet": "ชื่อชีตดิบต้นทาง (ตรงกับอำเภอ)", "district_file": "ชื่ออำเภอตามที่บันทึกในไฟล์ (ก่อนปรับเป็นชื่อมาตรฐานตอนโหลด)", "status_file": "สถานะโครงการตามที่บันทึกในไฟล์ (ไม่ใช้คำนวณ — ใช้สถานะตามเกณฑ์ใหม่แทน)", "district": "อำเภอ (ปรับเป็นชื่อมาตรฐานแล้ว)", "status": "สถานะตามเกณฑ์ใหม่ (คำนวณจากยอดคงเหลือและวันสิ้นสุดสัญญา)",
        "members": "จำนวนผู้ร่วมโครงการ (นับจากรายชื่อที่คั่นด้วยจุลภาค)", "category": "ประเภทโครงการ (จัดกลุ่มจากคำในชื่อโครงการ)"}
    rows = []
    for c in df.columns:
        s = df[c]
        if c in DATES:
            rng = f"{be_date(s.min())} – {be_date(s.max())}"
        elif pd.api.types.is_numeric_dtype(s) and c != "contract_id":
            rng = f"{s.min():,.4g} – {s.max():,.4g}"
        else:
            rng = ""
        rows.append({"คอลัมน์": LABELS.get(c, c), "ชนิดข้อมูล": str(s.dtype), "ค่าว่าง": int(s.isna().sum()), "ค่าไม่ซ้ำ": int(s.nunique()),
                     "ช่วงค่า": rng, "ความหมาย": desc.get(c, "")})
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch", height=520,
                 column_config={"ความหมาย": st.column_config.TextColumn(width="large")})
    st.caption("คอลัมน์ ‘ผู้ร่วมโครงการ’ และ ‘ประเภทโครงการ’ คำนวณเพิ่มโดยระบบ ส่วนที่เหลือมาจากไฟล์ Excel โดยตรง")


@st.cache_data(show_spinner="กำลังเทียบข้อมูลดิบกับข้อมูลที่คลีนแล้ว…")
def cached_raw_audit(raw: pd.DataFrame, clean: pd.DataFrame) -> dict:
    return raw_audit(raw, clean)

def _raw_summary_tab(df, ra):
    log = ra["log"]
    ok = ra["n_raw"] - ra["n_summary"] - ra["n_dup"] == len(df)
    src_cols = list(RENAME.values())
    complete = 1 - df[src_cols].isna().sum().sum() / (len(df) * len(src_cols))
    st.markdown('<div class="flow">' + '<div class="sep"></div>'.join([
        f'<div class="step"><b>{ra["n_raw"]:,}<small>แถว</small></b><span>แถวในชีตดิบ ({ra["n_sheets"]} ชีตอำเภอ)</span></div>',
        f'<div class="step minus"><b>−{ra["n_summary"]:,}<small>แถว</small></b><span>ลบแถวสรุป/แถวว่างท้ายชีต</span></div>',
        f'<div class="step minus"><b>−{ra["n_dup"]:,}<small>แถว</small></b><span>ลบแถวซ้ำ (เลขที่สัญญาซ้ำ)</span></div>',
        f'<div class="step"><b>{ra["fixed"]:,}<small>จุด</small></b><span>จุดที่ผิดหรือว่างและถูกแก้/เติมค่าแล้ว</span></div>',
        f'<div class="step final"><b>{len(df):,}</b><span>สัญญาพร้อมใช้งาน · ความสมบูรณ์ {complete:.1%}</span></div>',
    ]) + "</div>", unsafe_allow_html=True)
    if ra["still"]:
        st.warning(f"ไฟล์ที่คลีนแล้วยังเหลือ {ra['still']:,} จุดที่ไม่ตรงมาตรฐานหรือต่างจากต้นฉบับ (ดูแถวสถานะ ‘ยังไม่แก้’ / ‘ควรตรวจสอบ’ ในตารางด้านล่าง) "
                   "— ระบบปรับชื่ออำเภอให้ตอนโหลดเพื่อให้ตัวเลขรายอำเภอถูกต้อง แต่ควรแก้ที่ Power Query", icon=":material/rule:")
    if not ok:
        st.warning("จำนวนแถวหลังคลีนไม่ตรงกับแถวดิบที่ลบออก — อาจมีการลบเพิ่มที่ระบบยังไม่ได้ระบุเหตุผล", icon=":material/warning:")
    with st.container(key="card_issue_table"):
        card_head("ข้อผิดพลาดในข้อมูลดิบและวิธีทำความสะอาด (Cleansing Methodology)",
                  "เปรียบเทียบชีตดิบรายอำเภอกับชีตที่คลีนด้วย Power Query — ลบ / แก้ไข / คงไว้ ตามที่ปรากฏในข้อมูลจริง")
        st.dataframe(log, hide_index=True, width="stretch", height=430, column_config={
            "จำนวน": st.column_config.NumberColumn(format="%d"), "วิธีแก้ไข": st.column_config.TextColumn(width="large"),
            "ปัญหาที่พบในข้อมูลดิบ": st.column_config.TextColumn(width="large")})
        st.download_button("ดาวน์โหลด Audit Log (CSV)", log.to_csv(index=False).encode("utf-8-sig"), "audit_log_raw_vs_clean.csv", "text/csv",
                           icon=":material/download:", key="dl_audit_raw")
    with st.container(key="card_issue_chart"):
        g = log.sort_values("จำนวน")
        card_head("ปัญหาที่พบมากที่สุดในข้อมูลดิบ", "จำนวนแถว/จุดต่อปัญหา (แดง = ลบ, น้ำเงิน = แก้ไขแล้ว, ทอง = คงไว้/ข้อสังเกต)")
        colr = {"ลบแล้ว": T["BAD"], "แก้ไขแล้ว": T["NAVY2"]}
        fig = go.Figure(go.Bar(x=g["จำนวน"], y=g["ปัญหาที่พบในข้อมูลดิบ"].str.slice(0, 48), orientation="h",
                               marker_color=[colr.get(h, T["GOLD"]) for h in g["การจัดการ"]], hovertemplate="%{y}: %{x:,}<extra></extra>"))
        fig.update_yaxes(showgrid=False, automargin=True)
        show(style_fig(fig, max(240, 34 * len(g)), legend=False), "au_bar")

def raw_view(ra: dict, rows, cols: list[str], note=False, extra=None):
    raw, iss = ra["raw"], ra["iss"]
    names = {"sheet": "ชีตดิบ", "xl_row": "แถวใน Excel", **LABELS}
    t = pd.DataFrame({names[c]: [_disp(raw.loc[i, c], c) for i in rows] for c in cols}, index=rows)
    kind = raw.loc[rows, "kind"]
    if note:
        def _note(i):
            if kind[i] != "ข้อมูล":
                return kind[i] + " (ถูกลบ)"
            return "; ".join(f"{LABELS.get(c, c)}: {v}" for c, v in iss.loc[i].items() if v and v not in SOFT_LABELS)
        t["ปัญหาที่พบ"] = [_note(i) for i in rows]
    for k, v in (extra or {}).items():
        t[k] = [v.get(i, "") for i in rows]
    def paint(_):
        css = pd.DataFrame("", index=rows, columns=t.columns)
        for c in cols:
            if c in iss:
                css.loc[iss.loc[rows, c].map(lambda v: v != "" and v not in SOFT_LABELS), names[c]] = PAINT_BAD
                css.loc[iss.loc[rows, c].isin(SOFT_LABELS), names[c]] = PAINT_DUP
        css.loc[kind == "แถวซ้ำ", :] = PAINT_DUP
        css.loc[kind.isin(["แถวสรุป", "แถวว่าง"]), :] = PAINT_SKIP
        return css
    return t.style.apply(paint, axis=None)

def _raw_table_tab(ra):
    raw, iss = ra["raw"], ra["iss"]
    st.markdown('<div class="legend"><span class="bad">แดง</span> = จุดที่มีปัญหา (แก้ไข/คงเป็นค่าว่าง) &nbsp; '
                '<span class="dup">ทอง</span> = แถวซ้ำที่ถูกลบ หรือคอลัมน์ที่ถูกจับคู่ใหม่ &nbsp; เทา = แถวสรุป/แถวว่างที่ถูกลบ</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1.6, 1.4])
    only = c1.toggle("เฉพาะแถวที่มีปัญหา", value=True, key="au_raw_only")
    sheets = c2.multiselect("ชีตดิบ (อำเภอ)", list(dict.fromkeys(raw["sheet"])), key="au_raw_sheet", placeholder="ทุกชีต")
    q = c3.text_input("ค้นหา (เลขที่สัญญา / ชื่อโครงการ)", key="au_raw_q")
    mask = pd.Series(True, index=raw.index)
    if only:
        mask = (~iss.isin(["", *SOFT_LABELS])).any(axis=1) | (raw["kind"] != "ข้อมูล")
    if sheets:
        mask &= raw["sheet"].isin(sheets)
    if q:
        mask &= raw["contract_id"].map(_s).str.contains(q, regex=False) | raw["project"].map(_s).str.contains(q, case=False, regex=False)
    rows = raw.index[mask]
    st.caption(f"แสดง {len(rows):,} จาก {len(raw):,} แถวในชีตดิบ")
    cols = ["sheet", "xl_row", "no", "district", "subdistrict", "fy", "contract_id", "project", "approved", "last", "principal", "balance"]
    st.dataframe(raw_view(ra, rows, cols, note=True), hide_index=True, width="stretch", height=520)

def _compare_tab(df, ra):
    raw, iss = ra["raw"], ra["iss"]
    kept = raw["kept"]
    pri = [i for i in raw.index[kept] if iss.loc[i].isin(STILL_LABELS | {CHANGED_}).any()][:6]
    fix = [i for i in raw.index[kept] if i not in pri and iss.loc[i].isin({ALIAS_, PREFIX_, SPACE_, FILL_}).any()][:6]
    idx = pri + fix
    st.caption(f"ตัวอย่างแถวที่ถูกแก้ไขหรือยังมีปัญหา {len(idx)} แถว — ซ้าย = ข้อมูลดิบ, ขวา = หลังคลีน (จับคู่ด้วยชีตและเลขที่สัญญา) · {len(pri)} แถวแรกคือจุดที่ไฟล์ที่คลีนแล้วยังไม่ตรงมาตรฐานหรือต่างจากต้นฉบับ")
    ks = pd.DataFrame({"source_sheet": raw.loc[idx, "sheet"].to_numpy(), "contract_id": raw.loc[idx, "cid"].to_numpy()})
    right = ks.merge(df, on=["source_sheet", "contract_id"], how="left")
    a, b = st.columns(2)
    with a, st.container(key="card_before"):
        card_head("ก่อนคลีน (Raw)", "ข้อมูลดิบตามที่บันทึกในชีตรายอำเภอ")
        st.dataframe(raw_view(ra, idx, ["sheet", "xl_row", "contract_id", "district", "subdistrict", "project"]), hide_index=True, width="stretch")
    with b, st.container(key="card_after"):
        card_head("หลังคลีน (Cleaned)", "ไฟล์ KPI69_clean_only.xlsx (อำเภอแสดงตามที่บันทึกในไฟล์)")
        st.dataframe(pretty_table(right, ["source_sheet", "contract_id", "district_file", "subdistrict", "project"]), hide_index=True, width="stretch")
    dup = raw.index[raw["kind"] == "แถวซ้ำ"]
    cid_sheet = df.set_index("contract_id")["source_sheet"]
    where = {i: cid_sheet.get(raw.loc[i, "cid"], "") for i in dup}
    with st.container(key="card_dups"):
        card_head(f"แถวซ้ำที่ถูกลบ {len(dup):,} แถว", "เลขที่สัญญาซ้ำกับแถวอื่น — เก็บแถวที่มีข้อมูลการชำระครบไว้ ลบแถวที่เหลือ")
        st.dataframe(raw_view(ra, dup, ["sheet", "xl_row", "contract_id", "project", "principal"], extra={"เก็บสัญญานี้ไว้ที่ชีต": where}),
                     hide_index=True, width="stretch", height=360)

def page_audit():
    df, raw = get_data(), get_raw()
    page_head("ข้อมูลดิบ & Audit Log", "เทียบข้อมูลดิบรายอำเภอกับข้อมูลที่คลีนแล้ว ว่ามีข้อผิดพลาดตรงไหน แก้อย่างไร และยังเหลืออะไรให้ตรวจ")
    data_note(df)
    rules, rank = audit_rank(df)
    if raw is None:
        st.info(f"ไม่พบไฟล์ข้อมูลดิบ ({RAW_FILE.relative_to(BASE)}) จึงแสดงเฉพาะการตรวจซ้ำบนข้อมูลที่คลีนแล้ว", icon=":material/info:")
        t1, t2 = st.tabs(["ตรวจซ้ำข้อมูลที่คลีนแล้ว", "พจนานุกรมข้อมูล"])
        with t1:
            _checks_tab(df, rules, rank)
        with t2:
            _dictionary_tab(df)
        return
    ra = cached_raw_audit(raw, df)
    tabs = st.tabs(["สรุปก่อน → หลังคลีน", "ข้อมูลดิบ (ไฮไลต์จุดผิดพลาด)", "ดิบ vs สะอาด", "ตรวจซ้ำข้อมูลที่คลีนแล้ว", "พจนานุกรมข้อมูล"])
    with tabs[0]:
        _raw_summary_tab(df, ra)
    with tabs[1]:
        _raw_table_tab(ra)
    with tabs[2]:
        _compare_tab(df, ra)
    with tabs[3]:
        _checks_tab(df, rules, rank)
    with tabs[4]:
        _dictionary_tab(df)
