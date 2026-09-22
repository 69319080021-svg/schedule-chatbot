# ผู้ช่วยตารางสอนอาจารย์

บอทตอบคำถามตารางสอนของอาจารย์ในแผนก (เว็บแอป, FastAPI + Gemini API)

## ติดตั้ง

```bash
pip install -r requirements.txt
```

คัดลอก `.env.example` เป็น `.env` แล้วกรอกค่า:

```bash
GEMINI_API_KEY=...
ADMIN_PASSWORD=รหัสผ่านสำหรับหน้าอัปโหลด
SESSION_SECRET=สตริงสุ่มยาวๆ
```

## รัน

```bash
uvicorn app.main:app --reload
```

เปิดเบราว์เซอร์ที่ `http://127.0.0.1:8000`

- หน้าแรก (`/`) — ถาม-ตอบตารางสอน เปิดสาธารณะ ไม่ต้อง login
- `/admin/login` — เข้าสู่ระบบแอดมิน (ใช้ `ADMIN_PASSWORD`)
- `/admin/upload` — อัปโหลด PDF ตารางสอนใหม่ ระบบจะใช้ Gemini อ่านและแปลงเป็นข้อมูล แล้วให้ตรวจสอบ/แก้ไขก่อนบันทึกจริงที่หน้า `/admin/review`

## โครงสร้างข้อมูล

ข้อมูลตารางสอนทั้งหมดเก็บเป็น JSON ไฟล์เดียวที่ `data/schedules.json` (list ของอาจารย์แต่ละคน)
