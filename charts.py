"""Plotly styling, gradient colors and the district map."""
from __future__ import annotations

import base64
import io
import numpy as np
import plotly.graph_objects as go
import streamlit as st
from PIL import Image
from data import BASE
from theme import FONT, T

def style_fig(fig: go.Figure, h=300, legend=True) -> go.Figure:
    fig.update_layout(height=h, margin=dict(l=4, r=8, t=4, b=4), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(family=FONT, size=13, color=T["INK"]), showlegend=legend, hoverlabel=dict(font_family=FONT),
                      legend=dict(orientation="h", y=1.14, x=0, font_size=12))
    fig.update_xaxes(showgrid=False, linecolor=T["LINE"], tickfont_color=T["MUTED"])
    fig.update_yaxes(gridcolor="#E8ECF1", zeroline=False, tickfont_color=T["MUTED"])
    return fig

def show(fig, key, **kw):
    return st.plotly_chart(fig, width="stretch", key=key, config={"displayModeBar": False}, **kw)

def gradient_colors(values, light="#CFDDF0", dark="#14264A") -> list[str]:
    """ไล่สีตามค่า: ค่าน้อยสุด = สีอ่อน, ค่ามากสุด = สีเข้ม (ผสมเส้นตรงระหว่างสองสี)"""
    v = np.asarray(values, dtype=float)
    t = (v - v.min()) / (v.max() - v.min()) if v.max() > v.min() else np.ones_like(v)
    a, b = [np.array([int(c[i:i + 2], 16) for i in (1, 3, 5)]) for c in (light, dark)]
    return ["#%02X%02X%02X" % tuple(int(round(x)) for x in a + (b - a) * k) for k in t]

# ── แผนที่ระดับอำเภอ (choropleth) จากภาพแผนที่กระบี่ assets/krabi_map.jpg
MAP_FILE = BASE / "assets" / "krabi_map.jpg"
MAP_SCALE = 2
# จุดกลางของแต่ละอำเภอในภาพต้นฉบับ (349×573 px) ใช้จับคู่พื้นที่ในภาพกับชื่ออำเภอ และเป็นตำแหน่งแสดงชื่อ/ตัวเลข
MAP_ANCHORS = {"ปลายพระยา": (106, 59), "อ่าวลึก": (82, 126), "เมืองกระบี่": (120, 214), "เขาพนม": (218, 172), "คลองท่อม": (251, 308),
               "เหนือคลอง": (189, 254), "ลำทับ": (305, 261), "เกาะลันตา": (202, 400)}
MAP_LABEL_POS = {"ปลายพระยา": (106, 66), "อ่าวลึก": (95, 118), "เมืองกระบี่": (120, 215), "เขาพนม": (225, 160), "คลองท่อม": (255, 322),
                 "เหนือคลอง": (190, 255), "ลำทับ": (305, 262), "เกาะลันตา": (203, 418)}  # เกาะลันตา: วางกลางอำเภอ (บนเกาะ) ใช้ตัวอักษรสีเข้ม
# ปรับเฉพาะอำเภอ: (เลื่อนแนวนอน px, เลื่อนแนวตั้ง px (+ = ลง), เพิ่ม/ลดขนาดตัวอักษร) หน่วยตามภาพต้นฉบับ 349×573
MAP_TWEAK = {"เมืองกระบี่": (0, 14, 0), "ลำทับ": (0, 16, -3), "เขาพนม": (0, -10, -2)}
MAP_OUTSIDE = {"เกาะลันตา"}   # ป้ายที่อยู่นอกพื้นที่ (บนทะเล) ใช้ตัวอักษรสีเข้ม

