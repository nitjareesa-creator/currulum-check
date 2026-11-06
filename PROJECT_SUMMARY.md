# ระบบจัดการข้อมูลหลักสูตรปริญญาตรี — เอกสารสรุปโปรเจกต์

เอกสารนี้สรุปทั้งหมดของโปรเจกต์เพื่อใช้เป็นข้อมูลอ้างอิงในการเขียน/ต่อยอดโปรแกรมต่อ ครอบคลุมตั้งแต่เป้าหมาย, เทคโนโลยี, โครงสร้างฐานข้อมูล, ชั้นเข้าถึงข้อมูล, หน้าจอ UI, ไปจนถึงเวอร์ชันเว็บแบบ static

## 1. เป้าหมายของระบบ

จัดเก็บและจัดการข้อมูลหลักสูตรระดับปริญญาตรีของสถาบัน (KMITL) โดยรองรับ:

- หมวดวิชาศึกษาทั่วไป (GenEd) ที่ใช้ร่วมกันได้ทุกหลักสูตร
- หมวดวิชา/หมวดวิชาย่อยเฉพาะของแต่ละหลักสูตร (พื้นฐาน, บังคับ, เลือกสาขา, บังคับเลือก, เลือกเสรี)
- **โครงการ 2 ปริญญา (Dual Degree)** — การเทียบวิชาข้ามหลักสูตร
- **แผนทางเลือกภายในหลักสูตรเดียวกัน** — PROJECT (โครงงานพิเศษ) / COOP (สหกิจศึกษา) / OVERSEA_TRAINING (ฝึกงานต่างประเทศ) เป็น 3 แผนแยกกันชัดเจน
- **แผนการศึกษารายเทอม** พร้อม placeholder วิชาเลือกที่กดดูตัวอย่าง/กรอกเองได้ (preview เท่านั้น ไม่บันทึก)
- การตรวจสอบเงื่อนไขการจบการศึกษา

### หลักสูตรจริง 3 หลักสูตรของ KMITL ที่ใส่ไว้เป็นข้อมูลตัวอย่าง

เรียงตามลำดับที่แสดงในแอป (`display_order`):

1. วิศวกรรมศาสตรบัณฑิต สาขาวิชาวิศวกรรมไอโอทีและสารสนเทศ (ปรับปรุง พ.ศ. 2569) — **138 หน่วยกิต**
2. หลักสูตรสองปริญญา วิทยาศาสตรบัณฑิต (ฟิสิกส์อุตสาหกรรม) และวิศวกรรมศาสตรบัณฑิต (วิศวกรรมระบบไอโอทีและสารสนเทศ) (ปรับปรุง พ.ศ. 2569) — **175 หน่วยกิต**
3. วิศวกรรมศาสตรบัณฑิต สาขาวิชาวิศวกรรมคอมพิวเตอร์และไอโอที (ต่อเนื่อง) (ปรับปรุง พ.ศ. 2569) — **118 หน่วยกิต** (ไม่มีแผนทางเลือก)
4. วิทยาศาสตรบัณฑิต สาขาวิชาฟิสิกส์อุตสาหกรรม (ปรับปรุง พ.ศ. 2569) — **122 หน่วยกิต**
5. วิศวกรรมศาสตรบัณฑิต สาขาวิชาวิศวกรรมระบบไอโอทีและสารสนเทศ (หลักสูตรปรับปรุง พ.ศ. 2565) — **135 หน่วยกิต**

หน่วยกิตรวมของทั้ง 5 หลักสูตร (วิชาบังคับ + placeholder วิชาเลือกตามจำนวนช่องจริง) **ตรงเป๊ะกับเป้าหมายทุกแผนทางเลือก** — ตรวจสอบซ้ำแล้วหลายรอบตลอดการพัฒนา

## 2. เทคโนโลยีที่ใช้

