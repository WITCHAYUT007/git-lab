# BJT Common-Emitter DC Bias (ENG29 2121) · Lab 3

เว็บแอป Flask ที่คำนวณจุดการทำงาน DC (DC operating point) ของทรานซิสเตอร์
NPN แบบ common-emitter ได้ 3 รูปแบบในหน้าเดียว:

- **Voltage Divider Bias** (วงจรเดิมจาก Lab 2 — ผลไม่เปลี่ยนเมื่อกรอกค่าเดิม)
- **Fixed Bias** (`RB` ต่อจาก VCC ไป Base, Emitter ต่อกราวด์ตรง ๆ)
- **Emitter Bias แบบแหล่งจ่ายเดียว** (`RB` ต่อ Base, `RE` ต่อ Emitter ลงกราวด์)

ผลลัพธ์: `IB`, `IC`, `IE`, `VB`, `VC`, `VE`, `VCE` พร้อมหน่วย, ตรวจสอบอินพุต,
แจ้งเตือนเมื่ออยู่นอกย่าน Forward Active และแสดงผลตรวจสอบสมการ (KCL/nodal) ของแต่ละโหมด

## ขอบเขต

- คำนวณเฉพาะ DC bias ด้วยแบบจำลอง active-region ที่ β และ VBE คงที่
- ไม่มี AC, transient, SPICE, DC load line, ตัวเก็บประจุ bypass หรือ circuit editor
- ถ้าคำนวณแล้ว `IB ≤ 0` หรือ `VCE ≤ 0.2 V` จะแสดงคำเตือนว่าแบบจำลองอาจใช้ไม่ได้
  (ไม่ได้จำลองค่าที่ถูกต้องใน cutoff/saturation สำหรับโหมดใหม่)
- อินพุตผิด (ไม่ใช่ตัวเลข, ไม่จำกัด, หรือค่าที่ต้องเป็นบวกแต่ ≤ 0) แสดงข้อความแก้ไขทันที
- หน่วยตัวต้านทานบนฟอร์มเป็น **Ω** (เช่น 100 kΩ = `100000`, 1 MΩ = `1000000`)

## การติดตั้ง

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

## การรัน

```powershell
.venv\Scripts\python app.py
```

หรือ

```powershell
python -m flask --app app run
```

เปิด http://127.0.0.1:5000/ เลือกวงจรในช่อง **Bias circuit** กด **Apply mode**
เพื่อโหลดฟอร์มของโหมดนั้น แล้วกรอกค่าแล้วกด **Calculate**

| โหมด | ช่องที่ใช้ |
| --- | --- |
| Voltage Divider Bias | `VCC`, `R1`, `R2`, `RC`, `RE`, `β`, `VBE` |
| Fixed Bias | `VCC`, `RB`, `RC`, `β`, `VBE` |
| Emitter Bias | `VCC`, `RB`, `RC`, `RE`, `β`, `VBE` |

## ตรวจผ่าน Browser (Lab 3)

`opencode.json` ตั้งค่า **Playwright MCP** ไว้แล้ว (OpenCode V2 · `mcp.servers.playwright`,
`type: local`, ใช้ Chrome แบบ isolated) หลังเพิ่ม/เปลี่ยน config ให้ปิด–เปิด OpenCode ครั้งหนึ่ง
แล้วตรวจว่า MCP เชื่อม (`/mcps` ใน V2) ขณะที่ Flask ต้องรันค้างอยู่

- เปิด `http://127.0.0.1:5000/` ด้วย Tools ของ Playwright MCP แล้วอ่าน snapshot
- เลือกโหมด → **Apply mode** → กรอกช่องตามตาราง → **Calculate DC Bias** → อ่าน snapshot ใหม่
- ผล A1–A5 ที่ตรวจจริงพร้อม screenshot อยู่ใน [`docs/validation.md`](docs/validation.md)
- ไม่ต้องติดตั้ง Playwright ใน `requirements.txt` (เป็น MCP server ไม่ใช่ dependency ของแอป)

