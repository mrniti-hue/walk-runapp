# Walk & Run Community App — วงเวียนใหญ่ / ตลาดพลู

รายละเอียดสถาปัตยกรรม แผนงาน และบันทึกการตัดสินใจทั้งหมด อยู่ที่ `state-walkruncom.md`
**อ่านไฟล์นั้นก่อนเริ่มทำงานทุกครั้ง**

## เริ่ม dev แบบ local (Phase 1 skeleton)

ต้องมี Docker Desktop (พร้อม WSL2 backend) ติดตั้งไว้แล้ว

```bash
# 1. คัดลอก env file แล้วแก้ค่าตามจริง (อย่างน้อยต้องมีไฟล์นี้ให้ docker-compose อ่านได้)
cp backend/.env.example backend/.env

# 2. รันทั้งระบบ (Postgres + FastAPI พร้อม hot-reload)
docker-compose up --build

# 3. เช็คว่าใช้งานได้
curl http://localhost:8000/health
# ควรได้ {"status":"ok","env":"local"}
```

แก้โค้ดใน `backend/app/` แล้ว uvicorn จะ reload ให้เองอัตโนมัติ (bind mount ไว้แล้วใน docker-compose.yml)

## ทดสอบบนมือถือ / ทดสอบ OAuth callback (ต้องมี HTTPS URL สาธารณะ)

```bash
cloudflared tunnel --url http://localhost:8000
```

จะได้ URL แบบ `https://xxxx.trycloudflare.com` เอาไปเปิดบนมือถือ หรือใส่เป็น callback URL
ใน LINE Developers Console / Google Cloud Console ระหว่าง dev ได้เลย

## Migration (Alembic)

```bash
docker-compose exec api alembic revision --autogenerate -m "init tables"
docker-compose exec api alembic upgrade head
```

## รัน test

```bash
docker-compose exec api pytest
```

## โครงสร้าง repo

```
backend/   FastAPI app (app/core, app/models, app/schemas, app/api, app/services)
docs/      ผลสำรวจ checkpoint, เนื้อหาประวัติสถานที่
Gps/       เครื่องมือทดสอบ GPS accuracy หน้างาน (gps-spike.html)
state-walkruncom.md   สถานะโปรเจกต์แบบเต็ม — architecture, decision log, phase plan
```

## Deploy ขึ้น Railway

ยังไม่ตั้งค่า — จะทำตอนจบ Phase 1 skeleton แล้ว (ดู Phase 1 ใน state-walkruncom.md)