| ส่วน | เทคโนโลยี |
|---|---|
| ภาษา | Python 3 |
| UI Framework (Desktop) | PySide6 (Qt for Python) |
| ฐานข้อมูล | SQLite |
| ORM | SQLAlchemy 2.0 (declarative + `Mapped`/`mapped_column`) |
| เว็บ (static export) | HTML + CSS + Vanilla JS ล้วนๆ — ไม่มี build step, ไม่มี dependency |
| เว็บ (server prototype, ยังไม่ได้ใช้งานจริง) | FastAPI + Jinja2 (ดู §8) |

## 3. โครงสร้างโปรเจกต์

```
project/
├── data/
│   ├── __init__.py
│   ├── database.db              # ไฟล์ฐานข้อมูล (สร้างอัตโนมัติตอนรัน seed_data.py)
│   ├── models.py                 # SQLAlchemy ORM models (schema ทั้งหมด)
│   ├── database.py               # engine, session factory, init_db()
│   └── repository.py             # ชั้น CRUD + query ที่ใช้บ่อย (Data Access Layer)
├── app/
│   ├── __init__.py
│   ├── main.py                    # จุดเริ่มโปรแกรม Desktop (QApplication + MainWindow แบบแท็บ 5 แท็บ)
│   └── ui/
│       ├── __init__.py
│       ├── course_view.py         # หน้าจัดการรายวิชา
│       ├── curriculum_view.py     # หน้าจัดการหลักสูตร + แผนทางเลือก
│       ├── group_view.py          # หน้า tree view หมวดวิชา (แก้ไข/เพิ่ม/ลบได้)
│       ├── schedule_view.py       # หน้าแผนการศึกษารายเทอม (มี placeholder วิชาเลือกแบบ interactive)
│       └── elective_view.py       # หน้าสรุปภาพรวมกลุ่มวิชาเลือกทั้งหมด
├── web/                            # เว็บ prototype แบบมีเซิร์ฟเวอร์ (FastAPI) — ยังไม่ได้ใช้งานจริง ดู §8
│   ├── main.py
│   └── templates/
│       ├── base.html
│       ├── schedule.html
│       └── groups.html
├── seed_data.py                    # สคริปต์ใส่ข้อมูลจริงลงฐานข้อมูล (ล้างของเดิมแล้วใส่ใหม่ทุกครั้งที่รัน)
├── export_tree_view.py             # สร้าง static tree_view.html + data_tree_<ปี>.json (ดู §7)
├── export_schedule_view.py         # สร้าง static schedule_view.html + data_sched_<ปี>.json (ดู §7)
├── update_views.py                 # รวบสองหน้าจาก JSON: ประกอบ + ตรวจความสอดคล้อง + สำรอง (ดู §7 · UPDATE_VIEWS.md)
├── verify_nav.py / check_export.py # ตัวตรวจเมนูเชื่อมสองหน้า / ตัวตรวจไฟล์ HTML ที่ export แล้ว
├── split_course_pool.py            # แยกคลังวิชาออกจาก options ในสล็อตวิชาเลือก
├── build_preview.py                # ประกอบ HTML ตัวอย่างจาก JSON ชุดเล็ก (ใช้ทดสอบก่อน export เต็ม)
├── requirements.txt
└── __init__.py
```

**หลักการออกแบบสำคัญ:** แยกชั้นข้อมูล (`data/`) ออกจากชั้นแอปพลิเคชัน (`app/`, `web/`, export scripts) อย่างเด็ดขาด — ทุกจุดเรียกผ่าน `repository.py` เท่านั้น ไม่มีที่ไหนยิง SQL ตรง ทำให้เพิ่มหลักสูตรที่ 3 (ComIoT) เข้าไปแล้ว **ทุกหน้าจอ/ทุกไฟล์ export ใช้งานได้ทันทีโดยไม่ต้องแก้โค้ดเลยสักบรรทัด**

## 4. โครงสร้างฐานข้อมูล (`data/models.py`)

### ตาราง