## สมการที่ใช้

```
Fixed    · IB = (VCC − VBE) / RB
Emitter  · IB = (VCC − VBE) / [RB + (β + 1)RE]
Divider  · IB = (VTH − VBE) / [RTH + (β + 1)RE]
             VTH = VCC·R2/(R1+R2),  RTH = R1·R2/(R1+R2)

ทุกโหมด · IC = β·IB,  IE = (β+1)·IB
          VE = IE·RE (Emitter/Divider) หรือ 0 V (Fixed)
          VB = VE + VBE,  VC = VCC − IC·RC,  VCE = VC − VE
```

คำนวณด้วย Ω และ A ภายใน โชว์ `IB` เป็น µA, `IC`/`IE` เป็น mA และแรงดันเป็น V
(3 ตำแหน่งทศนิยม)

## การทดสอบ

```powershell
.venv\Scripts\python -m unittest discover -v
```

ชุดทดสอบจาก Lab 2 ยังใช้ได้ตามเดิม (ไม่เพิ่ม/ไม่ลบ) ผล Divider กับอินพุตเดิมต้องเป็น
`IC = 1.324 mA`, `VCE = 4.446 V`, `ACTIVE`, `PASS`

## ค่าอ้างอิงอิสระสำหรับการตรวจผ่าน Browser (A1–A5)

ใช้ร่วมกัน: `VCC = 12 V`, `RC = 2200 Ω`, `β = 100`, `VBE = 0.70 V`
เกณฑ์: |ΔIC| ≤ 0.01 mA และ |ΔVCE| ≤ 0.02 V เทียบกับค่าที่ยังไม่ปัดเศษ

| กรณี | อินพุต | IC คาดหมาย | VCE คาดหมาย |
| --- | --- | --- | --- |
| A1 | Divider · R1=100000, R2=22000, RE=1000 | 1.2299 mA | 8.0522 V |
| A2 | Fixed · RB=1000000 | 1.1300 mA | 9.5140 V |
| A3 | Emitter · RB=1000000, RE=1000 | 1.0263 mA | 8.7055 V |
| A4 | Emitter · RB=1000000, RE=2000 | 0.9401 mA | 8.0328 V |
| A5 | Fixed · RB=0 | ไม่มีผลคำนวณ | แจ้งว่า RB ต้อง > 0 |

A4: `IC` ต้อง **ลดลง** จาก A3 เพราะ `(β+1)RE` ในตัวหารเพิ่มขึ้น 1 kΩ → 2 kΩ

## โครงสร้างไฟล์

```
app.py                    เลือกโหมด ตรวจอินพุต แปลงหน่วย เรียกฟังก์ชัน และ render
bjt.py                    สมการและ validation ของทั้ง 3 วงจร (ไม่ import Flask)
templates/index.html      ฟอร์มตามโหมด ตารางผล ข้อความเตือน
static/style.css          styling
tests/                    ชุดทดสอบเดิมจาก Lab 2 (คงไว้)
electrical.py             เครื่องคิดเลข DC จาก Lab 1 (คงไว้)
docs/validation.md        ตารางผลจริง A1–A5 และหลักฐานจาก browser
```

## ส่วนที่ AI ช่วยสร้าง / สิ่งที่ตรวจ

- AI เขียน `analyze_fixed_bias`, `analyze_emitter_bias`, ฟังก์ชัน validation ร่วม
  `_validate_inputs`, การเลือกโหมดใน `app.py`, ฟอร์มตามโหมด และปรับ README นี้
- สิ่งที่ต้องตรวจจากสมการ Engineering Electronics: ตัวหาร `(β+1)RE` ใน Emitter/Divider,
  `VE = 0` ใน Fixed, `IC = β·IB`, `VCE = VC − VE`, และหน่วย Ω→A ที่จุดรับข้อมูล
- จุดเปลี่ยนหน่วย/เลือกฟังก์ชันอยู่ใน `app.py` (`MODE_FIELDS`, `SOLVERS`) ส่วนสมการอยู่ใน `bjt.py`
