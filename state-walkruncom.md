# Walk & Run Community App — State & Decision Log

อัปเดตล่าสุด: 2026-08-28
อ่านไฟล์นี้ก่อนเริ่มทำงานทุกครั้ง ตามที่ README บอกไว้ — นี่คือความจำโครงการที่ไม่ได้อยู่ในโค้ดหรือ git log ตรงๆ

---

## 1. โปรเจกต์นี้คืออะไร

แอปเดินท่องเที่ยวชุมชนแบบ checkpoint (คล้าย scavenger hunt เชิงประวัติศาสตร์) พื้นที่เริ่มต้น: วงเวียนใหญ่ / ตลาดพลู
ผู้เล่นลงทะเบียนเป็น**ทีม 2-4 คน** เดิน/ปั่นจักรยานไปตามจุด checkpoint ที่มีเนื้อหาประวัติศาสตร์ให้อ่าน เช็คอินด้วย GPS จริง

**Scale**: ~200 concurrent users ต่อ event, event จัดเป็นครั้งๆ ไม่ใช่ระบบสมาชิกถาวร

---

## 2. สถาปัตยกรรม

```
backend/   FastAPI (async SQLAlchemy + asyncpg + Postgres 16/18) + Alembic migrations
  app/models/      Community, Team, TeamMember, Checkpoint, CheckpointClaim,
                   CheckpointProgress, MemberPosition
  app/services/    pure logic, ไม่แตะ DB — geo.py (haversine), passkey.py (gen/hash/verify),
                   checkpoint_rules.py (accuracy/radius/dwell/quorum)
  app/api/         teams.py (register/login/me-status/me-position), checkpoints.py (list/claim)
  app/static/      participant test client — HTML/JS ตัวเดียว + Leaflet map (ดูหัวข้อ 6)
docker-compose.yml  Postgres + FastAPI container (ต้องมี Docker Desktop)
```

**Multi-tenant จากวันแรก**: ทุกตารางหลักผูกกับ `community_id` เผื่อขยายไปพื้นที่อื่นในอนาคต ไม่ใช่ over-engineering ที่ไม่จำเป็น — มีอยู่แล้วตั้งแต่ commit แรก (`d7184c5`)

---

## 3. Auth model: Team + Passkey (ไม่ใช่ OAuth)

**เดิม** (`d7184c5`) ออกแบบเป็น OAuth (LINE Login / Google) กับ `User` model เดี่ยว
**เปลี่ยนเป็น** Team/Passkey ที่ commit `1004c16` เพราะ:

- ผู้ใช้ลงทะเบียนเป็น**ทีม** ไม่ใช่บุคคลเดี่ยว (ทีมละ 2-4 คน มีชื่อ+อายุ)
- 200 concurrent ไม่จำเป็นต้องมี OAuth ซับซ้อน — ตัด LINE/Google callback, ตัด cloudflared tunnel ที่ต้องเปิดแค่ตอน dev OAuth ออกไปเลย (ยังใช้ cloudflared อยู่ แต่เพื่อทดสอบ GPS จริง ไม่ใช่ OAuth callback)
- **สมาชิกแต่ละคนได้ passkey ของตัวเอง** ไม่ใช่ key เดียวใช้ร่วมกันทั้งทีม — เหตุผลสำคัญ: ถ้าใช้ key เดียวกัน server จะแยกไม่ออกว่า GPS ที่ส่งเข้ามาเป็นของใคร ทำให้ off-route detection และ quorum anti-cheat (ข้อ 4) ทำไม่ได้เลย
- Passkey hash เป็น sha256+pepper แบบ **deterministic** (ไม่ใช่ bcrypt) เพราะ login ต้องเป็น indexed lookup ตรงๆ ไม่ใช่ scan-and-verify — passkey เป็น random สุ่มความ entropy สูงอยู่แล้ว ไม่ใช่ password ที่ user ตั้งเอง จึงไม่ต้องพึ่ง bcrypt's brute-force resistance
- `PASSKEY_PEPPER` ใน `.env` — **ห้ามเปลี่ยนระหว่างจัดงาน** เปลี่ยนแล้ว passkey ที่แจกไปแล้วทั้งหมดใช้ไม่ได้ทันที

---

## 4. Anti-cheat: Quorum + Dwell (หัวใจของระบบ)

ปัญหาหลักที่ต้องป้องกัน: **ทีมแยกกันเดิน** แล้วแต่ละคนไปเก็บ checkpoint คนละจุดพร้อมกัน จบเร็วกว่าทีมที่เดินด้วยกันจริง

**ชั้นการตรวจสอบ** (`app/services/checkpoint_rules.py`, ทั้งหมด unit test ได้โดยไม่แตะ DB):