```
Course
├── code (PK, string, 8 หลัก)     # "01236611" (IoT ขึ้นต้น 01), "05016201" (ฟิสิกส์ขึ้นต้น 05), "90641004" (GenEd ขึ้นต้น 90)
├── name_th, name_en
├── credits (int)
├── description (nullable)

CourseGroup                        # หมวดวิชา + หมวดวิชาย่อย (self-referencing hierarchy)
├── id (PK)
├── name
├── group_type (Enum: GroupType — GENED / MAJOR_REQUIRED / MAJOR_ELECTIVE / RESTRICTED_ELECTIVE / FREE_ELECTIVE)
├── parent_group_id (nullable, FK -> CourseGroup.id)
│     NULL = หมวดใหญ่ระดับบนสุด / มีค่า = หมวดย่อย
├── curriculum_id (nullable, FK -> Curriculum.id)
│     NULL = หมวดกลางของสถาบัน (GenEd ใช้ร่วมกันทุกหลักสูตร) / มีค่า = หมวดเฉพาะของหลักสูตรนั้น

Curriculum
├── id (PK)
├── name, faculty, year (พ.ศ.), total_credits
├── display_order (int)           # ลำดับแสดงผลใน dropdown/รายการ (น้อย=แสดงก่อน) — ไม่ใช่เรียงตามชื่อ A-Z แล้ว

StudyPlan                          # แผนทางเลือกภายในหลักสูตรเดียวกัน
├── id (PK)
├── curriculum_id (FK -> Curriculum.id)
├── code (PROJECT / COOP / OVERSEA_TRAINING)
├── name

CurriculumCourse                   # วิชา <-> หมวดย่อย <-> หลักสูตร <-> แผนทางเลือก (ตัวกลางหลัก)
├── id (PK)
├── curriculum_id (FK), course_code (FK), group_id (FK)
├── study_plan_id (nullable, FK -> StudyPlan.id)
│     NULL = วิชานี้ใช้ร่วมกันทุกแผน / มีค่า = เฉพาะแผนนั้น
├── is_required (bool)             # True = บังคับในหมวดนี้ / False = เลือกในหมวดนี้
├── recommended_year, recommended_semester (1/2/3=ฤดูร้อน)

CurriculumGroupRequirement          # เงื่อนไขหน่วยกิตขั้นต่ำ/สูงสุด ต่อหมวด ต่อหลักสูตร
├── id (PK), curriculum_id (FK), group_id (FK)
├── min_credits, max_credits (nullable)

CourseEquivalency                    # คู่วิชาเทียบเคียงข้ามหลักสูตร (สำหรับ 2 ปริญญา)
├── id (PK), course_code_a (FK), course_code_b (FK)
├── equivalence_type (Enum: FULL / PARTIAL)
├── credit_equivalent (nullable, ใช้เมื่อ PARTIAL)
├── note

ElectiveTermSlot                     # จำนวน "ช่องวิชาเลือก" ต้องเลือกกี่วิชา ต่อหมวด ต่อเทอม ต่อแผนทางเลือก
├── id (PK)
├── curriculum_id (FK), group_id (FK)
├── study_plan_id (nullable, FK -> StudyPlan.id)   # NULL = ใช้ร่วมกันทุกแผน
├── year, semester
├── slot_count (int)               # ต้องเลือกกี่วิชาในเทอมนี้จากหมวดนี้ (ระบุตรงๆ ไม่คำนวณจากหน่วยกิต)
```

### ER Diagram (ความสัมพันธ์หลัก)

```
Curriculum ──< CurriculumGroupRequirement >── CourseGroup
     │                                              │
     │                                        (parent_group_id
     │                                         หมวดวิชา → หมวดวิชาย่อย)
     ├──< StudyPlan                                 │
     │                                              │
     ├──< CurriculumCourse >───────────────────────┘
     │        (is_required, recommended_year/semester, study_plan_id)
     │
     └──< ElectiveTermSlot >── CourseGroup  (จำนวนช่องวิชาเลือกต่อเทอม ต่อแผน)
              │
           Course(code) ──< CourseEquivalency >── Course(code)
                                (จับคู่วิชาข้ามหลักสูตร)
```

### กฎสำคัญที่ฝังอยู่ในโครงสร้าง

