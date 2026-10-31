# แผนงาน: ย้าย UI บางหน้าจาก PySide6 (Desktop) สู่ Web (Read-Only)

## 0. เป้าหมายและขอบเขต (Scope)

**เป้าหมาย:** นำ 2 หน้าจากโปรแกรม Desktop ขึ้นเว็บ แบบ **"ดูอย่างเดียว" (Read-Only)**
โดยใช้ data layer เดิม (`data/`) ทั้งหมด ไม่แก้ไข

**หน้าที่จะย้าย:**
- [ ] หน้า "แผนการศึกษารายเทอม" (Table) — ทำก่อน
- [ ] หน้า "หมวดวิชา" (Tree View) — ทำทีหลัง

**สิ่งที่ "ยังไม่ทำ" ในรอบนี้ (กันหลงประเด็น):**
- ❌ **ไม่มี Create / Update / Delete บนเว็บ** — ทุกหน้าคือ GET แสดงผลอย่างเดียว
- ❌ ไม่มีฟอร์ม, ไม่มีปุ่มเพิ่ม/แก้/ลบ, ไม่มี POST route ใดๆ ทั้งสิ้น
- ❌ การแก้ไขข้อมูลยังคงทำผ่านโปรแกรม Desktop (PySide6) เดิมเท่านั้น
- ❌ ไม่เปลี่ยนฐานข้อมูลเป็น PostgreSQL (SQLite พอสำหรับตอนนี้)
- ❌ ไม่ทำระบบ Login/Authentication
- ❌ ไม่ทำ Production server (Gunicorn/Uvicorn + Nginx)
- ❌ ไม่ทำ Frontend แยก (React/Vue) — ใช้ Jinja2 พอ
- ❌ ไม่ต้องรองรับ mobile responsive แบบสมบูรณ์ในรอบแรก
- ❌ ไม่เพิ่มฟังก์ชันใหม่ใน `repository.py` ในรอบแรก (ของเดิมครอบคลุมพอแล้ว)

> กติกา: ถ้าอยากทำอะไรนอกเหนือจากลิสต์ข้างบน ให้จดไว้ใน "Backlog" ท้ายเอกสารนี้ อย่าทำแทรกกลางทาง

> ⚠️ **ผลจาก Read-Only:** งานเล็กลงมาก เพราะใช้แค่ฟังก์ชัน `list_*` / `get_*` ใน `repository.py`
> ไม่ต้องแตะฟังก์ชัน `create_*` / `update_*` / `delete_*` เลยแม้แต่ตัวเดียว
> และไม่ต้องทำ template ฟอร์ม, ไม่ต้องมี `python-multipart`, ไม่ต้องกังวลเรื่อง CSRF

---

## 1. ข้อมูลจริงที่ต้องรู้ก่อนออกแบบ (ล็อกไว้แล้ว)

- มี **2 หลักสูตร** ในระบบ → ต้องมีหน้าเลือกหลักสูตร ห้าม hardcode
- มี **1 หมวดวิชาศึกษาทั่วไป** ใช้ร่วมกันทั้ง 2 หลักสูตร (`curriculum_id IS NULL` ที่ระดับ `CourseGroup`)
  → `list_courses_for_curriculum()` และ `list_course_groups()` ของเดิม รองรับ pattern นี้อยู่แล้ว ไม่ต้องเขียน logic พิเศษ
- `recommended_semester` มีค่า **1, 2, 3** โดย:
  - ส่วนใหญ่เป็น 1 หรือ 2
  - มีแค่ 2 วิชาทั้งระบบที่เป็นเทอม 3 (ภาคฤดูร้อน): `01006004 การฝึกงานอุตสาหกรรม` และ `05366090 ฝึกงาน`
  → ต้อง handle แบบ sparse ไม่ทำคอลัมน์เทอม 3 แยกเต็มรูปแบบ (ดู Phase 3)

---

## 2. การตัดสินใจทางเทคนิค (ล็อกไว้ ห้ามเปลี่ยนกลางทาง)