1. **Accuracy check ก่อน** — ถ้า GPS accuracy หยาบกว่า `max_accuracy_m` (default 50m) ปฏิเสธทันที ไม่เช็คระยะทางต่อ
2. **Radius check** — haversine distance ต้องไม่เกิน `radius_m` ของ checkpoint (fallback `default_radius_m` = 40m)
3. **Dwell time** — ต้องอยู่ในรัศมีต่อเนื่อง `dwell_seconds` (default 45s) ถึงจะนับว่า "มาถึงจริง" ไม่ใช่แค่ผ่านหน้าบ้าน — ทน gap สัญญาณหลุดได้ในระดับหนึ่ง (`gap_tolerance_seconds`)
4. **Quorum** — checkpoint จะ complete ก็ต่อเมื่อมีสมาชิก ≥ `quorum_min_members` (default 2) dwell ครบ **พร้อมกันในกรอบเวลาเดียว** (`quorum_window_seconds`, default 300s) ไม่ใช่แค่ "มาครบทุกคนสักวันหนึ่ง" — นี่คือจุดที่กันทีมแยกกันเดินได้จริง (unit test: `test_quorum_not_met_when_team_splits_up`)

**จุดสำคัญ**: dwell/quorum คำนวณจาก **`received_at` (นาฬิกา server ตอนรับ request)** ไม่ใช่ `reported_at` (นาฬิกาเครื่อง client) — เพราะ client ปลอมนาฬิกาตัวเองได้ ถ้าใช้ `reported_at` จะโกง dwell time ได้ง่ายๆ `reported_at` เก็บไว้แค่เป็น audit trail เทียบดูความเพี้ยนของนาฬิกาเครื่อง ไม่ใช้ตัดสินใจอะไร

**ไม่ได้ทำ (ยอมรับข้อจำกัด)**: GPS spoofing ระดับ root/mock-location-app กันไม่ได้จริงในชั้น client เป้าหมายคือ "ทำให้โกงแบบขำๆ ไม่สะดวกและตรวจพบได้" ไม่ใช่กัน 100% — ถ้างานมีรางวัลใหญ่ต้องคุยเพิ่มเรื่อง speed-anomaly flag ให้ staff ตรวจสอบ (ยังไม่ implement)

**ไม่มี PostGIS** — ใช้ lat/lng ธรรมดา + haversine ใน service layer เพราะจำนวน checkpoint น้อยและ `postgres:16-alpine` ไม่มี PostGIS ติดมา ไม่คุ้มเพิ่ม dependency

---

## 5. Local dev environment (สำคัญ — เครื่องนี้ไม่มี Docker)

**เครื่อง BAANFRESH ไม่มี Docker Desktop ติดตั้ง** ใช้วิธีนี้แทน `docker-compose up` ตาม README:

- Python 3.14 venv ที่ `backend/.venv` + PostgreSQL 18 (local service, ไม่ใช่ container)
- `backend/.env` ชี้ `DATABASE_URL` ไปที่ `localhost` แทน `db` (hostname ของ Docker network)
- **Python 3.14 ยังไม่มี wheel สำเร็จรูปสำหรับ `asyncpg`, `pydantic-core`, `sqlalchemy` บางเวอร์ชัน** (ต้องคอมไพล์ C/Rust ซึ่งเครื่องนี้ไม่มี MSVC Build Tools) — แก้โดยอัปเกรดสามแพ็กเกจนี้เฉพาะใน venv local (`asyncpg>=0.31`, `pydantic>=2.11`, `sqlalchemy>=2.0.43`) ส่วน `requirements.txt` ในโปรเจกต์ยังคง pin เวอร์ชันเดิมไว้เพื่อ Docker build (Python 3.12) ไม่กระทบ
- สร้าง DB role/database ด้วย `backend/scripts/create_local_db.sql` (รันครั้งเดียวโดย postgres superuser)
- Seed ข้อมูลทดสอบ: `backend/scripts/seed_local_community.sql` (community `talat-phlu`), `backend/scripts/seed_local_checkpoint.sql` (2 จุดทดสอบ: วัดอรุณ, วัดโพธิ์ — เป็นพิกัดจริงแต่ไม่ใช่เส้นทางจริงของตลาดพลู)