- **หมวดวิชาเลือกเสรี (`FREE_ELECTIVE`)**: ไม่มี `CurriculumCourse` ผูกไว้ล่วงหน้าเลย เพราะเลือกได้จากวิชาใดก็ได้ในสถาบัน
- **GenEd ใช้ร่วมกันข้ามหลักสูตร**: สร้าง `CourseGroup` ครั้งเดียวที่ `curriculum_id = NULL` แต่ละหลักสูตรผูก `CurriculumCourse` ของตัวเองเข้ากลุ่มเดียวกันได้ กำหนด `min_credits` ต่างกันได้ผ่าน `CurriculumGroupRequirement`
- **วิชาบังคับ vs เลือกในหมวดเดียวกัน**: แยกด้วย `is_required` ใน `CurriculumCourse` ไม่ใช่ `group_type`
- **แผนทางเลือก**: วิชาที่ `study_plan_id = NULL` ใช้ร่วมกันทุกแผน ส่วนวิชาที่ระบุแผนจะปรากฏเฉพาะแผนนั้น
- **GenEd ตัวเดียวกัน บังคับ/ไม่บังคับต่างกันตามหลักสูตร**: ใช้ฟังก์ชัน `link_gened_for_curriculum()` + dict override รายหลักสูตร (`PHYSICS_GENED_OVERRIDES`, `COMIOT_GENED_OVERRIDES`) — เช่นวิชา `90642036` บังคับสำหรับ IoT/ComIoT แต่ไม่บังคับสำหรับฟิสิกส์ฯ, วิชา `90642118` บังคับเฉพาะบางหลักสูตร ไม่ใช้ในฟิสิกส์ฯ เลย (override เป็น `None` = ข้ามวิชานั้นไปเลย)
- **จำนวนช่องวิชาเลือกต่อเทอม (`ElectiveTermSlot`)**: ระบุตรงๆ จากข้อมูลจริงของแต่ละหลักสูตร (ไม่ได้คำนวณจากหน่วยกิตเป้าหมาย ÷ หน่วยกิตต่อวิชา เพราะเคยลองแล้วซับซ้อนเกินและมักผิด) หลักสูตรที่ยังไม่มีข้อมูลนี้จะ fallback ไปใช้ตรรกะเดิม (1 แถวต่อหมวดต่อเทอม อิงจาก `recommended_year/semester` ของวิชาเลือกแต่ละตัว)

## 5. Data Access Layer (`data/database.py` + `data/repository.py`)

### `database.py`
- `engine`, `SessionLocal`, `init_db()` (สร้างตารางถ้ายังไม่มี ไม่ลบข้อมูลเดิม), `get_session()`

### `repository.py`
ทุกฟังก์ชันรับ `session: Session` เป็นพารามิเตอร์แรก ฟังก์ชันเขียนข้อมูลจะ `commit()` ให้ภายในฟังก์ชันเลย

**CRUD มาตรฐานสำหรับทุกตาราง** รวมถึง `ElectiveTermSlot` (`set_elective_term_slot` แบบ upsert, `list_elective_term_slots`, `delete_elective_term_slot`)

**ฟังก์ชันระดับสูง:**
- `find_equivalent_courses(session, course_code)` — วิชาที่เทียบเคียงกันได้ทั้งหมด
- `get_group_tree(session, curriculum_id=None)` — โครงสร้างหมวดวิชาแบบ nested dict
- `check_graduation_progress(session, curriculum_id, completed_course_codes, study_plan_id=None)` — คำนวณความคืบหน้าการจบการศึกษา (นับหมวดเลือกเสรีอัตโนมัติ, นับวิชาเทียบเคียงอัตโนมัติ)

## 6. หน้าจอ UI (`app/ui/`)

