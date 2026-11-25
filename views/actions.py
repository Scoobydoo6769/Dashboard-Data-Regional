from __future__ import annotations

import html
import streamlit as st
from data import LATE_SET, RUN, baht_m, get_data
from filters import data_note
from theme import page_head

def page_actions():
    df = get_data()
    page_head("แผนปฏิบัติการเชิงกลยุทธ์ (Strategic Action Plan)", "แปลงข้อค้นพบจากข้อมูลให้เป็นการลงมือทำ: ปัญหา → สาเหตุ → สิ่งที่ควรทำ → ผลลัพธ์ที่คาด")
    data_note(df)
    if "actions" not in st.session_state:  # ข้อเสนอเริ่มต้นสร้างจากข้อมูลจริง ส่วน ‘สาเหตุ’ รอยืนยันกับพื้นที่
        g = df.groupby("district").agg(n=("status", "size"), late=("status", lambda s: s.isin(LATE_SET).sum()))
        g["p"] = g["late"] / g["n"]
        w = g["p"].idxmax()
        late = df[df["status"].isin(LATE_SET)]
        no_last = df[(df["status"] == RUN) & df["last"].isna()]
        st.session_state["actions"] = [
            dict(f=f"{w}มีสัดส่วนโครงการค้างชำระสูงสุด {g.loc[w, 'p']:.0%} ({int(g.loc[w, 'late'])} จาก {int(g.loc[w, 'n'])} โครงการ)",
                 c="รอยืนยันสาเหตุจากการลงพื้นที่", a="ลงพื้นที่ติดตามกลุ่มค้างชำระ และจัดเวทีทบทวนแผนการชำระ", i="สัดส่วนโครงการค้างชำระลดลงอย่างน้อยหนึ่งในสาม ภายใน 2 ปีงบประมาณ"),
            dict(f=f"ยอดคงเหลือของโครงการค้างชำระรวม {baht_m(late['balance'].sum())} ล้านบาท ({len(late):,} โครงการ)",
                 c="รอยืนยันสาเหตุ", a="จัดลำดับทวงถามตามยอดคงเหลือ เริ่มจากรายใหญ่ (ดูตัวจำลองในหน้าพยากรณ์)", i="เก็บคืนได้อย่างน้อย 30% ของยอดค้างภายใน 12 เดือน"),
            dict(f=f"โครงการที่ยังดำเนินการ {len(no_last):,} แห่งไม่มีวันที่รับชำระล่าสุด",
                 c="อาจยังไม่เคยชำระ หรือไม่ได้บันทึกข้อมูล", a="ตรวจสอบเอกสารการรับชำระของโครงการเหล่านี้และอัปเดตข้อมูล", i="ข้อมูลการชำระครบถ้วน ติดตามความเสี่ยงได้ทันท่วงที"),
        ]
    acts = st.session_state["actions"]
    for i, a in enumerate(acts):
        e = {k: html.escape(v) for k, v in a.items()}
        st.markdown(f'<div class="plan"><div><small>ปัญหาที่พบ (Finding)</small>{e["f"]}</div>'
                    f'<div><small>สาเหตุเชิงลึก (Root Cause)</small>{e["c"]}</div>'
                    f'<div><small>สิ่งที่ควรทำ (Action)</small>{e["a"]}</div>'
                    f'<div class="impact"><small>ผลลัพธ์ที่คาด (Expected Impact)</small>{e["i"]}</div></div>', unsafe_allow_html=True)
        if st.button("ลบข้อเสนอนี้", key=f"act_del_{i}", type="tertiary", icon=":material/delete:"):
            acts.pop(i)
            st.rerun()
    if not acts:
        st.info("ยังไม่มีข้อเสนอ — เพิ่มข้อเสนอแรกได้ด้านล่าง", icon=":material/assignment:")
    with st.expander("เพิ่มข้อเสนอเชิงกลยุทธ์", icon=":material/add:"):
        with st.form("act_form", clear_on_submit=True):
            c = st.columns(4)
            vals = [c[0].text_area("ปัญหาที่พบ", key="act_f"), c[1].text_area("สาเหตุเชิงลึก", key="act_c"),
                    c[2].text_area("สิ่งที่ควรทำ", key="act_a"), c[3].text_area("ผลลัพธ์ที่คาด", key="act_i")]
            if st.form_submit_button("เพิ่มข้อเสนอ", type="primary"):
                if all(v.strip() for v in vals):
                    acts.append(dict(zip("fcai", [v.strip() for v in vals])))
                    st.rerun()
                else:
                    st.warning("กรุณากรอกให้ครบทั้ง 4 ช่อง", icon=":material/edit_note:")
    st.caption("ข้อเสนอเก็บอยู่ในเซสชันนี้เท่านั้น — เมื่อรีเฟรชหรือออกจากระบบจะรีเซ็ต · ข้อความเริ่มต้นคำนวณจากข้อมูลจริง ส่วนสาเหตุควรยืนยันกับพื้นที่ก่อนใช้")