**รันเซิร์ฟเวอร์**:
```bash
cd backend
.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**ทดสอบ GPS จริงบนมือถือ** — geolocation API ต้องการ HTTPS (ยกเว้น localhost) จึงต้องเปิด tunnel:
```bash
cloudflared tunnel --url http://localhost:8000
```
ติดตั้งผ่าน `winget install --id Cloudflare.cloudflared -e` (ทำไปแล้วบนเครื่องนี้) URL จาก tunnel เปลี่ยนทุกครั้งที่เปิดใหม่ — ไม่เหมาะกับการแชร์ระยะยาว เหมาะกับทดสอบเองช่วงสั้นๆ เท่านั้น

**ถ้าเครื่องมี Docker Desktop** ให้ใช้ `docker-compose up --build` ตาม README ปกติแทนวิธีข้างบนทั้งหมด — pin เวอร์ชันใน `requirements.txt` จะทำงานได้ตรงๆ ไม่ต้องแก้อะไร

---

## 6. Participant test client (`backend/app/static/index.html`)

**ไม่ใช่แอปจริงของ Phase 3** (README ระบุ web/ จะทำใน Phase 3 ด้วย Vite) — นี่คือ throwaway test harness ใช้ยืนยันว่า backend flow ทำงานถูกต้องจริงจาก browser มือถือ ไม่ใช่แค่ curl

Single HTML file, เสิร์ฟจาก FastAPI เอง (`app.mount("/app", StaticFiles(...))`) — same-origin กับ API เลยไม่ต้องตั้ง CORS

Features: login ด้วย passkey → แผนที่จริง (Leaflet + OpenStreetMap ฟรี ไม่ต้อง API key) แสดง checkpoint เขียว/แดง (ผ่านแล้ว/ยังไม่เจอ) → เช็คอินจากลิสต์หรือจาก popup บนแผนที่ → ตำแหน่งตัวเองอัปเดตแบบเรียลไทม์ผ่าน `watchPosition()` (ไม่ใช่แค่ตอนกดเช็คอิน) พร้อม pulse animation, push ขึ้น server ทุก 10s (throttle) ผ่าน `POST /teams/me/position` ที่แยกจาก `/claim` เพราะจุดประสงค์ต่างกัน (position ping = แค่บันทึกตำแหน่ง, claim = ประเมิน accuracy/radius/quorum)

**Test credentials ที่ seed ไว้ในเครื่อง local** (ทีม "ทีมทดสอบ", community `talat-phlu`):
- Alice: `3E8XWQGKD8`
- Bob: `AKHN9S39NB`

---

## 7. สถานะ Phase 1 — ทำอะไรไปแล้ว / ยังไม่ได้ทำ

**เสร็จแล้ว**:
- Schema เต็ม (Community/Team/TeamMember/Checkpoint/CheckpointClaim/CheckpointProgress/MemberPosition) + migrations
- Service layer anti-cheat logic พร้อม unit test (17 tests ผ่าน)
- API: register team, login, list checkpoints, claim checkpoint, team status, live position ping
- ทดสอบ end-to-end จริงผ่าน browser (รวม quorum completion จริง, ไม่ใช่แค่ mock)
- Participant test client พร้อมแผนที่ + live tracking

**ยังไม่ได้ทำ**:
- ข้อมูล checkpoint จริงของตลาดพลู/วงเวียนใหญ่ (ตอนนี้เป็นข้อมูลทดสอบ วัดอรุณ/วัดโพธิ์) — README พูดถึงโฟลเดอร์ `docs/` (ผลสำรวจ) และ `Gps/` (ทดสอบ accuracy) แต่**ยังไม่มีอยู่จริงในโปรเจกต์**
- Rate limiting / anti-spam บน `/checkpoints/{id}/claim` และ `/teams/me/position`
- เครื่องมือ staff/admin (ดูสถานะทุกทีม, ค้นหา/ส่ง passkey ซ้ำ, mark ทีมเริ่ม/จบ — `Team.status` field มีอยู่แล้วแต่ไม่มี endpoint เปลี่ยนค่า)
- Speed-anomaly detection (คุยไว้ตอนออกแบบ anti-cheat แต่ยังไม่ implement)
- Railway deploy — **ตั้งใจรอจนจบ Phase 1 skeleton** ตาม README เดิม
- Git remote: `https://github.com/mrniti-hue/walk-runapp` (push แล้วถึง commit ล่าสุด)

---

## 8. Decision log (ย่อ เรียงเวลา)

| Commit | การตัดสินใจ | เหตุผล |
|---|---|---|
| `1004c16` | เปลี่ยน OAuth → Team/Passkey | ผู้ใช้จริงลงทะเบียนเป็นทีม ไม่ใช่บุคคล, ต้องการ per-member identity สำหรับ anti-cheat |
| `bcdc0db` | Service layer แยกจาก DB/HTTP | quorum logic คือจุดเสี่ยงสูงสุด ต้อง unit test ได้ตรงๆ |
| `b71bc15` | ใช้ `received_at` ไม่ใช่ `reported_at` สำหรับ dwell/quorum | client ปลอมนาฬิกาตัวเองได้ |
| `b71bc15` | เพิ่ม `quorum_window_seconds` ใน Community | ลืมใส่ตอนออกแบบ schema ครั้งแรก จำเป็นสำหรับ quorum ทำงานถูกต้อง |
| `51463d7`, `dbd859e`, `de8234e` | ทำ test client + map + live tracking | ต้องทดสอบ flow จริงจากมือถือ ไม่ใช่แค่ curl |
| (session นี้) | ใช้ cloudflared tunnel แทน VPS/Railway สำหรับทดสอบตอนนี้ | ต้องการแค่ HTTPS ชั่วคราวทดสอบ GPS ไม่ใช่ deploy ถาวร — Railway ตั้งใจรอจนจบ Phase 1 |