| ไฟล์ | หน้าจอ | ความสามารถ |
|---|---|---|
| `course_view.py` | จัดการรายวิชา | ค้นหา, เพิ่ม, แก้ไข, ลบ |
| `curriculum_view.py` | จัดการหลักสูตร | ซ้าย = รายการหลักสูตร, ขวา = รายละเอียด + จัดการแผนทางเลือก |
| `group_view.py` | หมวดวิชา (Tree View) | Tree หมวดใหญ่→ย่อย→วิชา — เพิ่ม/แก้ไข/ลบหมวด, กำหนดหน่วยกิต, ผูก/นำวิชาออก, **ดับเบิลคลิกวิชาเพื่อแก้ไขปี/เทอม/บังคับ-เลือก/แผนทางเลือกได้โดยตรง**; หมวด GenEd แสดงอยู่ล่างสุดเสมอ |
| `schedule_view.py` | แผนการศึกษารายเทอม | ตารางรายปี/เทอมของวิชาบังคับ + **แถว placeholder วิชาเลือก** (รหัส `xxxxxxxx`) จำนวนแถวตาม `ElectiveTermSlot` จริง — กด **"เลือกวิชา..."** เพื่อ preview วิชาจริงจากกลุ่ม หรือกด **"กรอกวิชาเอง..."** สำหรับหมวดเลือกเสรี (auto-fill ชื่อ/หน่วยกิตถ้ารหัสตรงกับวิชาในระบบ) — **ทั้งหมดเป็นแค่ preview ไม่บันทึกลงฐานข้อมูล** |
| `elective_view.py` | วิชาเลือก | สรุปทุกกลุ่มวิชาเลือกของหลักสูตร: หน่วยกิตที่ต้องเลือกเพิ่ม + จำนวนวิชาให้เลือกต่อกลุ่ม + ตารางเทอมที่แนะนำระดับหมวด (ไม่ใช่รายวิชา) |

`app/main.py` รวมเป็นแท็บเดียว: จัดการหลักสูตร / จัดการรายวิชา / หมวดวิชา (Tree View) / แผนการศึกษารายเทอม / วิชาเลือก

## 7. เวอร์ชันเว็บแบบ Static (ไม่ต้องมีเซิร์ฟเวอร์)

ผู้ใช้ตัดสินใจไม่ใช้ Python server (`uvicorn`) หรือ Node.js — แค่ต้องการดูข้อมูลผ่านเว็บได้ ไม่ต้องเชื่อมฐานข้อมูลตลอดเวลา จึงทำเป็นไฟล์ HTML เดี่ยวๆ ที่ฝังข้อมูลไว้ในตัว (snapshot) เปิดได้ด้วยการดับเบิลคลิก

| สคริปต์ | สร้างไฟล์ | เนื้อหา |
|---|---|---|
| `export_tree_view.py` | `data_tree_<ปี>.json` + `tree_view.html` | หมวดวิชาแบบ tree expand/collapse + ช่องค้นหาไฮไลต์วิชา + **ตัวกรองแผนทางเลือก** (หน่วยกิตวิชาบังคับตรงกับแผนที่เลือก — ต้องส่ง `plan_code` ของแต่ละรายวิชาออกมาด้วย ดู README §4.1) |
| `export_schedule_view.py` | `data_sched_<ปี>.json` + `schedule_view.html` | แผนการศึกษารายเทอมของทุกหลักสูตร/ทุกแผน พร้อม dropdown เลือกวิชา + ฟอร์มกรอกวิชาเองสำหรับหมวดเลือกเสรี (JS ล้วน คำนวณหน่วยกิตรวมสดตามที่เลือก) |
| `update_views.py` | (รันจาก JSON ที่มีอยู่) `tree_view.html` + `schedule_view.html` | ตัวรวบรวม: รวม JSON หลายไฟล์/ตัดซ้ำ → ประกอบทั้งสองหน้า → เทียบข้อมูลข้ามหน้า → รัน `verify_nav.py` + `check_export.py` ให้ในรอบเดียว (`--pool auto/embed/split/none`, `--dry-run`, `--soft`, `--suffix`, สำรองไฟล์ใน `backups/`) |

**วิธีใช้ (ดึงจากฐานข้อมูลโดยตรง — ได้ทั้ง JSON และ HTML):**
```bash
python export_tree_view.py       # → data_tree_<ปี>.json + tree_view.html
python export_schedule_view.py   # → data_sched_<ปี>.json + schedule_view.html
```
ได้ไฟล์ `.html` มาเปิดในเบราว์เซอร์ได้เลย — ถ้าข้อมูลในฐานข้อมูลเปลี่ยน ต้องรันสคริปต์ใหม่เพื่ออัปเดตไฟล์ (เป็น snapshot ไม่ sync อัตโนมัติ)

