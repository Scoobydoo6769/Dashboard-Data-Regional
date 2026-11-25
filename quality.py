"""Raw-vs-clean audit logic (no UI)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import re
from data import CHECK, DISTRICTS, FIX, LABELS, NOTE, RAW_KEYS, _norm_dist, _s, quality_rules

def audit_rank(df: pd.DataFrame):
    """rank รายเซลล์: 0 = ปกติ, 1 = ข้อสังเกต, 2 = ควรตรวจสอบ, 3 = ควรแก้ไข"""
    rules = quality_rules(df)
    order = {NOTE: 1, CHECK: 2, FIX: 3}
    rank = pd.DataFrame(0, index=df.index, columns=df.columns)
    for _, _, lv, mask, cols, _ in rules:
        for c in cols:
            rank.loc[mask, c] = np.maximum(rank.loc[mask, c], order[lv])
    return rules, rank

# ── ตรวจเทียบข้อมูลดิบ (ชีตรายอำเภอ) กับข้อมูลที่คลีนแล้ว (ไฟล์ KPI69_clean_only.xlsx)
(BLANK_, FILL_, ALIAS_, ALIAS_STILL_, PREFIX_, PREFIX_STILL_, SPACE_, SPACE_STILL_, CHANGED_, NEWLINE_, ALIASCOL_, TEXTNUM_, FLOATID_, UNREAD_) = (
    "ค่าว่าง", "ค่าว่างถูกเติมค่า", "ชื่อไม่ตรงมาตรฐาน", "ชื่อไม่ตรงมาตรฐาน (ยังเหลือในไฟล์ที่คลีน)", "มีคำนำหน้า", "มีคำนำหน้า (ยังเหลือในไฟล์ที่คลีน)",
    "มีช่องว่างซ้ำ", "มีช่องว่างซ้ำ (ยังเหลือในไฟล์ที่คลีน)", "ค่าถูกเปลี่ยนจากต้นฉบับ", "ขึ้นบรรทัดใหม่ในช่อง", "ชื่อคอลัมน์ต่างจากชีตอื่น",
    "ปีเก็บเป็นข้อความ", "เลขที่สัญญาเป็นทศนิยม", "อ่านค่าไม่ได้")
SOFT_LABELS = {NEWLINE_, ALIASCOL_}   # ความต่างของรูปแบบที่พบทุกแถว ไม่นับเป็นข้อผิดพลาด
STILL_LABELS = {ALIAS_STILL_, PREFIX_STILL_, SPACE_STILL_, UNREAD_}
FIXED_LABELS = {ALIAS_, PREFIX_, SPACE_, FILL_, TEXTNUM_, FLOATID_, NEWLINE_, ALIASCOL_}
COUNT_FIXED = {ALIAS_, PREFIX_, SPACE_, FILL_, TEXTNUM_, FLOATID_}   # นับเป็น ‘จุดที่ผิดและถูกแก้’
LABEL_METHOD = {
    BLANK_: "ไม่มีข้อมูลในต้นฉบับ คงเป็นค่าว่าง (ควรเติมจากเอกสารสัญญา)",
    FILL_: "ไฟล์ที่คลีนเติมค่าแทนค่าว่าง (เช่น ตำบล = ‘ไม่ระบุ’, ดอกเบี้ย 0.1 / 5, ยอดเงิน 0)",
    ALIAS_: "ตัดคำนำหน้า ‘อ.’/‘อำเภอ’ และแปลงชื่อย่อ (เช่น ‘เมือง’) เป็นชื่ออำเภอมาตรฐาน",
    ALIAS_STILL_: "ไฟล์ที่คลีนแล้วยังไม่แก้ — ระบบปรับเป็นชื่อมาตรฐานให้ตอนโหลดเพื่อให้รวมกลุ่มถูกต้อง แต่ควรแก้ที่ Power Query",
    PREFIX_: "ตัดคำว่า ‘ตำบล’/‘ต.’ ออก ให้เหลือเฉพาะชื่อตำบล",
    PREFIX_STILL_: "ไฟล์ที่คลีนแล้วยังมีคำนำหน้า — ควรแก้ที่ Power Query",
    SPACE_: "ตัดช่องว่างซ้ำให้เหลือช่องเดียว",
    SPACE_STILL_: "ไฟล์ที่คลีนแล้วยังมีช่องว่างซ้ำ — ควรแก้ที่ Power Query",
    CHANGED_: "ค่าในไฟล์ที่คลีนแล้วต่างจากต้นฉบับ ควรตรวจว่าตั้งใจแก้หรือไม่ (เช่น ‘ไสไทย’ → ‘ไสไทยย’ อาจเกิดจากการแทนที่ค่าซ้ำซ้อน)",
    NEWLINE_: "รวมรายชื่อที่คั่นด้วยการขึ้นบรรทัดใหม่ให้เป็นบรรทัดเดียว คั่นด้วยจุลภาค",
    ALIASCOL_: "จับคู่คอลัมน์ ‘รับคืนเงินต้น/ดอกเบี้ย/เบี้ยปรับ/รวม/เงินต้นคงเหลือ’ เข้ากับคอลัมน์มาตรฐาน",
    TEXTNUM_: "แปลงปีงบประมาณจากข้อความเป็นตัวเลข",
    FLOATID_: "แปลงเลขที่สัญญาจากทศนิยมเป็นจำนวนเต็ม",
    UNREAD_: "ไม่อยู่ในรายชื่ออำเภอ ต้องตรวจด้วยตนเอง",
}
HANDLING_ORDER = {"ลบแล้ว": 0, "แก้ไขแล้ว": 1, "ควรตรวจสอบ": 2, "ยังไม่แก้": 3, "คงไว้ (ค่าว่าง)": 4, "ข้อสังเกต": 5}

def _cid(v) -> str:
    try:
        return str(int(float(v)))
    except (TypeError, ValueError):
        return "" if pd.isna(v) else str(v).strip()

def _ws(v) -> str:
    return "" if pd.isna(v) else re.sub(r"\s+", " ", str(v).replace("\n", ", ")).strip()

def raw_audit(raw: pd.DataFrame, clean: pd.DataFrame) -> dict:
    no = pd.to_numeric(raw["no"], errors="coerce")
    blank = raw[RAW_KEYS].isna().all(axis=1)
    kind = pd.Series("ข้อมูล", index=raw.index)
    kind[no.isna() & blank] = "แถวว่าง"
    kind[no.isna() & ~blank] = "แถวสรุป"
    cid = raw["contract_id"].map(_cid)
    keys = set(zip(clean["source_sheet"], clean["contract_id"]))
    cand = (kind == "ข้อมูล") & pd.Series([(a, b) in keys for a, b in zip(raw["sheet"], cid)], index=raw.index)
    first = ~pd.DataFrame({"s": raw["sheet"], "c": cid})[cand].duplicated(keep="first")
    kept = pd.Series(False, index=raw.index)
    kept[cand] = first.to_numpy()
    kind[(kind == "ข้อมูล") & ~kept] = "แถวซ้ำ"
    # ค่าที่ตรงกันในไฟล์ที่คลีนแล้ว (จับคู่ด้วยชีต + เลขที่สัญญา)
    cl = pd.DataFrame({"source_sheet": raw["sheet"].to_numpy(), "contract_id": cid.to_numpy()}).merge(
        clean.drop_duplicates(["source_sheet", "contract_id"]), on=["source_sheet", "contract_id"], how="left").set_axis(raw.index)

    iss = pd.DataFrame("", index=raw.index, columns=RAW_KEYS)
    def put(col, mask, label):
        iss.loc[mask & kept, col] = label
    txt = lambda c: raw[c].map(lambda v: "" if pd.isna(v) else str(v))
    # ช่องว่าง: ถ้าไฟล์ที่คลีนมีค่าแล้ว = ถูกเติม
    for c in ["subdistrict", "rate", "rate_late", "last", "principal", "interest", "interest_late", "total", "balance"]:
        put(c, raw[c].isna() & cl[c].isna(), BLANK_)
        put(c, raw[c].isna() & cl[c].notna(), FILL_)
    d = txt("district")
    ok_d = d.str.strip().isin(DISTRICTS) & (d == d.str.strip())
    nd = d.map(_norm_dist)
    put("district", d.str.strip() == "", BLANK_)
    put("district", (d.str.strip() != "") & ~ok_d & nd.notna() & (cl["district_file"] == nd), ALIAS_)
    put("district", (d.str.strip() != "") & ~ok_d & nd.notna() & (cl["district_file"] != nd), ALIAS_STILL_)
    put("district", (d.str.strip() != "") & ~ok_d & nd.isna(), UNREAD_)
    sub, csub = txt("subdistrict"), cl["subdistrict"].map(lambda v: "" if pd.isna(v) else str(v))
    pref = lambda s: s.str.match(r"^(ตำบล|ต\.)")
    put("subdistrict", pref(sub) & ~pref(csub), PREFIX_)
    put("subdistrict", pref(sub) & pref(csub), PREFIX_STILL_)
    strip_pref = sub.str.replace(r"^(ตำบล|ต\.)\s*", "", regex=True).str.strip()
    put("subdistrict", (sub.str.strip() != "") & ~pref(sub) & cl["subdistrict"].notna() & (strip_pref != csub.str.strip()), CHANGED_)
    put("proposers", txt("proposers").str.contains("\n"), NEWLINE_)
    for c in ("project", "proposers"):
        r, cc = raw[c].map(_s), cl[c].map(_s)
        dbl = r.str.contains(r"[ \t]{2,}")
        put(c, dbl & ~cc.str.contains(r"[ \t]{2,}"), SPACE_)
        put(c, dbl & cc.str.contains(r"[ \t]{2,}"), SPACE_STILL_)
        put(c, ~dbl & cl[c].notna() & (r.map(_ws) != cc.map(_ws)), CHANGED_)
    for c in ("principal", "interest", "interest_late", "total", "balance"):
        put(c, raw["alias_cols"].astype(bool) & raw[c].notna(), ALIASCOL_)
    put("fy", raw["fy"].map(lambda v: isinstance(v, str)), TEXTNUM_)
    put("contract_id", raw["contract_id"].map(lambda v: isinstance(v, float) and pd.notna(v)), FLOATID_)

    rows = []
    def add(where, problem, n, handling, method, ex=""):
        if n:
            rows.append({"ตำแหน่ง": where, "ปัญหาที่พบในข้อมูลดิบ": problem, "จำนวน": int(n), "การจัดการ": handling, "วิธีแก้ไข": method, "ตัวอย่างค่าดิบ": ex})
    summ, blk, dup = raw[kind == "แถวสรุป"], raw[kind == "แถวว่าง"], raw[kind == "แถวซ้ำ"]
    add("ทั้งแถว", "แถวสรุป (‘ภาพรวมอำเภอ/จังหวัด’) ท้ายชีต", len(summ), "ลบแล้ว", "ลบออก เพราะไม่ใช่ข้อมูลสัญญาและจะทำให้ยอดรวมซ้ำ", " | ".join(summ["no"].astype(str).head(2)))
    add("ทั้งแถว", "แถวว่างท้ายชีต", len(blk), "ลบแล้ว", "ลบออก", "(แถวว่าง)")
    add("ทั้งแถว", "แถวซ้ำ (เลขที่สัญญาซ้ำกับแถวอื่น)", len(dup), "ลบแล้ว", "เก็บแถวที่มีข้อมูลการชำระครบ ลบแถวที่ซ้ำ",
        ", ".join(f"{k} {v}" for k, v in dup["sheet"].value_counts().head(3).items()))
    add("หัวคอลัมน์", "หัวคอลัมน์ ‘ผู้เสนอโครงการ/ผู้ร่วมโครงการ’ มีการขึ้นบรรทัดใหม่", raw.loc[raw["raw_header_newline"].astype(bool), "sheet"].nunique(),
        "แก้ไขแล้ว", "ปรับชื่อหัวคอลัมน์ให้ตรงกันทุกชีต (นับเป็นจำนวนชีต)", "ผู้เสนอโครงการ/⏎ผู้ร่วมโครงการ")
    for col in RAW_KEYS:
        for label, n in iss[col][iss[col] != ""].value_counts().items():
            if label == ALIASCOL_:
                continue
            idx = iss.index[iss[col] == label][:2]
            def show_(i):
                a = raw.loc[i, col]
                a = "(ว่าง)" if pd.isna(a) else str(a).replace("\n", " ⏎ ")[:30]
                if label in (FILL_, ALIAS_, ALIAS_STILL_, PREFIX_, CHANGED_, SPACE_):
                    b = cl.loc[i, "district_file" if col == "district" else col]
                    return f"{a} → {'(ว่าง)' if pd.isna(b) else str(b)[:30]}"
                return a
            handling = ("แก้ไขแล้ว" if label in FIXED_LABELS else "ยังไม่แก้" if label in STILL_LABELS else
                        "ควรตรวจสอบ" if label == CHANGED_ else "คงไว้ (ค่าว่าง)")
            add(LABELS.get(col, col), label, n, handling, LABEL_METHOD[label], " | ".join(show_(i) for i in idx))
    n_alias_rows = int((kept & raw["alias_cols"].astype(bool)).sum())
    add("เงินต้น, ดอกเบี้ย, รวม, คงเหลือ", "ชีตเกาะลันตาตั้งชื่อคอลัมน์การเงินต่างจากชีตอื่น (5 คอลัมน์) และมีหัวข้อ ‘เงินต้นคงเหลือ ณ 30 ก.ย. 2568’",
        n_alias_rows, "แก้ไขแล้ว", LABEL_METHOD[ALIASCOL_], "รับคืนเงินต้น → เงินต้น")
    add("คงเหลือ", "ยอดคงเหลือของชีตเกาะลันตาอ้างอิง ณ 30 ก.ย. 2568 ซึ่งต่างจากวันที่ข้อมูลล่าสุดของชีตอื่น", n_alias_rows, "ข้อสังเกต",
        "ยังไม่ปรับยอด ควรยืนยันวันที่อ้างอิงกับเจ้าของข้อมูล", "")
    log = pd.DataFrame(rows)
    log = log.assign(_o=log["การจัดการ"].map(HANDLING_ORDER)).sort_values(["_o", "จำนวน"], ascending=[True, False]).drop(columns="_o").reset_index(drop=True)
    fixed_cells = int(iss.isin(COUNT_FIXED).to_numpy().sum())
    still_cells = int(iss.isin(STILL_LABELS | {CHANGED_}).to_numpy().sum())
    return dict(raw=raw.assign(kind=kind, kept=kept, cid=cid), iss=iss, log=log, n_raw=len(raw), n_sheets=raw["sheet"].nunique(),
                n_summary=len(summ) + len(blk), n_dup=len(dup), fixed=fixed_cells, still=still_cells)
