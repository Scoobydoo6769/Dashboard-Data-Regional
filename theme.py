"""Colors, CSS and small HTML UI pieces."""
from __future__ import annotations

import base64
import streamlit as st
from data import BASE

# สี: พื้นหลังสว่าง 60 / น้ำเงินกรมท่า 30 / ทอง accent 10 — แดง/เขียวใช้สื่อความหมายเท่านั้น
T = dict(NAVY="#14264A", NAVY2="#1F3A5F", STEEL="#6B94BD", SAND="#D9B26F", SLATE="#A9B4C2", TEAL="#4C8C8A",
         BG="#F3F5F8", SURF="#FFFFFF", INK="#16202E", MUTED="#566377", LINE="#DCE2EA",
         GOLD="#C48A1F", GOOD="#1B7F52", BAD="#B83A2E", BAD_BG="#FBE3DF", WARN_BG="#FFF3D6")
PALETTE = [T["NAVY"], T["STEEL"], T["SAND"], T["SLATE"], T["TEAL"]]
FONT = "Noto Sans Thai, system-ui, sans-serif"

# ─────────────────────────────── ธีม / CSS ───────────────────────────────
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Thai:wght@400;500;600;700&display=swap');
.stApp, .stApp p, .stApp label, .stApp input, .stApp textarea, .stApp button, .stApp li, .stApp td, .stApp th,
.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp [data-baseweb], .stApp [data-testid="stMarkdownContainer"]
 { font-family: 'Noto Sans Thai', system-ui, sans-serif; }