**ถ้าอยากอัปเดตสองหน้าพร้อมกันในคำสั่งเดียวจาก JSON ที่ export ไว้:**
```bash
py update_views.py --tree-data data_tree_2569.json --schedule-data data_sched_2569.json
```
คู่มือสั้น: `UPDATE_VIEWS.md` · จุดเริ่มต้น: `START_HERE.md`

**ตัวเลือกของสคริปต์ export ทั้งคู่ (ชื่อพารามิเตอร์เหมือนกัน):** `--json-only` (ยังไม่แตะ HTML),
`--no-json`, `--json FILE`, `--template FILE`, `--verify`, `--no-backup`, `--keep-backups N`
ฝั่ง tree ยังรับ `-o/--out/--html FILE` แบบเดิม

**เทมเพลตแยกเป็นต้นทาง:** ทั้งสองสคริปต์อ่านเทมเพลตจากไฟล์จริง
(`*_template.html` → ไฟล์หลัก) และ "กู้คืน" เทมเพลตจากไฟล์ที่ export แล้วได้
ถ้าเจอแต่เทมเพลตรุ่นเก่า (ไม่มี `#plan-select`) จะ **หยุดพร้อมบอกวิธีแก้** ไม่เขียนทับ
→ ปิดความเสี่ยงเดิมที่สคริปต์เคยฝังเทมเพลตเก่าไว้ในตัว แล้วรันแล้ว UI ใหม่หายทั้งหน้า
(ดู `REVIEW_export_schedule_view.md`) · ไฟล์เดิมที่ถูกเขียนทับจะถูกสำรองใน `backups/` 5 รุ่นล่าสุด

**เมนูด้านซ้ายเชื่อมสองหน้า:** ทั้ง `tree_view.html` และ `schedule_view.html` มี sidebar แบบเดียวกัน (`<nav class="sidenav">`) ใช้สลับไปมาระหว่างสองหน้าได้โดยไม่ต้องเปิดไฟล์เอง และ **ส่งค่าหลักสูตร + แผนที่กำลังดูอยู่ไปกับลิงก์ด้วย** ผ่าน query string `?cur=<ลำดับหลักสูตร>&plan=<รหัสแผน>` หน้าปลายทางจะเลือกหลักสูตร/แผนนั้นให้ทันที (จับคู่แผนด้วยรหัสก่อน ถ้าไม่ได้จึงลองด้วย id)

- ชื่อไฟล์เป้าหมายแก้ได้ที่ค่าคงที่ `NAV_FILE` ใน `<script>` ของแต่ละไฟล์ (ค่าเริ่มต้น `tree_view.html` / `schedule_view.html`)
- ถ้าเปลี่ยนชื่อไฟล์ทั้งคู่ให้มี suffix เดียวกัน (เช่น `*_2569.html`) หน้าเว็บจะเดาชื่อคู่ให้เอง
- ต้องวางไฟล์ทั้งสองไว้โฟลเดอร์เดียวกัน · จอแคบกว่า 820px เมนูจะย้ายไปเป็นแถบแนวนอนด้านบน
- ไม่มี dependency เพิ่ม (CSS + vanilla JS ในไฟล์เดิม) จึงยังเปิดแบบ offline ได้ตามปกติ — รายละเอียดใน README §3.1 และตรวจอัตโนมัติด้วย `verify_nav.py`

**ข้อควรทราบ:** การเลือกวิชา/กรอกวิชาเองในหน้าเว็บ static เป็นแค่การดูตัวอย่างในเบราว์เซอร์ (client-side JS ล้วน) **ไม่บันทึกที่ไหนทั้งสิ้น** ปิดหน้าเว็บแล้วค่าที่เลือกไว้หายไป — เหมือนฟีเจอร์เดียวกันในฝั่ง Desktop ทุกจุด

## 8. เว็บ Prototype แบบมีเซิร์ฟเวอร์ (`web/`) — ของเก่า ยังไม่ได้ใช้งานจริง