| หัวข้อ | เลือก | เหตุผล |
|---|---|---|
| Web Framework | **Flask** | เบา, เรียนรู้ง่าย, เหมาะกับโปรเจกต์ read-only ขนาดเล็ก |
| Template Engine | **Jinja2** (built-in มากับ Flask) | ใกล้เคียงของเดิม ไม่ต้องเขียน JS เยอะ |
| Database | **SQLite (เดิม)** | ยังไม่มี concurrent user เยอะ |
| Session Pattern | **เปิด-ปิดต่อ request** ผ่าน Flask `g` object + `app.teardown_appcontext()` | ต่างจาก Desktop ที่เปิดค้างไว้ |
| Route Organization | **Flask Blueprint** (`Blueprint(...)`) | วิธีมาตรฐานของ Flask ในการแยก route เป็นกลุ่ม |
| CSS | **plain CSS หรือ Bootstrap (CDN)** | ไม่ต้องตั้ง build tool |
| Tree View | **HTML `<details>/<summary>` + Jinja2 recursive macro** | `get_group_tree()` คืน dict พร้อมใช้อยู่แล้ว ไม่ต้องพึ่ง jsTree |
| เทอมฤดูร้อน (sem 3) | **แสดงแยกเป็น list ท้ายตารางของปีนั้น** ไม่ทำคอลัมน์ที่ 3 | มีข้อมูลแค่ 2 วิชา ทำคอลัมน์เต็มจะว่างเปล่าเกินจำเป็น |
| **Mode** | **Read-Only ทั้งระบบ** | การแก้ไขทำผ่าน Desktop app เดิมเท่านั้น เว็บมีไว้ดูข้อมูล |

---

## 3. โครงสร้างโฟลเดอร์เป้าหมาย

```
project/
├── data/                  # ห้ามแก้ ของเดิมทั้งหมด
│   ├── models.py
│   ├── database.py
│   └── repository.py
├── app/                   # Desktop UI เดิม (PySide6) — คงไว้ไม่ลบ ยังใช้แก้ไขข้อมูลอยู่
│   └── ...
└── web/                   # ★ ส่วนใหม่ที่จะสร้าง (Read-Only)
    ├── main.py            # Flask app + register blueprints + get_db()/close_db() (ทำเสร็จแล้วใน Phase 2)
    ├── blueprints/
    │   ├── curriculum.py  # Blueprint: เลือกหลักสูตร + หน้าแผนการศึกษา (GET เท่านั้น)
    │   └── group.py       # Blueprint: หน้าหมวดวิชา (GET เท่านั้น)
    ├── templates/
    │   ├── base.html
    │   ├── curriculum_list.html
    │   ├── plan_table.html
    │   └── group_tree.html
    └── static/
        └── style.css
```

> 📝 หมายเหตุ: ไม่มีไฟล์ `dependencies.py` แยก เพราะ Flask ใช้ `g` object + `teardown_appcontext()` ตรงๆ ใน `main.py` ได้เลย (ตามที่ Phase 2 ทำสำเร็จไปแล้ว) ไม่ใช่ pattern แบบ FastAPI `Depends()`

---

## 4. Phase 1 — โครงกระดูก (Skeleton) [เป้าหมาย: run ได้ ยังไม่มี logic]

**Checklist:**
- [x] ติดตั้ง `flask` (Jinja2 มากับ Flask อยู่แล้ว ไม่ต้องแยกติดตั้ง)
- [x] สร้างโฟลเดอร์ `web/` ตามโครงสร้างข้อ 3
- [x] เขียน `main.py` ที่ run แล้วเห็นหน้า "Hello" ผ่าน browser ได้
- [x] เขียน `templates/base.html` เป็นโครง HTML เปล่า (header/footer/nav) — ไม่มีปุ่ม action ใดๆ

**Definition of Done:** เปิด `http://localhost:5000` แล้วเห็นหน้าเปล่าๆ ที่ render จาก Jinja2 ได้ ไม่ error

---

## 5. Phase 2 — Session Management [หัวใจสำคัญที่สุด ทำก่อนแตะ repository] ✅ เสร็จแล้ว

**Checklist:**
- [x] เขียนฟังก์ชัน `get_db()` ใน `main.py` ที่ใช้ Flask `g` เก็บ session ต่อ request
- [x] เขียน `close_db()` แล้วลงทะเบียนผ่าน `app.teardown_appcontext(close_db)`
- [x] ทดสอบ inject session เข้า route ตัวอย่าง (`/test-curricula`) แล้ว query `list_curricula()` มาแสดงเป็นข้อความ — ทำงานได้
- [x] ยืนยันว่า session ปิดจริง (ไม่มี connection ค้าง) — ทดสอบด้วยการรีเฟรชหลายครั้ง ไม่เจอ "database is locked" แล้ว

