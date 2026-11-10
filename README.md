# BJT Common-Emitter DC Bias (ENG29 2121)

เว็บแอป Flask สำหรับคำนวณจุดการทำงาน DC (DC operating point) ของวงจรไบแอส
แบบ voltage divider ในทรานซิสเตอร์ BJT ต่อแบบ common-emitter

ให้ผลลัพธ์ IB, IC, IE, VB, VC, VE และ VCE พร้อมหน่วย, ตรวจสอบค่าอินพุต,
แจ้งเตือนเมื่อทรานซิสเตอร์อยู่นอกช่วง active (cutoff / saturation) และ
เปรียบเทียบผลกับ independent calculation ที่แก้ด้วย nodal analysis

## ขอบเขต

- คำนวณเฉพาะ DC bias ด้วย linear active-region model
- ไม่มี AC, transient, circuit editor หรือ FET
- เมื่อเข้า cutoff จะ clamp กระแสเป็นศูนย์และแจ้งเตือน
- เมื่อเข้า saturation จะแสดงผล linear ตามจริงพร้อมแจ้งเตือนว่า model ใช้ไม่ได้

## การติดตั้ง

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

## การรัน

```powershell
.venv\Scripts\python app.py
```

เปิด http://127.0.0.1:5000/ แล้วกรอกค่า VCC, R1, R2, RC, RE, β และ VBE

## การทดสอบ

```powershell
.venv\Scripts\python -m unittest discover -v
```

## ตัวอย่างอ้างอิง

| อินพุต | ค่า |
| --- | --- |
| VCC | 12 V |
| R1 | 47 kΩ |
| R2 | 10 kΩ |
| RC | 4.7 kΩ |
| RE | 1 kΩ |
| β | 150 |
| VBE | 0.7 V |

ผลลัพธ์: IC = 1.324 mA, VCE = 4.446 V, region = ACTIVE,
independent check = PASS

## โครงสร้างไฟล์

```
app.py                    Flask routes
bjt.py                    engineering logic (validation, solve, cross-check)
templates/                base + index page
static/style.css          styling
tests/test_bjt.py         engineering logic tests
tests/test_app.py         route and rendering tests
```