ก่อนจะย้ายมาทำ static export (§7) เคยทำ prototype ด้วย **FastAPI + Jinja2** ไว้ก่อน (`web/main.py` + `web/templates/`) แสดงหน้าหมวดวิชาและแผนการศึกษารายเทอมแบบ read-only เชื่อมฐานข้อมูลจริงผ่าน `repository.py` เดียวกัน รันด้วย:
```bash
uvicorn web.main:app --reload
```
ไฟล์นี้ยังอยู่ในโปรเจกต์เผื่อในอนาคตอยากกลับไปทำเว็บแบบ real-time เชื่อมฐานข้อมูลตลอด (เช่น ถ้าจะเปิดให้แก้ไขข้อมูลจากเว็บได้) แต่ **ตอนนี้ไม่ใช่แนวทางหลักแล้ว** เพราะความต้องการจริงคือแค่ดูข้อมูล ไม่ต้องมีเซิร์ฟเวอร์ทำงานตลอดเวลา

## 9. ข้อมูลตัวอย่าง (`seed_data.py`)

- ข้อมูลจริงของ 3 หลักสูตร KMITL ครบทุกปีการศึกษา รวมกว่า 500 รายวิชา
- คู่วิชาเทียบเคียงข้ามหลักสูตรจริงกว่า 100 คู่ (IoT↔ฟิสิกส์, ComIoT↔IoT)
- `ElectiveTermSlot` ครบทั้ง 3 หลักสูตร — จำนวนช่องวิชาเลือกต่อหมวดต่อเทอมต่อแผน ตรงกับข้อมูลจริงที่ได้รับมา
- ใช้ฟังก์ชัน `link_gened_for_curriculum()` พร้อม override pattern ลดการเขียนโค้ดซ้ำสำหรับ GenEd ข้ามหลักสูตร
- รัน `python seed_data.py` จะ **ล้างข้อมูลเดิมทั้งหมดแล้วใส่ใหม่** (`reset_db()` เรียก `drop_all` + `create_all`) — ใช้สำหรับพัฒนา/ทดสอบเท่านั้น

## 10. วิธีรันโปรเจกต์

```bash
# ติดตั้ง dependencies (รวม PySide6, SQLAlchemy, FastAPI แม้ไม่ได้ใช้ทุกตัวตอนนี้)
pip install -r requirements.txt

# สร้างฐานข้อมูล + ใส่ข้อมูลจริง (รันครั้งแรก หรือรันซ้ำเพื่อรีเซ็ตข้อมูล)
python seed_data.py

# ทางเลือกที่ 1: เปิดโปรแกรม Desktop
python -m app.main

# ทางเลือกที่ 2: สร้างเว็บ static แล้วเปิดในเบราว์เซอร์
python export_tree_view.py
python export_schedule_view.py
# แล้วดับเบิลคลิก tree_view.html หรือ schedule_view.html
```

## 11. แนวทางต่อยอด (ยังไม่ได้ทำ)

- หน้าจัดการคู่วิชาเทียบเคียง (equivalency UI) ในฝั่ง Desktop
- หน้าตรวจสอบเงื่อนไขจบการศึกษาแบบ UI (ต่อยอดจาก `repo.check_graduation_progress()` ที่เขียนและทดสอบไว้แล้ว)
- ข้อมูลนักศึกษา (Student) และการลงทะเบียนเรียนจริง (ตกลงกันไว้แต่แรกว่ายังไม่รวมในเวอร์ชันนี้)
- Export/Import ข้อมูลหลักสูตรเป็น Excel/PDF
- ทำ static export ให้หน้า "วิชาเลือก" (elective_view) ด้วย เหมือนที่ทำ tree/schedule ไปแล้ว
- ปรับ `seed_data.py` ให้เป็น upsert แทนการ `drop_all` ทุกครั้ง เพื่อให้ปลอดภัยต่อการรันซ้ำเมื่อมีข้อมูลจริงในระบบแล้ว
- ถ้าจะเปิดให้แก้ไขข้อมูลจากเว็บได้จริง ต้องกลับไปพัฒนา `web/` (FastAPI) ต่อ พร้อมเพิ่ม session-per-request และระบบ auth