**Definition of Done:** ✅ ผ่านแล้ว — `/test-curricula` ดึงข้อมูลจริงจาก SQLite ผ่าน `repository.py` มาโชว์ได้ปกติ ไม่มี error

> 📝 **บันทึกปัญหาที่เจอระหว่างทาง:** เคยมีไฟล์ `code.py` อยู่ใน `project/` ที่ชื่อชนกับ Python standard library module `code` ทำให้ Flask debug mode import ผิดไฟล์แล้ว error กระทันหัน — แก้โดยลบ/เปลี่ยนชื่อไฟล์ที่ชนกับ built-in module ชื่อ (จำไว้เป็น checklist: **ห้ามตั้งชื่อไฟล์ว่า `code.py`, `types.py`, `test.py` ฯลฯ ที่ชนกับ stdlib**)

---

## 6. Phase 3 — หน้า "แผนการศึกษารายเทอม" (Table) — Read-Only  ⬅️ **กำลังทำอยู่ตรงนี้**

**สถานะ:** Phase 2 ผ่านแล้ว (session ทำงานถูกต้อง, มี route ทดสอบ `/test-curricula` แล้ว)
ยังไม่เริ่มสร้างหน้าตาราง/route จริงตาม mapping ด้านล่าง — checklist ทั้งหมดยังไม่ติ๊ก

**เหตุผลที่ทำก่อน:** เป็น HTML table ธรรมดา ไม่ซับซ้อนเท่า tree จะได้เห็นผลเร็วว่าทั้งระบบต่อกันได้จริง

### Route Mapping (เฉพาะ GET เท่านั้น — ใช้ฟังก์ชัน `list_*`/`get_*` เดิม, ใน Blueprint `curriculum.py`)

| Route (Flask syntax) | Method | เรียกฟังก์ชัน |
|---|---|---|
| `/` หรือ `/curricula` | GET | `list_curricula(session)` → หน้าแสดง 2 หลักสูตรให้เลือก |
| `/curricula/<int:curriculum_id>/plan` | GET | `get_curriculum(session, curriculum_id)` + `list_courses_for_curriculum(session, curriculum_id)` |

> ไม่มี route POST/PUT/DELETE ใดๆ ในหน้านี้

### Layout ตาราง (ตัวเลือก A — ล็อกแล้ว)

ตารางหลักแสดงเทอม 1/2 ตามปกติ แยกตามปี ส่วนวิชาที่ `recommended_semester == 3`
(มีแค่ 2 วิชา) แสดงแยกเป็น "รายวิชาภาคฤดูร้อน" ท้ายตาราง ไม่ทำคอลัมน์ที่ 3

**Logic การจัดกลุ่มใน route (ก่อนส่งเข้า Jinja2):**

```python
courses = repo.list_courses_for_curriculum(session, curriculum_id)

by_year = {}           # {year: {1: [...], 2: [...]}}
summer_courses = []     # semester == 3 ทั้งหมด รวมทุกปี

for link in courses:
    course = repo.get_course(session, link.course_code)
    row = {"course": course, "link": link}
    if link.recommended_semester == 3:
        summer_courses.append(row)
    else:
        by_year.setdefault(link.recommended_year, {1: [], 2: []})
        by_year[link.recommended_year][link.recommended_semester].append(row)
```

**Checklist ย่อยตาม flow:**
- [ ] หน้าเลือกหลักสูตร (2 ตัว) ก่อนเข้าหน้าตาราง
- [ ] แสดงตารางแผนการเรียนแยกปี/เทอม + วิชาฤดูร้อนแยกท้ายตาราง
- [ ] ทดสอบว่าหมวดศึกษาทั่วไปแสดงปนอยู่ในตารางถูกต้อง (ไม่ต้อง filter อะไรพิเศษ เพราะ query เดิมรองรับอยู่แล้ว)
- [ ] ทดสอบดูข้อมูลทั้ง 2 หลักสูตร ว่าตารางถูกต้องตรงกับที่มีใน Desktop app

**Definition of Done:**
- เลือกหลักสูตรจาก 2 ตัวได้
- เห็นตาราง ปี 1-4 × เทอม 1-2 ปกติ
- เห็นวิชาเทอม 3 (2 วิชา) แสดงแยกต่างหากชัดเจน
- **ไม่มีปุ่มหรือฟอร์มใดๆ ให้แก้ไขข้อมูลบนหน้านี้**

---

## 7. Phase 4 — หน้า "หมวดวิชา" (Tree View) — Read-Only