.stApp { background:@BG@; color:@INK@; line-height:1.6; font-variant-numeric: tabular-nums; }
.block-container { padding-top:2.2rem; padding-bottom:3rem; max-width:1480px; }
header[data-testid="stHeader"] { background:transparent; }
::selection { background:@GOLD@; color:#fff; }
:focus-visible { outline:2px solid @GOLD@ !important; outline-offset:2px; }
* { scrollbar-width:thin; scrollbar-color:@SLATE@ transparent; }
h1,h2,h3 { color:@NAVY@; letter-spacing:0; }
.stApp h1.page-title { font-size:1.5rem; padding:0; font-weight:700; color:@NAVY@; line-height:1.35; margin:0; text-wrap:balance; }
.page-sub { color:@MUTED@; font-size:.95rem; margin:.15rem 0 1.1rem; }

/* sidebar */
[data-testid="stSidebar"] { background:@NAVY@; border-right:0; }
[data-testid="stSidebarHeader"]::before { content:"กองทุนพัฒนาบทบาทสตรี\\A จังหวัดกระบี่"; white-space:pre; color:#fff;
  font-weight:700; font-size:1.02rem; line-height:1.4; padding:.3rem .5rem .3rem 3.4rem; min-height:2.8rem;
  display:flex; align-items:center; background:@SEAL@ no-repeat .3rem center / 2.6rem 2.6rem; }
[data-testid="stSidebar"] * { color:#E4EAF3; }
[data-testid="stSidebarNavLink"] { border-radius:8px; padding:.4rem .75rem; margin-bottom:1px; }
[data-testid="stSidebarNavLink"]:hover { background:rgba(255,255,255,.08); }
[data-testid="stSidebarNavLink"][aria-current="page"] { background:rgba(255,255,255,.14); }
[data-testid="stSidebarNavLink"][aria-current="page"] * { color:#fff; font-weight:600; }
[data-testid="stSidebarNavLink"][aria-current="page"] span[data-testid="stIconMaterial"] { color:@SAND@; }
[data-testid="stSidebar"] .stButton button { background:transparent; border:1px solid rgba(255,255,255,.35); color:#fff; width:100%; }
[data-testid="stSidebar"] .stButton button:hover { background:rgba(255,255,255,.1); border-color:#fff; }
.user-chip { font-size:.85rem; color:#B9C5D8 !important; margin:.1rem 0 .4rem; line-height:1.5; }
.user-chip b { color:#fff !important; font-size:.95rem; }

/* cards */
[class*="st-key-card"] { background:@SURF@; border:1px solid @LINE@; border-radius:12px; padding:1.1rem 1.2rem 1rem;
  box-shadow:0 1px 2px rgba(20,38,74,.05), 0 4px 14px rgba(20,38,74,.04); }
.card-t { font-weight:700; color:@NAVY@; font-size:1.02rem; line-height:1.45; text-wrap:balance; }
.card-s { color:@MUTED@; font-size:.82rem; margin-bottom:.4rem; }

/* kpi */
.kpi-row { display:grid; grid-template-columns:repeat(4,1fr); gap:1rem; margin-bottom:1rem; }
.kpi { background:@SURF@; border:1px solid @LINE@; border-radius:12px; padding:1rem 1.2rem;
  box-shadow:0 1px 2px rgba(20,38,74,.05), 0 4px 14px rgba(20,38,74,.04); }
.kpi-l { color:@MUTED@; font-weight:600; font-size:.95rem; }
.kpi-v { color:@NAVY@; font-weight:700; font-size:2.15rem; line-height:1.3; margin:.1rem 0; }
.kpi-u { font-size:1rem; font-weight:600; color:@MUTED@; margin-left:.35rem; }
.kpi-d { font-size:.85rem; font-weight:600; color:@MUTED@; display:flex; align-items:center; gap:.4rem; }
.kpi-d.good { color:@GOOD@; } .kpi-d.bad { color:@BAD@; }
.kpi-d i { width:.6rem; height:.5rem; background:currentColor; display:inline-block; }
.kpi-d i.up { clip-path:polygon(50% 0,100% 100%,0 100%); } .kpi-d i.down { clip-path:polygon(0 0,100% 0,50% 100%); }
.kpi-d i.flat { height:2px; }

/* insights, flow, action plan */
.insights { background:@SURF@; border:1px solid @LINE@; border-radius:12px; padding:.9rem 1.2rem; margin-bottom:1rem; }
.insights .blue { color:#1B4380; font-weight:700; }
.insights .pos { color:@GOOD@; font-weight:700; } .insights .neg { color:@BAD@; font-weight:700; }
.insights ul { margin:.35rem 0 0; padding-left:1.1rem; } .insights li { margin:.15rem 0; }
.flow { display:flex; align-items:stretch; gap:.5rem; flex-wrap:wrap; margin:.2rem 0 1rem; }
.step { flex:1 1 150px; background:@SURF@; border:1px solid @LINE@; border-radius:12px; padding:.8rem 1rem; }
.step b { display:block; font-size:1.7rem; color:@NAVY@; line-height:1.3; } .step span { color:@MUTED@; font-size:.85rem; }
.step b small { display:inline; font-size:1.2rem; font-weight:700; color:@INK@; margin-left:.35rem; }
.step.final { background:@NAVY@; border-color:@NAVY@; } .step.final b, .step.final span, .step.final b small { color:#fff; }
.step.minus b { color:@BAD@; }
.sep { align-self:center; width:.6rem; height:.8rem; background:@SLATE@; clip-path:polygon(0 0,100% 50%,0 100%); }
.plan { display:grid; grid-template-columns:repeat(4,1fr); gap:.6rem; margin-bottom:.25rem; }
.plan > div { background:@SURF@; border:1px solid @LINE@; border-radius:10px; padding:.7rem .9rem; font-size:.92rem; }
.plan small { display:block; color:@MUTED@; font-weight:600; margin-bottom:.15rem; }
.plan .impact { background:#EAF5EF; border-color:#BFE0CE; }
.legend { color:@MUTED@; font-size:.85rem; margin-bottom:.4rem; }
.legend .bad { background:@BAD_BG@; color:@BAD@; padding:.05rem .5rem; border-radius:4px; font-weight:600; }
.legend .dup { background:@WARN_BG@; padding:.05rem .5rem; border-radius:4px; font-weight:600; }
.note { background:#EEF2F8; border-radius:8px; padding:.45rem .9rem; font-size:.85rem; color:@MUTED@; margin-bottom:.9rem; }
.login-brand { color:@NAVY@; font-weight:700; font-size:1.35rem; line-height:1.45; text-align:center; }
.login-sub { color:@MUTED@; text-align:center; margin-bottom:1rem; }
@media (max-width:1000px) { .kpi-row, .plan { grid-template-columns:repeat(2,1fr); } }
@media (max-width:600px) { .kpi-row, .plan { grid-template-columns:1fr; } .stApp h1.page-title { font-size:1.3rem; } }

/* sidebar: หัวข้อกลุ่มเมนู / เส้นคั่น / ตัวกรอง */
[data-testid="stNavSectionHeader"] { color:#8FA3C2 !important; font-size:.78rem; font-weight:600; letter-spacing:.04em; margin-top:.9rem; }
.side-rule { height:1px; background:rgba(255,255,255,.16); margin:.45rem 0; }
.side-h { color:#fff !important; font-weight:700; font-size:1.05rem; margin:.1rem 0 .4rem; }
[data-testid="stSidebar"] label p { color:#E4EAF3 !important; font-size:.9rem; }

/* ปุ่มออกจากระบบอยู่ล่างสุดของ sidebar: ให้เนื้อหา sidebar สูงเต็มหน้าจอ แล้วดันกลุ่มนี้ลงล่าง (และตรึงไว้เมื่อเนื้อหายาวกว่าจอ) */
[data-testid="stSidebarContent"] { display:flex; flex-direction:column; }
[data-testid="stSidebarUserContent"], [data-testid="stSidebarUserContent"] > div, [data-testid="stSidebarUserContent"] > div > [data-testid="stVerticalBlock"]
 { flex:1 1 auto; display:flex; flex-direction:column; }
[data-testid="stLayoutWrapper"]:has(> .st-key-side_logout) { margin-top:auto; position:sticky; bottom:0; background:@NAVY@; z-index:5; }
.st-key-side_logout { padding-bottom:.9rem; }

/* ข้อค้นพบสำคัญ 4 คอลัมน์ */
.ins-card { background:@SURF@; border:1px solid @LINE@; border-radius:14px; padding:1.2rem 1.5rem 1.3rem; margin-bottom:1rem;
  box-shadow:0 1px 2px rgba(20,38,74,.05), 0 4px 14px rgba(20,38,74,.04); }
.ins-title { font-weight:700; color:@NAVY@; font-size:1.2rem; line-height:1.4; }
.ins-sub { color:@MUTED@; font-size:.9rem; margin-bottom:1rem; }
.ins-grid { display:grid; grid-template-columns:repeat(4,1fr); }
.ins { padding:0 1.2rem; border-left:1px solid @LINE@; } .ins:first-child { padding-left:0; border-left:0; }
.ins-n { font-size:2rem; font-weight:700; line-height:1.3; color:@NAVY@; } .ins-n small { font-size:1rem; font-weight:600; }
.ins-n.blue { color:#1B4380; } .ins-n.pos { color:@GOOD@; } .ins-n.neg { color:@BAD@; }
.ins-h { font-weight:700; color:@INK@; line-height:1.45; margin:.2rem 0 .25rem; }
.ins-d { color:@MUTED@; font-size:.88rem; line-height:1.55; }

/* การ์ดตัวชี้วัดด้านข้าง */
.sk-col { display:flex; flex-direction:column; gap:.75rem; }
.sk { background:@SURF@; border:1px solid @LINE@; border-radius:14px; padding:.8rem 1.1rem;
  box-shadow:0 1px 2px rgba(20,38,74,.05), 0 4px 14px rgba(20,38,74,.04); }
.sk-l { color:@MUTED@; font-size:.9rem; font-weight:600; }
.sk-row { display:flex; justify-content:space-between; align-items:flex-end; gap:.8rem; }
.sk-v { color:@NAVY@; font-size:1.9rem; font-weight:700; line-height:1.3; } .sk-v span { font-size:.95rem; font-weight:600; color:@MUTED@; margin-left:.35rem; }
.pill { display:inline-flex; align-items:center; gap:.35rem; font-size:.78rem; font-weight:700; padding:.1rem .55rem; border-radius:99px; background:#EEF1F5; color:@MUTED@; }
.pill.good { background:#E3F4EA; color:@GOOD@; } .pill.bad { background:#FBE3DF; color:@BAD@; }
.pill i { width:.5rem; height:.42rem; background:currentColor; display:inline-block; }
.pill i.up { clip-path:polygon(50% 0,100% 100%,0 100%); } .pill i.down { clip-path:polygon(0 0,100% 0,50% 100%); } .pill i.flat { height:2px; }
.bars { display:flex; align-items:flex-end; gap:3px; height:2.9rem; flex:0 0 7.2rem; }
.bars b { flex:1; background:#C9D8EC; border-radius:2px 2px 0 0; } .bars b.on { background:#4A74A8; }
@media (max-width:1000px) { .ins-grid { grid-template-columns:repeat(2,1fr); row-gap:1rem; } .ins:nth-child(odd) { padding-left:0; border-left:0; } }
@media (max-width:600px) { .ins-grid { grid-template-columns:1fr; } .ins { padding:0; border-left:0; } }
</style>
"""

def inject_css(hide_sidebar: bool = False):
    css = CSS
    seal = BASE / "assets" / "krabi_seal.png"  # ตราเมืองกระบี่ (ไม่มีไฟล์ = แสดงเฉพาะข้อความ)
    uri = "url(data:image/png;base64," + base64.b64encode(seal.read_bytes()).decode() + ")" if seal.exists() else "none"
    css = css.replace("@SEAL@", uri)
    for k, v in T.items():
        css = css.replace(f"@{k}@", v)
    if hide_sidebar:
        css = css.replace("</style>", '[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"] { display:none; } </style>')
    st.markdown(css, unsafe_allow_html=True)

# ─────────────────────────────── ส่วนประกอบ UI ───────────────────────────────
def page_head(title: str, sub: str):
    st.markdown(f'<h1 class="page-title">{title}</h1><p class="page-sub">{sub}</p>', unsafe_allow_html=True)

def card_head(title: str, sub: str):
    st.markdown(f'<div class="card-t">{title}</div><div class="card-s">{sub}</div>', unsafe_allow_html=True)

def kpi(label, value, unit, delta, tone="flat", arrow="flat"):
    return (f'<div class="kpi"><div class="kpi-l">{label}</div><div class="kpi-v">{value}<span class="kpi-u">{unit}</span></div>'
            f'<div class="kpi-d {tone}"><i class="{arrow}"></i>{delta}</div></div>')

def delta_pct(cur, prev, suffix="เทียบช่วงก่อนหน้า", good_up=True):
    if not prev:
        return "ไม่มีช่วงก่อนหน้าให้เทียบ", "flat", "flat"
    p = (cur - prev) / prev
    up = p >= 0
    tone = "flat" if abs(p) < .0005 else ("good" if up == good_up else "bad")
    return f"{p:+.1%} {suffix}", tone, "up" if up else "down"

def empty_state(msg="ไม่พบข้อมูลในช่วงเวลา/ตัวกรองที่เลือก — ลองขยายช่วงปีงบประมาณหรือเลือกอำเภออื่น"):
    st.info(msg, icon=":material/search_off:")
    st.stop()

def sk_card(label, value, unit, delta, tone, arrow, series):
    """การ์ดตัวชี้วัดด้านข้าง: ตัวเลข + ป้ายเปลี่ยนแปลง + แท่งเล็กรายปีงบประมาณ (แท่งสุดท้ายเข้ม)"""
    mx = max(series) if len(series) and max(series) > 0 else 1
    bars = "".join(f'<b class="{"on" if i == len(series) - 1 else ""}" style="height:{max(12, v / mx * 100):.0f}%"></b>' for i, v in enumerate(series))
    return (f'<div class="sk"><div class="sk-l">{label}</div><div class="sk-row"><div><div class="sk-v">{value}<span>{unit}</span></div>'
            f'<span class="pill {tone}"><i class="{arrow}"></i>{delta}</span></div><div class="bars">{bars}</div></div></div>')

def insight(num, cls, head, desc):
    return f'<div class="ins"><div class="ins-n {cls}">{num}</div><div class="ins-h">{head}</div><div class="ins-d">{desc}</div></div>'
