# Lab 3 — Validation Record (BJT DC Bias Web App)

วันที่ตรวจ: 2026-11-17
แอปที่ตรวจ: `http://127.0.0.1:5000/` (Flask dev server, Python 3.12)
เกณฑ์: `|ΔIC| ≤ 0.01 mA`, `|ΔVCE| ≤ 0.02 V` เทียบค่าที่แสดงกับค่าอ้างอิงที่ยังไม่ปัดเศษ

## 1. เครื่องมือที่ใช้ตรวจ และบทบาทของ MCP

| รายการ | ผล |
| --- | --- |
| วิธีตรวจหลัก | **Playwright MCP** (`@playwright/mcp`) ผ่านเครื่องมือ `browser_*` ใน OpenCode |
| ตรวจซ้ำด้วย | **OpenCode Browser** — ได้ผลตรงกันทุกกรณี (รอบแรกก่อนเพิ่ม `opencode.json`) |
| MCP config | `opencode.json` (OpenCode V2) · `"type": "local"` · `--browser chrome --isolated` |
| Node / npx | ตรวจแล้ว: `node v24.14.0`, `npx 11.9.0` |
| Console | ไม่มี error จากแอป — มีเพียง `404 /favicon.ico` ซึ่งไม่กระทบผลคำนวณ |

**MCP (Model Context Protocol)** คือมาตรฐานที่ให้แอป AI รู้ว่ามีเครื่องมืออะไร เรียกใช้เครื่องมือนั้น และรับผลกลับมา

- **OpenCode** เป็น host / **MCP Client** — เอเจนต์อยู่ฝั่งนี้
- **Playwright MCP** เป็น **MCP Server** — ใน `opencode.json` ใช้ `"type": "local"` จึงสตาร์ทเป็นโปรเซสในเครื่อง สื่อสารผ่าน `stdio` (ไม่ต้องเปิดพอร์ตของ MCP เอง)
- ลำดับข้อมูล: `OpenCode → (MCP) → Playwright MCP → Browser → (HTTP) → Flask + Python`
  แล้วส่งกลับ `หน้าเว็บ → Browser → MCP → OpenCode` เป็น snapshot ให้อ่าน
- เบราว์เซอร์คุยกับ Flask ด้วย HTTP ปกติ (ฟอร์ม POST) จึง **ไม่ต้องลง Playwright ใน `requirements.txt`**
- `--isolated` ให้ใช้โปรไฟล์ทดสอบแยก ไม่แตะเซสชัน Chrome ส่วนตัว

รอบสุดท้ายรันผ่าน Playwright MCP ตามที่ใบงานแนะนำ (ใช้ `browser_navigate`, `browser_snapshot`,
`browser_select_option`, `browser_fill_form`, `browser_click`, `browser_evaluate`) แล้วตรวจซ้ำด้วย
OpenCode Browser ได้ผลเหมือนกันทุกตัวเลข ทั้งสองวิธีอ่านจากหน้าเว็บจริง ไม่ได้ใช้ `curl` หรืออ่านโค้ดแทน

## 2. ผล A1–A5 (ตารางตามแบบใบงาน)

ใช้ร่วมกัน: `VCC = 12 V`, `RC = 2200 Ω` (2.2 kΩ), `β = 100`, `VBE = 0.70 V`
ฟอร์มรับหน่วย **Ω** (เช่น 1 MΩ = `1000000`)

| กรณี | เลือกโหมดและกรอกค่า | คาดหมายก่อนรัน | เห็นจริง (พร้อมหน่วย) | วิธีตรวจ | สถานะ |
| --- | --- | --- | --- | --- | --- |
| A1 · โหมดเดิม | Divider · R1=100000, R2=22000, RE=1000 | IC 1.229858 mA · VCE 8.052155 V (ตรงกับค่าอ้างอิงเดิม) | IC **1.230 mA** · VCE **8.052 V** · ACTIVE · KCL PASS | Playwright MCP | PASS |
| A2 · Fixed | Fixed · RB=1000000 (ไม่กรอก RE) | IC 1.130000 mA · VCE 9.514000 V | IC **1.130 mA** · VCE **9.514 V** · ACTIVE · KCL PASS | Playwright MCP | PASS |
| A3 · Emitter | Emitter · RB=1000000, RE=1000 (มีช่อง RE) | IC 1.026340 mA · VCE 8.705450 V | IC **1.026 mA** · VCE **8.705 V** · ACTIVE · KCL PASS | Playwright MCP | PASS |
| A4 · เปลี่ยนค่าเดียว | Emitter · เหมือน A3 แต่ RE=2000 | ทำนาย: **IC ลดลง** เพราะ `(β+1)RE` ในตัวหารเพิ่ม | IC **0.940 mA** · VCE **8.033 V** · ACTIVE · KCL PASS → ลดลงจริงตามทำนาย | Playwright MCP | PASS |
| A5 · อินพุตผิด | Fixed · RB=0 | มีข้อความให้แก้ RB, เว็บไม่ล่ม, ไม่แสดงผลเดิมเป็นผลรอบนี้ | `Fixed Bias — RB must be greater than zero.` · ไม่มีตารางผล · status ยังเป็น `No calculation yet / READY` | Playwright MCP | PASS |

หมายเหตุ: ผลทั้ง 5 กรณีข้างต้นตรวจซ้ำด้วย OpenCode Browser ได้ค่าและข้อความตรงกันทุกกรณี

## 3. รายละเอียดผลที่อ่านได้ และส่วนต่าง