**ข่าวดี:** มีฟังก์ชัน `get_group_tree(session, curriculum_id)` ที่คืนโครงสร้าง tree
เป็น `List[Dict]` (พร้อม `children` ซ้อนกัน + `courses` ในแต่ละหมวด) อยู่แล้ว
→ ไม่ต้องเขียน logic ประกอบ tree เองใน route เลย แค่ render dict นี้เป็น HTML

**หมวดศึกษาทั่วไป:** `list_course_groups(curriculum_id=X)` query แบบ
`curriculum_id == X OR curriculum_id IS NULL` อยู่แล้ว → หมวดศึกษาทั่วไปจะโผล่ในทั้ง 2 หลักสูตรอัตโนมัติ ไม่ต้องแก้อะไร

### Route Mapping (เฉพาะ GET เท่านั้น, ใน Blueprint `group.py`)

| Route (Flask syntax) | Method | เรียกฟังก์ชัน |
|---|---|---|
| `/curricula/<int:curriculum_id>/groups` | GET | `get_group_tree(session, curriculum_id)` |

> ไม่มี route สำหรับเพิ่ม/แก้/ลบ node ใดๆ

**Checklist:**
- [ ] แสดง tree แบบ read-only ด้วย Jinja2 recursive macro
- [ ] expand/collapse ด้วย `<details><summary>` (ไม่ต้องพึ่ง JS)
- [ ] ทดสอบว่าหมวดศึกษาทั่วไปแสดงถูกต้องในทั้ง 2 หลักสูตร

**Definition of Done:** หน้า tree แสดงโครงสร้างหมวดวิชาถูกต้องครบถ้วน เปิด/ปิดดูได้ **ไม่มีการแก้ไขใดๆ บนเว็บ**

---

## 8. Phase 5 — Polish (ทำเมื่อ Phase 1-4 เสร็จหมดแล้วเท่านั้น)

- [ ] ปรับ CSS ให้ดูดีขึ้น
- [ ] พิจารณาว่า query แบบ N+1 (เรียก `get_course()` วนลูปใน Phase 3) ช้าเกินไปหรือไม่ ถ้าใช่ค่อยเพิ่มฟังก์ชัน join ใหม่ใน repository.py (ยังคงเป็นแค่ read function)
- [ ] (ถ้าจำเป็นจริงๆ ในอนาคต) เริ่มคุยเรื่อง Auth / Production server — **ไม่รวมการเปิดสิทธิ์แก้ไขบนเว็บ** เว้นแต่จะมีการตัดสินใจใหม่อย่างชัดเจน

---

## 9. Backlog (ไอเดียที่เกิดขึ้นระหว่างทาง แต่ยังไม่ทำตอนนี้)

<!-- จดไว้ตรงนี้ อย่าทำแทรก -->
-
-

---

## หมายเหตุการทำงาน

- ทำทีละ Phase ให้จบ Definition of Done ก่อนขึ้น Phase ถัดไป
- ถ้ารู้สึกอยากลบทิ้งแล้วเริ่มใหม่ → ให้กลับมาดูว่าตอนนี้ค้างอยู่ Phase ไหน แล้วแก้เฉพาะจุดนั้น อย่า refactor ทั้งโปรเจกต์
- `data/` ห้ามแก้ไขตลอดทั้งแผนนี้ ถ้ารู้สึกว่าต้องแก้ = สัญญาณว่าออกแบบ route ผิดทาง ให้ทบทวนก่อน
- **เว็บนี้คือหน้าต่างดูข้อมูล (view) เท่านั้น การแก้ไขข้อมูลทุกครั้งยังต้องทำผ่านโปรแกรม Desktop เดิม**
```

## สรุปสิ่งที่แก้ไป

| จุดที่แก้ | เดิม | ใหม่ |
|---|---|---|
| โฟลเดอร์ | `routers/` | `blueprints/` |
| ไฟล์แยก | `dependencies.py` | ตัดออก รวมเข้า `main.py` (ตรงกับที่ Phase 2 ทำสำเร็จจริง) |
| Route path | `/curricula/{id}/plan` | `/curricula/<int:curriculum_id>/plan` |
| Route path | `/curricula/{id}/groups` | `/curricula/<int:curriculum_id>/groups` |
| ตาราง technical decisions | ไม่มีแถว organize route | เพิ่มแถว "Route Organization: Flask Blueprint" |
| Default port ในตัวอย่าง | `localhost:8000` | `localhost:5000` (ค่า default ของ Flask) |

