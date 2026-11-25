"""Data layer: schema, loading, status rules, quality rules."""
from __future__ import annotations

import numpy as np
import pandas as pd
import re
import streamlit as st
from pathlib import Path

# ─────────────────────────────── ค่าคงที่ / schema ───────────────────────────────
BASE = Path(__file__).parent
DATA_FILE = BASE / "data" / "KPI69_clean_only.xlsx"
RAW_FILE = BASE / "data" / "KPI69_raw_sheets.xlsx"

# หัวคอลัมน์ในไฟล์ Excel -> ชื่อที่ใช้ในโค้ด
RENAME = {
    "ลำดับ": "no", "อำเภอ/เขต": "district", "ตำบล": "subdistrict", "ปีงบประมาณ": "fy", "เลขที่สัญญา": "contract_id",
    "ชื่อโครงการ": "project", "ผู้เสนอโครงการ/ผู้ร่วมโครงการ": "proposers", "เงินอนุมัติ": "approved",
    "อัตราดอกเบี้ยตามสัญญา (ร้อยละ)": "rate", "อัตราดอกเบี้ยผิดนัด (ร้อยละ)": "rate_late",
    "วันที่เริ่มต้นสัญญา": "start", "วันที่สิ้นสุดสัญญา": "end", "วันที่รับชำระล่าสุด": "last",
    "เงินต้น": "principal", "ดอกเบี้ยโครงการ": "interest", "ดอกเบี้ยผิดนัด": "interest_late", "รวม": "total",
    "ยอดเงินคงเหลือ": "balance", "ชีตต้นทาง": "source_sheet",
}
# หัวคอลัมน์ทางเลือก (ไม่บังคับต้องมี)
RENAME_ALT = {"ชื่อชีตต้นทาง": "source_sheet", "สถานะโครงการ": "status_file"}
# ชีตดิบของบางอำเภอ (เกาะลันตา) ตั้งชื่อคอลัมน์การเงินต่างจากชีตอื่น
RAW_ALIASES = {"รับคืนเงินต้น": "principal", "รับคืนดอกเบี้ย": "interest", "รับคืนเบี้ยปรับ": "interest_late",
               "รับคืนรวม": "total", "เงินต้นคงเหลือ ณ 30 ก.ย. 2568": "balance"}
RAW_KEYS = [v for v in RENAME.values() if v != "source_sheet"]
LABELS = {
    "no": "ลำดับ", "district": "อำเภอ", "district_file": "อำเภอ (ตามไฟล์)", "status_file": "สถานะเดิมในไฟล์", "subdistrict": "ตำบล", "fy": "ปีงบประมาณ", "contract_id": "เลขที่สัญญา",
    "project": "ชื่อโครงการ", "proposers": "ผู้เสนอโครงการ", "approved": "เงินอนุมัติ (บาท)", "rate": "ดอกเบี้ยตามสัญญา (%)",
    "rate_late": "ดอกเบี้ยผิดนัด (%)", "start": "วันที่เริ่มสัญญา", "end": "วันที่สิ้นสุดสัญญา", "last": "รับชำระล่าสุด",
    "principal": "เงินต้นที่ชำระ (บาท)", "interest": "ดอกเบี้ยโครงการ (บาท)", "interest_late": "ดอกเบี้ยผิดนัด (บาท)",
    "total": "รวมที่ชำระ (บาท)", "balance": "คงเหลือ (บาท)", "source_sheet": "ชื่อชีตต้นทาง", "status": "สถานะ",
    "members": "ผู้ร่วมโครงการ (ราย)", "category": "ประเภทโครงการ",
}
MONEY = ["approved", "principal", "interest", "interest_late", "total", "balance"]
DATES = ["start", "end", "last"]
# สถานะตามเกณฑ์ (คำนวณจากยอดคงเหลือและวันสิ้นสุดสัญญา) — ใช้ทุกหน้า
CLOSED, RUN, DEFAULT, MEDIATE, SUE = "ปิดโครงการ", "ดำเนินโครงการอยู่", "ผิดนัดชำระ", "ไกล่เกลี่ย", "ดำเนินการฟ้อง"
LATE_SET = (DEFAULT, MEDIATE, SUE)           # กลุ่มที่สิ้นสุดสัญญาแล้วแต่ยังมียอดค้าง
STATUSES = [RUN, CLOSED, DEFAULT, MEDIATE, SUE]
CLOSE_TOL = 0.05                              # ยอดคงเหลือไม่เกิน 5% ของเงินต้น (เงินอนุมัติ) ถือว่าชำระแล้ว
DISTRICTS = ["เมืองกระบี่", "อ่าวลึก", "เขาพนม", "คลองท่อม", "เกาะลันตา", "ปลายพระยา", "ลำทับ", "เหนือคลอง"]
TH_ABBR = ["ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.", "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค."]

