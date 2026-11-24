# BJT Common-Emitter DC Bias + SPICE Amplifier Simulator (ENG29 2121) · Lab 3–4

เว็บแอป Flask ที่คำนวณจุดการทำงาน DC (DC operating point) ของทรานซิสเตอร์
NPN แบบ common-emitter ได้ 3 รูปแบบในหน้าเดียว:

- **Voltage Divider Bias** (วงจรเดิมจาก Lab 2 — ผลไม่เปลี่ยนเมื่อกรอกค่าเดิม)
- **Fixed Bias** (`RB` ต่อจาก VCC ไป Base, Emitter ต่อกราวด์ตรง ๆ)
- **Emitter Bias แบบแหล่งจ่ายเดียว** (`RB` ต่อ Base, `RE` ต่อ Emitter ลงกราวด์)

ผลลัพธ์: `IB`, `IC`, `IE`, `VB`, `VC`, `VE`, `VCE` พร้อมหน่วย, ตรวจสอบอินพุต,
แจ้งเตือนเมื่ออยู่นอกย่าน Forward Active และแสดงผลตรวจสอบสมการ (KCL/nodal) ของแต่ละโหมด

**Lab 4 เพิ่มส่วน Simulator ด้านล่าง:** เรียก ngspice จริงสำหรับ `.op`, `.ac`, `.tran`
ของวงจร CE voltage-divider (RE ไม่ bypass) แสดงกราฟ Bode/waveform ที่สร้างจาก
ผล solver, แยกป้าย **SPICE** กับ **Analytical (Lab 3)** และแสดง netlist + log จริง
Lab 3 ทั้ง 3 โหมดและผลเดิมยังใช้ได้เหมือนเดิม

## ขอบเขต

- Lab 3 คำนวณเฉพาะ DC bias ด้วยแบบจำลอง active-region ที่ β และ VBE คงที่
- Lab 4 จำลองเฉพาะวงจร CE reference ที่กำหนด (ไม่มี circuit editor, ไม่มี bypass cap,
  ไม่มี parameter sweep) และไม่มี analytical AC model ในแอป
- ไม่มี DC load line
- ถ้าคำนวณแล้ว `IB ≤ 0` หรือ `VCE ≤ 0.2 V` จะแสดงคำเตือนว่าแบบจำลองอาจใช้ไม่ได้
  (ไม่ได้จำลองค่าที่ถูกต้องใน cutoff/saturation สำหรับโหมดใหม่)
- อินพุตผิด (ไม่ใช่ตัวเลข, ไม่จำกัด, หรือค่าที่ต้องเป็นบวกแต่ ≤ 0) แสดงข้อความแก้ไขทันที
- หน่วยตัวต้านทานบนฟอร์มเป็น **Ω** (เช่น 100 kΩ = `100000`, 1 MΩ = `1000000`)

## การติดตั้ง

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

**ngspice (จำเป็นสำหรับ Lab 4)** — เครื่องนี้ใช้ไฟล์พกพา `tools/ngspice/ngspice_con.exe`
(ngspice 47) ซึ่งถูก ignore ใน git. ถ้า clone จาก GitHub ให้โหลด binary จาก
<https://ngspice.sourceforge.io/download.html> แล้วเลือกวิธีใดวิธีหนึ่ง:

```powershell
# วิธีที่ 1: วาง ngspice_con.exe ไว้ที่ tools/ngspice/
# วิธีที่ 2: ตั้ง environment variable ชี้ไปที่ executable ที่มีอยู่แล้ว
$env:NGSPICE_EXE = "C:\path\to\ngspice_con.exe"
```

ตรวจเวอร์ชันด้วย `& "$env:NGSPICE_EXE" --version` (หรือ `ngspice --version` ถ้าอยู่ใน PATH)

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

### ใช้ Simulator (Lab 4)

เลื่อนลงไปที่การ์ด **Common-Emitter Amplifier Simulator** แล้ว:

1. เลือก Analysis: `DC operating point (.op)` / `AC frequency response (.ac)` /
   `Transient waveform (.tran)`
2. กรอก **Amplitude (mV peak)** และ **Frequency (Hz)** — frequency ยังกำหนด
   ความยาวหน้าต่าง transient = 5 รอบด้วย
3. ปรับ `R1/R2/RC/RE/RL/Cin/Cout` หากต้องการ (ค่าเริ่มต้นเป็นวงจรอ้างอิง)
4. กด **Run simulation** → status เปลี่ยน `Ready → Running → Success/Error`

ผลที่ได้: ตาราง metric พร้อมหน่วย, กราฟ Bode (gain dB + phase deg vs Hz log)
หรือ waveform (Vin/Vout mV vs ms), ตารางเทียบ SPICE/Analytical, netlist ที่ส่งให้
ngspice และ solver log excerpt. ถ้า solver fail จะมีข้อความ error และ **ไม่แสดงผลเก่า**