@st.cache_resource(show_spinner="กำลังเตรียมแผนที่…")
def load_map():
    """แยกพื้นที่อำเภอจากภาพแผนที่ (พื้นที่สีครีมที่คั่นด้วยเส้นเขต) แล้วจับคู่กับชื่ออำเภอตามตำแหน่งที่ใกล้ที่สุด"""
    from collections import deque
    im = Image.open(MAP_FILE).convert("RGB")
    a = np.asarray(im).astype(int)
    H, W = a.shape[:2]
    cream = (a[:, :, 0] >= 238) & (a[:, :, 1] >= 238) & (a[:, :, 2] >= 212) & (a[:, :, 2] <= 252) & (a[:, :, 0] - a[:, :, 2] >= 2)
    lab = np.zeros((H, W), int)
    comps = []
    for y in range(H):
        for x in range(W):
            if cream[y, x] and not lab[y, x]:
                k = len(comps) + 1
                q, pts = deque([(y, x)]), []
                lab[y, x] = k
                while q:
                    cy, cx = q.popleft()
                    pts.append((cy, cx))
                    for ny, nx in ((cy + 1, cx), (cy - 1, cx), (cy, cx + 1), (cy, cx - 1)):
                        if 0 <= ny < H and 0 <= nx < W and cream[ny, nx] and not lab[ny, nx]:
                            lab[ny, nx] = k
                            q.append((ny, nx))
                comps.append(pts)
    masks = {n: np.zeros((H, W), np.uint8) for n in MAP_ANCHORS}
    for pts in comps:
        if len(pts) < 150:      # เกาะเล็ก/จุดเล็กไม่ลงสี
            continue
        cy, cx = np.mean(pts, axis=0)
        name = min(MAP_ANCHORS, key=lambda n: (MAP_ANCHORS[n][0] - cx) ** 2 + (MAP_ANCHORS[n][1] - cy) ** 2)
        for y, x in pts:
            masks[name][y, x] = 255
    # ขยายพื้นที่ออก 1 px ไปยังพิกเซลขอบที่เป็นสีผสม (ไม่ใช่เส้นเขตสีเข้ม ไม่ใช่ทะเล/เขตจังหวัดข้างเคียง) เพื่อไม่ให้เหลือขอบขาว
    lum = a.mean(axis=2)
    near_water = (np.abs(a - np.array([196, 232, 248])).sum(axis=2) < 40)
    tan = (a[:, :, 2] < 205) & (a[:, :, 0] > 225)
    allowed = (lum > 205) & ~near_water & ~tan & ~cream
    for n, m in masks.items():
        on = m > 0
        grown = on.copy()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            grown |= np.roll(np.roll(on, dy, axis=0), dx, axis=1) & allowed
        masks[n] = (grown * 255).astype(np.uint8)
    # จุดวางป้ายที่ "กว้างที่สุด" ภายในพื้นที่ (สูง ~2 บรรทัด) + ความกว้างที่ใช้ได้ -> ใช้กำหนดขนาดตัวอักษรไม่ให้ล้น
    labels = {}
    for n, m in masks.items():
        on = m > 0
        run = np.zeros((H, W), int)                       # ความยาวช่วงต่อเนื่องในแนวนอนที่พิกเซลนั้นอยู่
        for y in range(H):
            x = 0
            while x < W:
                if on[y, x]:
                    x0 = x
                    while x < W and on[y, x]:
                        x += 1
                    run[y, x0:x] = x - x0
                else:
                    x += 1
        h = 12                                            # ครึ่งหนึ่งของความสูงป้าย (px ของภาพต้นฉบับ)
        wid = np.minimum(np.minimum(np.roll(run, h, axis=0), run), np.roll(run, -h, axis=0))
        wid[:h] = 0
        wid[-h:] = 0
        yy, xx = np.unravel_index(int(np.argmax(wid)), wid.shape)
        # ถ้ามีหลายจุดกว้างเท่ากัน เลือกจุดกลางของกลุ่มนั้น
        ys, xs = np.where(wid >= wid[yy, xx] - 2)
        labels[n] = (float(xs.mean()), float(ys.mean()), int(wid[yy, xx]))
    size = (W * MAP_SCALE, H * MAP_SCALE)
    soft = {n: np.asarray(Image.fromarray(m).resize(size, Image.BICUBIC)).astype(float) / 255 for n, m in masks.items()}
    base = np.asarray(im.resize(size, Image.BICUBIC)).astype(float)
    return dict(base=base, soft=soft, size=size, labels=labels)

def hex_rgb(h: str) -> np.ndarray:
    return np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)], float)

def map_data_uri(colors: dict, fade: dict) -> str:
    m = load_map()
    out = m["base"].copy()
    for name, soft in m["soft"].items():
        alpha = (soft * fade.get(name, 1.0))[:, :, None]
        out = out * (1 - alpha) + hex_rgb(colors[name]) * alpha
    buf = io.BytesIO()
    Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).save(buf, format="JPEG", quality=88)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()

LINE_COLORS = [T["NAVY"], T["STEEL"], T["SAND"], T["TEAL"], "#8C6D3F", "#2F6F8F", "#9AA7B8", "#B07A9A"]