# จัดประเภทโครงการจากคำในชื่อโครงการ (ไฟล์ไม่มีคอลัมน์ประเภทธุรกิจ) — เรียงตามลำดับความสำคัญ แก้คำได้ที่นี่
CATEGORY_RULES = [
    ("ท่องเที่ยว", ["ท่องเที่ยว", "โฮมสเตย์", "ที่พัก", "รีสอร์ท", "ดำน้ำ", "ล่องเรือ"]),
    ("แปรรูป/หัตถกรรม", ["แปรรูป", "มัดย้อม", "บาติก", "ผ้า", "เย็บ", "ทอ", "จักสาน", "หมอน", "ไม้กวาด", "ผลิตภัณฑ์", "ผลิต", "น้ำพริก", "เครื่องแกง", "ขนม"]),
    ("ค้าขาย/บริการ", ["ร้าน", "ค้าขาย", "ค้า", "อาหาร", "ข้าวแกง", "ซัก", "เสริมสวย", "นวด", "บริการ", "ขายของ", "ขาย", "รับซื้อ", "ซื้อ", "คาเฟ่", "ครัว", "เช่า", "เต้นท์", "โต๊ะจีน", "ตลาด"]),
    ("เกษตรกรรม", ["ปลูก", "เลี้ยง", "เพาะ", "ฟาร์ม", "ปศุสัตว์", "สุกร", "หมู", "วัว", "โค", "แพะ", "ไก่", "เป็ด", "ปลา", "กุ้ง", "ปู", "ยาง", "ปาล์ม", "สวน", "ผัก", "เห็ด", "ไส้เดือน", "จิ้งหรีด", "เกษตร", "ถั่ว", "สับปะรด", "พริก", "กล้วย", "สาหร่าย", "แปลง", "ข้าว"]),
]
CATEGORIES = [c for c, _ in CATEGORY_RULES] + ["อื่นๆ"]

# ─────────────────────────────── ตัวช่วย ───────────────────────────────
def _s(x) -> str:
    return "" if pd.isna(x) else str(x)

def _norm_dist(x):
    """ชื่ออำเภอมาตรฐาน หรือ None ถ้าอ่านไม่ได้ (รองรับ ‘อ.’, ‘อำเภอ’ และ ‘เมือง’)"""
    if pd.isna(x):
        return None
    t = re.sub(r"^(อำเภอ|อ\.)\s*", "", str(x).strip())
    if t in DISTRICTS:
        return t
    return "เมืองกระบี่" if t == "เมือง" else None

def be_date(d) -> str:
    return "-" if pd.isna(d) else f"{d.day:02d}/{d.month:02d}/{d.year + 543}"

def classify(name: str) -> str:
    for cat, words in CATEGORY_RULES:
        if any(w in name for w in words):
            return cat
    return "อื่นๆ"

def baht_m(x: float) -> str:
    return f"{x / 1e6:,.1f}"

def derive_status(df: pd.DataFrame, cut: pd.Timestamp) -> pd.Series:
    """สถานะตามเกณฑ์:
    ปิดโครงการ    = ชำระแล้ว (คงเหลือ ≤ 5% ของเงินต้น)
    ดำเนินโครงการอยู่ = ยังไม่สิ้นสุดสัญญา
    ผิดนัดชำระ    = สิ้นสุดสัญญาไม่เกิน 1 ปี และคงเหลือ > 5%
    ไกล่เกลี่ย     = สิ้นสุดสัญญา 1–2 ปี และคงเหลือ > 5%
    ดำเนินการฟ้อง  = สิ้นสุดสัญญาเกิน 2 ปี และคงเหลือ > 5%   (นับถึงวันที่ข้อมูลล่าสุด)"""
    paid = df["balance"] <= df["approved"] * CLOSE_TOL
    ended = df["end"] <= cut
    out = np.select(
        [paid, ~ended, df["end"] + pd.DateOffset(years=1) >= cut, df["end"] + pd.DateOffset(years=2) >= cut],
        [CLOSED, RUN, DEFAULT, MEDIATE], default=SUE)
    return pd.Series(out, index=df.index)