| เคส | IB | IC | IE | VB | VC | VE | VCE | Δ (KCL) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A1 | 12.299 µA | 1.230 mA | 1.242 mA | 1.942 V | 9.294 V | 1.242 V | 8.052 V | 2.22e−16 |
| A2 | 11.300 µA | 1.130 mA | 1.141 mA | 0.700 V | 9.514 V | 0.000 V | 9.514 V | 4.34e−19 |
| A3 | 10.263 µA | 1.026 mA | 1.037 mA | 1.737 V | 9.742 V | 1.037 V | 8.705 V | 4.34e−19 |
| A4 | 9.401 µA | 0.940 mA | 0.950 mA | 2.599 V | 9.932 V | 1.899 V | 8.033 V | 2.22e−16 |

| เคส | ΔIC (mA) | ΔVCE (V) | อยู่ในเกณฑ์ |
| --- | --- | --- | --- |
| A1 | +0.000142 | −0.000155 | ✅ |
| A2 | 0.000000 | 0.000000 | ✅ |
| A3 | −0.000340 | −0.000450 | ✅ |
| A4 | −0.000100 | +0.000221 | ✅ |

## 4. ข้อสังเกตจากผลจริง

- **A4 เทียบ A3**: เปลี่ยนเฉพาะ `RE` จาก 1 kΩ → 2 kΩ ทำให้ `IC` ลด 1.026 → 0.940 mA
  และ `VCE` ลด 8.705 → 8.033 V (ยังอยู่ใน active region)
- **A2 (Fixed)**: `VE = 0.000 V`, `VB = VBE = 0.700 V` ตามแบบจำลอง emitter ต่อกราวด์ตรง
- **A5**: ข้อความมาจาก Flask ('`RB must be greater than zero.`') แสดงในหน้าเว็บ พร้อมชื่อโหมด
  และไม่มีผลรอบก่อนค้างอยู่
- ทุกเคส A1–A4 แสดง `Active region approximation · OK · VCE > 0.2 V`
  console มีเพียง `404 /favicon.ico` (ไม่มี error จากแอป)

## 5. ไล่เส้นทางข้อมูล `RE` ใน A4 (ฟอร์ม → Flask → สมการ)

1. **ฟอร์ม** — `templates/index.html` โหมด Emitter มี
   `<input type="number" id="re" name="re" value="2000">` (หน่วย Ω)
2. **Browser** ส่ง `POST /` พร้อม `mode=emitter`, `re=2000` และช่องอื่นเท่ากับ A3
3. **`app.py:107–108`** — `values = {name: float(form[name]) for name in MODE_FIELDS[mode]}`
   → `values["re"] = 2000.0` (แปลงข้อความเป็นตัวเลขครั้งเดียวที่นี่)
4. **`app.py:114`** — `result = SOLVERS[mode](**values)` → `SOLVERS["emitter"] = analyze_emitter_bias`
5. **`bjt.py:227`** รับ `re` → **`bjt.py:231`**
   `ib = (vcc - vbe) / (rb + (beta + 1) * re)`
   ตัวหาร A3 = `1 MΩ + 101×1 kΩ = 1.101 MΩ`, A4 = `1 MΩ + 101×2 kΩ = 1.202 MΩ`
   → `IB` ตก 10.263 → 9.401 µA → `IC = β·IB` ตก 1.026 → 0.940 mA
6. **`bjt.py:234`** `ve = ie * re` และ `vce = vc - ve` → `VCE` 8.705 → 8.033 V

ถ้าค่า `RE` ไม่เปลี่ยนผล ให้ตรวจตามลำดับ: ค่าในช่องฟอร์ม → `name="re"` กับ `MODE_FIELDS["emitter"]` →
`float()` ใน `app.py` → ฟังก์ชันที่ `SOLVERS` เลือก → `(beta + 1) * re` ใน `bjt.py`

## 6. หลักฐานภาพ

ผล A1 ที่ได้จาก Playwright MCP (วิธีตรวจหลัก):

![ผล A1 จาก Playwright MCP](browser-a1-playwright.png)

ผล A1 จาก OpenCode Browser (รอบตรวจซ้ำ ผลตรงกัน):

![ผล A1 จาก OpenCode Browser](browser-a1.png)

## 7. การถดถอย Lab 2

ชุดทดสอบเดิมผ่าน **28/28** (`python -m unittest discover -v`) และอินพุตเดิม
`VCC=12, R1=47000, R2=10000, RC=4700, RE=1000, β=150, VBE=0.7` ยังให้
`IC = 1.324 mA`, `VCE = 4.446 V`, `ACTIVE`, `PASS` เหมือนเดิม

## 8. สิ่งที่ AI ช่วย / สิ่งที่ต้องตรวจเอง

- AI เขียน `analyze_fixed_bias`, `analyze_emitter_bias`, `_validate_inputs`, การเลือกโหมดใน `app.py`,
  ฟอร์มตามโหมด, `opencode.json` รัน A1–A5 ผ่าน Playwright MCP แล้วตรวจซ้ำด้วย OpenCode Browser
- สิ่งที่ตรวจจากสมการ Engineering Electronics: ตัวหาร `(β+1)RE`, `VE = 0` ใน Fixed,
  `IC = β·IB`, `VCE = VC − VE`, หน่วย Ω→A
- จุดแปลงหน่วย/เลือกฟังก์ชันอยู่ใน `app.py` (`MODE_FIELDS`, `SOLVERS`) ส่วนสมการอยู่ใน `bjt.py`
- **นักศึกษาทวนเอง 1 กรณีบนหน้าเว็บ** ตามข้อ 06–07 ของใบงาน (ยังไม่ได้ทำในเอกสารนี้)