## ตรวจผ่าน Browser (Lab 3)

`opencode.json` ตั้งค่า **Playwright MCP** ไว้แล้ว (OpenCode V2 · `mcp.servers.playwright`,
`type: local`, ใช้ Chrome แบบ isolated) หลังเพิ่ม/เปลี่ยน config ให้ปิด–เปิด OpenCode ครั้งหนึ่ง
แล้วตรวจว่า MCP เชื่อม (`/mcps` ใน V2) ขณะที่ Flask ต้องรันค้างอยู่

- เปิด `http://127.0.0.1:5000/` ด้วย Tools ของ Playwright MCP แล้วอ่าน snapshot
- เลือกโหมด → **Apply mode** → กรอกช่องตามตาราง → **Calculate DC Bias** → อ่าน snapshot ใหม่
- ผล A1–A5 ที่ตรวจจริงพร้อม screenshot อยู่ใน [`docs/validation.md`](docs/validation.md)
- ผล **B1–B8** ของ Lab 4 (DC/AC/Transient, error state, desktop/mobile) อยู่ใน
  [`docs/validation.md`](docs/validation.md) หัวข้อ 9–13
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
app.py                    เลือกโหมด Lab 3 + route /simulate ของ Lab 4
bjt.py                    สมการและ validation ของทั้ง 3 วงจร (ไม่ import Flask)
spice_engine.py           สร้าง netlist, เรียก ngspice ด้วย subprocess, parse .op/.ac/.tran
charts.py                 สร้าง SVG Bode/waveform จาก array ที่ parse ได้ (ไม่เพิ่ม dependency)
templates/index.html      ฟอร์ม Lab 3 + ส่วน simulator Lab 4
static/style.css          styling ทั้ง 2 แลป + responsive
opencode.json             ตั้งค่า Playwright MCP สำหรับตรวจผ่าน Browser
tests/                    ชุดทดสอบเดิมจาก Lab 2/3 (คงไว้ 28/28)
electrical.py             เครื่องคิดเลข DC จาก Lab 1 (คงไว้)
tools/ngspice/            ngspice portable (ignore ใน git — ต้องเตรียมเองตอน clone)
docs/validation.md        ผลจริง A1–A5 และ B1–B8 + หลักฐานจาก browser
```

## ส่วนที่ AI ช่วยสร้าง / สิ่งที่ตรวจ

- **Lab 3:** AI เขียน `analyze_fixed_bias`, `analyze_emitter_bias`, validation ร่วม
  `_validate_inputs`, การเลือกโหมดใน `app.py` และฟอร์มตามโหมด
- **Lab 4:** AI เขียน `spice_engine.py`, `charts.py`, route `/simulate`, ส่วน UI simulator,
  และปรับ README นี้； โหลด ngspice แบบพกพา + ติดตั้ง Impeccable skill ตามที่อนุมัติ
- **Impeccable:** ใช้ context/craft-floor/polish + detector ก่อน–หลัง (1280×800 และ
  390×844) แก้ contrast `status-flag` 4.4:1 → ผ่าน, ยุบ nested cards, เปลี่ยน
  error/warning เป็น full border — ผล Detector รอบสุดท้าย `[]` ทั้ง 2 viewport
- สิ่งที่ต้องตรวจจากสมการ Engineering Electronics: ตัวหาร `(β+1)RE` ใน Emitter/Divider,
  `VE = 0` ใน Fixed, `IC = β·IB`, `VCE = VC − VE`, และหน่วย Ω→A ที่จุดรับข้อมูล
- **นักศึกษาต้องทวนเอง 1 กรณีบนหน้าเว็บ** ตามข้อ 06–07 ของใบงาน Lab 3 (แนะนำ A4)
  และควรตรวจด้วยตาว่ากราฟ Bode/waveform ที่ได้ตรงกับการตีความทางวงจร

## ส่งงาน (Submission)

- **GitHub:** https://github.com/WITCHAYUT007/git-lab
- **Commit SHA · โค้ด Lab 3:** `f56b0a1` — `feat: add fixed/emitter bias modes and reference-style UI`
- **Commit SHA · หลักฐานและ MCP:** `bca8829` — `docs: add Playwright MCP config and browser validation evidence`
- **Commit SHA · โค้ด Lab 4:** `7e3a7ba9d5747f566c9069bca106314b1d9c3242` — `feat: add ngspice CE amplifier simulator with AC/transient plots (Lab 4)`
- ตรวจ SHA ของ HEAD ได้ด้วย `git rev-parse HEAD`
- หลักฐาน A1–A5 และ B1–B8 รวมภาพหน้าจอ: [`docs/validation.md`](docs/validation.md)