# ─────────────────────────────── โหลดข้อมูลจริง ───────────────────────────────
def _hdr(c) -> str:
    """ทำหัวคอลัมน์ให้เป็นรูปแบบเดียวกัน (ตัดการขึ้นบรรทัดใหม่/ช่องว่างเกิน)"""
    return re.sub(r"\s+", " ", str(c).replace("/\n", "/")).strip()

@st.cache_data(show_spinner="กำลังโหลดข้อมูล…")
def load_data(mtime: float) -> pd.DataFrame:
    df = pd.read_excel(DATA_FILE, sheet_name=0)        # ชีตแรก = ข้อมูลที่คลีนแล้ว
    df.columns = [_hdr(c) for c in df.columns]
    df = df.rename(columns=RENAME_ALT)
    if "source_sheet" in df.columns and "ชีตต้นทาง" in df.columns:
        df = df.drop(columns="ชีตต้นทาง")
    missing = [c for c in RENAME if c not in df.columns and RENAME[c] not in df.columns]
    if missing:
        raise ValueError("ไฟล์ Excel ขาดคอลัมน์: " + ", ".join(missing))
    df = df.rename(columns=RENAME)
    keep = list(RENAME.values()) + (["status_file"] if "status_file" in df.columns else [])
    df = df[keep]
    df["contract_id"] = df["contract_id"].astype(str)
    for c in DATES:
        df[c] = pd.to_datetime(df[c], errors="coerce")
    df["district_file"] = df["district"]                # ค่าตามที่บันทึกในไฟล์ (ใช้ตรวจ Audit)
    df["district"] = [_norm_dist(v) or v for v in df["district_file"]]   # ปรับเป็นชื่ออำเภอมาตรฐานเพื่อให้รวมกลุ่มถูกต้อง
    df["status"] = derive_status(df, df["last"].max())
    df["members"] = df["proposers"].fillna("").map(lambda s: len([p for p in s.split(",") if p.strip()]))
    df["category"] = df["project"].fillna("").map(classify)
    return df

@st.cache_data(show_spinner="กำลังโหลดข้อมูลดิบ…")
def load_raw(mtime: float) -> pd.DataFrame:
    """ชีตที่ 2 เป็นต้นไป = ข้อมูลดิบรายอำเภอ รวมเป็นตารางเดียว (คงค่าตามต้นฉบับ ไม่แก้ไข)"""
    sheets = pd.read_excel(RAW_FILE, sheet_name=None, dtype=object)
    frames = []
    for name, d in list(sheets.items())[1:]:
        orig = [_hdr(c) for c in d.columns]
        d.columns = [RAW_ALIASES.get(c, RENAME.get(c, c)) for c in orig]
        d = d.loc[:, ~d.columns.duplicated()]
        d.insert(0, "sheet", name)
        d.insert(1, "xl_row", range(2, len(d) + 2))
        d["alias_cols"] = any(c in RAW_ALIASES for c in orig)
        d["raw_header_newline"] = any("\n" in str(c) for c in sheets[name].columns)
        frames.append(d)
    raw = pd.concat(frames, ignore_index=True)
    for c in RAW_KEYS:
        if c not in raw:
            raw[c] = np.nan
    return raw

def get_raw():
    """ข้อมูลดิบ (ถ้ามีไฟล์) — ไม่มีไฟล์จะได้ None"""
    get_data()
    return load_raw(RAW_FILE.stat().st_mtime) if RAW_FILE.exists() else None

def get_data() -> pd.DataFrame:
    if not DATA_FILE.exists():
        st.error(f"ไม่พบไฟล์ข้อมูล: {DATA_FILE.relative_to(BASE)}")
        st.stop()
    try:
        return load_data(DATA_FILE.stat().st_mtime)
    except ValueError as e:
        st.error(str(e))
        st.stop()

def as_of(df: pd.DataFrame) -> pd.Timestamp:
    """วันที่ล่าสุดของข้อมูล = วันที่รับชำระล่าสุดที่พบในไฟล์"""
    return df["last"].max()

# ─────────────────────────────── ตรวจคุณภาพข้อมูล (Audit) ───────────────────────────────
FIX, CHECK, NOTE = "ควรแก้ไข", "ควรตรวจสอบ", "ข้อสังเกต"

def quality_rules(df: pd.DataFrame):
    """กฎตรวจซ้ำบนข้อมูลที่คลีนแล้ว -> [(รหัส, ชื่อกฎ, ระดับ, mask, คอลัมน์ที่ไฮไลต์, คำอธิบาย)]"""
    cut = as_of(df)
    paid_ok = np.isclose(df["principal"] + df["balance"], df["approved"], atol=1)
    money = df[MONEY]
    return [
        ("dup", "เลขที่สัญญาซ้ำ", FIX, df["contract_id"].duplicated(keep=False), ["contract_id"], "สัญญาเดียวกันไม่ควรปรากฏมากกว่า 1 แถว"),
        ("neg", "ค่าเงินติดลบ", FIX, (money < 0).any(axis=1), MONEY, "ยอดเงินต้องไม่ติดลบ"),
        ("sheet", "อำเภอไม่ตรงกับชีตต้นทาง", FIX, df["district"] != df["source_sheet"], ["district", "source_sheet"], "ชื่ออำเภอควรตรงกับชีตที่นำเข้ามา"),
        ("rate", "ไม่มีอัตราดอกเบี้ยตามสัญญา", FIX, df["rate"].isna(), ["rate"], "ตรวจกับสัญญาต้นฉบับแล้วเติมค่า"),
        ("rate_late", "ไม่มีอัตราดอกเบี้ยผิดนัด", FIX, df["rate_late"].isna(), ["rate_late"], "ตรวจกับสัญญาต้นฉบับแล้วเติมค่า"),
        ("end_before_start", "วันสิ้นสุดสัญญาก่อนวันเริ่มสัญญา", FIX, df["end"] < df["start"], ["start", "end"], "ลำดับวันที่ผิดปกติ ควรตรวจกับสัญญา"),
        ("pay_before_start", "รับชำระก่อนวันเริ่มสัญญา", FIX, df["last"] < df["start"], ["start", "last"], "ลำดับวันที่ผิดปกติ ควรตรวจกับสัญญา"),
        ("dist_alias", "ชื่ออำเภอในไฟล์ไม่ตรงมาตรฐาน (ระบบปรับให้ตอนโหลด)", CHECK, df["district_file"] != df["district"], ["district_file"], "เช่น ‘อ.ปลายพระยา’, ‘อำเภอลำทับ’, ‘เมือง’ — ควรแก้ที่ต้นทางให้เป็นชื่อมาตรฐาน"),
        ("sub_prefix", "ชื่อตำบลมีคำนำหน้า ‘ตำบล’/‘ต.’", CHECK, df["subdistrict"].fillna("").str.match(r"^(ตำบล|ต\.)"), ["subdistrict"], "ควรเหลือเฉพาะชื่อตำบล"),
        ("sub_none", "ตำบลระบุเป็น ‘ไม่ระบุ’ หรือว่าง", NOTE, df["subdistrict"].isna() | (df["subdistrict"] == "ไม่ระบุ"), ["subdistrict"], "ไม่มีข้อมูลตำบลของโครงการ ควรเติมจากเอกสารโครงการ"),
        ("late_no_pay", "สถานะเกินกำหนด (ผิดนัด/ไกล่เกลี่ย/ฟ้อง) แต่ไม่มีวันที่รับชำระล่าสุด", CHECK, df["status"].isin(LATE_SET) & df["last"].isna(), ["status", "last"], "ยังไม่เคยชำระ หรือไม่ได้บันทึกวันที่"),
        ("bal", "เงินต้นที่ชำระ + คงเหลือ ≠ เงินอนุมัติ (ต่างเกิน 1 บาท)", CHECK, ~paid_ok, ["approved", "principal", "balance"], "อาจเบิกจ่ายจริงน้อยกว่าเงินอนุมัติ หรือปรับยอดภายหลัง"),
        ("fy", "วันที่เริ่มสัญญาเร็วกว่าปีงบประมาณเกิน 1 ปี", CHECK, df["start"].dt.year < df["fy"] - 543 - 1, ["fy", "start"], "ปีงบประมาณกับวันที่เริ่มสัญญาควรสอดคล้องกัน"),
        ("no_last", "ไม่มีวันที่รับชำระล่าสุด", CHECK, df["last"].isna(), ["last"], "ยังไม่เคยชำระ หรือไม่ได้บันทึกวันที่"),
        ("pay_after_end", "รับชำระล่าสุดหลังวันสิ้นสุดสัญญา", NOTE, df["last"] > df["end"], ["last", "end"], "พบในสัญญาที่ชำระล่าช้าเกินกำหนด"),
        ("late_int", "มีดอกเบี้ยผิดนัดแต่สถานะยังเป็น ‘ดำเนินการ’", NOTE, (df["interest_late"] > 0) & (df["status"] == RUN), ["interest_late", "status"], "เคยชำระล่าช้าระหว่างสัญญา"),
    ]
