# แก้ `export_tree_view.py` — เวอร์ชันที่ถูกต้อง (แก้เอกสารเดิมที่ผิด)

> **สรุป:** ที่ผมเคยบอกว่า "แทรก `cc.study_plan.code if cc.study_plan else None`" **ใช้กับไฟล์นี้ไม่ได้**
> เพราะ `export_tree_view.py` ของคุณไม่ได้แปลง ORM object — มันได้ข้อมูลเป็น **dict** จาก
> `repo.get_group_tree()` แล้ว ตัวแปร `cc` ไม่มีอยู่จริงในไฟล์
> **ใช้ไฟล์ `export_tree_view.py` v2 ที่แนบมาแทน** ไม่ต้องพิมพ์ตามเอกสารนี้
> *(ปัจจุบันเป็น **v6** แล้ว — เพิ่ม `--json` เขียน `data_tree_<ปี>.json`, สำรองไฟล์ใน `backups/`,
> และ `--verify` ให้ ดูหัวข้อ 3)*

---

## 1. ทำไมสูตรเดิมใช้ไม่ได้ (3 จุดที่กระทบกัน)

| # | ที่ผมเขียนผิด | ความจริงในไฟล์คุณ |
|---|---|---|
| 1 | ให้ใช้ `cc.study_plan.code` | ไม่มี `cc` เลย — ลูปคือ `for c in node["courses"]:` โดย `c` เป็น dict `{"code","is_required","recommended_year","recommended_semester"}` ไม่มีข้อมูลแผนติดมา |
| 2 | ให้ใส่ `"plans": [...for p in curriculum.study_plans]` | ไม่รู้ว่า repository เปิด attribute/ฟังก์ชันชื่ออะไร (และอาจไม่มีเลย) |
| 3 | ไม่ได้บอกว่า `HTML_TEMPLATE` ใน `.py` เป็นรุ่นเก่า | ผลคือ **รันสคริปต์ = ตัวกรองแผนที่เพิ่งทำไว้หายทั้งหน้า** (เขียนทับด้วย template เก่าที่ไม่มี `#plan-select`) |

จุดที่ 3 คือสาเหตุที่ทำให้ "แทนตัวแปรไม่ตรง" มากที่สุด — ไม่ใช่แค่ข้อมูล แต่เป็น **เทมเพลตทั้งไฟล์**

---

## 2. ไฟล์ v2 ทำอะไรให้

```
export_tree_view.py  (v2)
        │
        ├─ 1) หาเทมเพลตจริงจากไฟล์ (ไม่ใช้ template เก่าที่ฝังใน .py)
        │      tree_view_template.html → tree_view.html (ถ้ายังเป็นเทมเพลต)
        │      ถ้า tree_view.html เป็นไฟล์ export แล้ว → กู้คืนเป็นเทมเพลตให้เอง
        │      ถ้าเจอเทมเพลตที่ไม่มี #plan-select → หยุดพร้อมบอกวิธีแก้ (ไม่เขียนทับให้พัง)
        │
        ├─ 2) ดึงแผนแบบทนชื่อฟังก์ชัน
        │      repo.list_study_plans / list_plans / list_alternative_plans
        │      curriculum.study_plans / plans / alternative_plans
        │
        └─ 3) ดึง "วิชานี้ผูกแผนไหน"
               repo.list_curriculum_courses / list_curriculum_course_rows / ...
               อ่าน study_plan_id (หรือ plan_id) + รหัสวิชา
               → วิชาที่อยู่ครบทุกแผน = ไม่ติดป้าย (ใช้ร่วมกัน)
               → วิชาที่อยู่บางแผน = ติด plan_codes: ["COOP"]
```

---

## 3. วิธีใช้ (2 คำสั่ง)

```bash
# ครั้งแรกครั้งเดียว: ให้สคริปต์มีเทมเพลตแยกไว้ ไม่ถูกเขียนทับ
copy tree_view.html tree_view_template.html      # Windows
# cp tree_view.html tree_view_template.html      # macOS / Linux
```

```bash
python export_tree_view.py
```

> **อัปเดต (v6):** ตอนนี้สคริปต์เขียน **JSON ควบคู่ไปด้วย** → ได้ `data_tree_<ปี>.json`
> และ `tree_view.html` ในคำสั่งเดียว เอา JSON ไปรวมกับฝั่ง schedule ได้ทันที:
> ```bash
> py update_views.py --tree-data data_tree_2569.json --schedule-data data_sched_2569.json
> ```
> ตัวเลือกเพิ่มเติม: `--json-only` (ยังไม่แตะ HTML), `--no-json`, `--json FILE`,
> `--template FILE`, `--verify`, `--no-backup`, `--keep-backups N`
> (ไฟล์เดิมจะถูกสำรองไว้ใน `backups/` เก็บ 5 รุ่นล่าสุด — รุ่นก่อนเขียนทับตรง ๆ ไม่มีสำรอง)

ผลลัพธ์ที่ควรเห็น:

```
  · กู้คืนเทมเพลตจาก tree_view.html (ไฟล์นั้นมีข้อมูลอยู่แล้ว)
สร้างไฟล์ tree_view.html สำเร็จ (5 หลักสูตร, 412.3 KB)
ข้อมูล JSON: data_tree_2569.json (88.4 KB)
เทมเพลต: tree_view_template.html (มีตัวกรองแผน)

==============================================================
ข้อมูลแผนทางเลือก
==============================================================
หลักสูตรที่มีแผน: 4/5 | วิชาที่ผูกกับแผน: 8 วิชา
  • วิศวกรรมศาสตรบัณฑิต สาขาวิชาวิศวกรรมไอโอทีและสารสนเทศ (2569)
      แผน 3: COOP, OVERSEA_TRAINING, PROJECT
      ที่มา: repo.list_study_plans() + repo.list_curriculum_courses()
      วิชาที่ผูกกับแผน 4 / ทั้งหมด 50 วิชา
        01236491 สหกิจศึกษา                            -> COOP
        01236492 ฝึกงานต่างประเทศ                       -> OVERSEA_TRAINING
        ...
```

**ถ้าเห็น `วิชาที่ผูกกับแผน: 0`** → มีรายชื่อแผนแล้ว แต่ไม่มีวิชาไหนระบุแผน
สคริปต์จะพิมพ์รายชื่อฟังก์ชันที่มันลองไปแล้วออกมาให้ดู ให้ดูว่า repository มีฟังก์ชันที่คืน
`study_plan_id` มาด้วยหรือไม่ ถ้าไม่มีเลย → ใช้ทางลัดในหัวข้อ 5

**ถ้าเห็น `⚠ ไม่พบแผนทางเลือกของหลักสูตรใดเลย`** → จะได้หน้าเว็บแบบเดิมทุกอย่าง (ยอดรวมทุกแผน)
พร้อมแบนเนอร์อธิบายในหน้าเว็บ ไม่ใช่ไฟล์พัง

---

## 4. ตรวจผล

```bash
py check_export.py tree_view.html schedule_view.html
```

| สิ่งที่ต้องเห็น | ความหมาย |
|---|---|
| `✓ tree_view มีตัวกรองแผน` | เทมเพลตใหม่ถูกใช้จริง |
| `PROJECT: tree 108 = schedule 108 นก. ✓` | ข้อมูลแผนต่อรายวิชาตรงกับฝั่ง schedule |
| `COOP: tree 114 = schedule 114 นก. ✓` | ปิดบั๊ก +12 นก. แล้ว |

เปิด `tree_view.html` → dropdown **แผน** ต้องกดได้, ชิปขึ้นว่า
`[ทุกแผน 120] [PROJECT 108] [COOP 114] [OVERSEA_TRAINING 114]`, วิชาเฉพาะแผนมีป้าย `แผน COOP`

---

## 5. ทางลัด ถ้า repository ไม่มีข้อมูลแผนให้ดึง

ไม่ต้องแก้ `export_tree_view.py` เลย — ใช้ไฟล์ schedule ที่ export ไว้แล้วเป็นแหล่งข้อมูลแผน:

```bash
py add_plans_to_tree.py tree_view.html schedule_view.html \
    --template tree_view_template.html --out-html tree_view.html
```

ข้อดี: ใช้ได้แน่นอนเพราะ `schedule_view.html` รู้ plan ของทุกแถวอยู่แล้ว
ข้อจำกัด: วิชาที่อยู่ใน tree แต่ไม่โผล่ในหน้า schedule จะถูกนับเป็น "ใช้ร่วมทุกแผน"

---

## 6. ตารางเทียบ: อาการ → สาเหตุ → แก้

| อาการ | สาเหตุ | แก้ |
|---|---|---|
| รันแล้ว UI ตัวกรองแผนหาย | template เก่าใน `.py` เขียนทับ | ใช้ v2 (อ่านเทมเพลตจากไฟล์) |
| `NameError: cc is not defined` | ตามสูตรเดิมของผม | ใช้ v2 |
| `หาเทมเพลตที่มีตัวกรองแผนไม่สำเร็จ` | ไม่มี `tree_view_template.html` และ `tree_view.html` เป็นรุ่นเก่า | `copy` ไฟล์เทมเพลตใหม่มาวาง |
| `วิชาที่ผูกกับแผน: 0` | repository ไม่คืน `study_plan_id` | ใช้หัวข้อ 5 |
| dropdown กดได้ แต่ตัวเลขเท่ากันทุกแผน | วิชาเฉพาะแผนอยู่ครบทุกแผนในฐานข้อมูล | ตรวจ `CurriculumCourse.study_plan_id` ใน DB |
| ตัวเลขเป็น 120 ตอนเปิดหน้า | ยังเลือก "ทุกแผน" | กดชิป `PROJECT` |

---

## 7. v5 → v6 เปลี่ยนอะไร (สรุปสั้น)

| เรื่อง | v5 | v6 |
|---|---|---|
| ไฟล์ JSON | ❌ ไม่มี | ✅ `data_tree_<ปี>.json` ควบคู่กับ HTML ทุกครั้ง |
| โหมด | เขียน HTML เสมอ | `--json-only`, `--no-json`, `--json FILE`, `--template FILE` |
| สำรองไฟล์เดิม | ❌ เขียนทับตรง ๆ | ✅ `backups/` เก็บ 5 รุ่นล่าสุด (`--no-backup`, `--keep-backups N`) |
| ตรวจหลังเขียน | ❌ ต้องรันเอง | `--verify` → รัน `verify_nav.py` + `check_export.py` ให้ |
| ด่านกัน UI ถอยหลัง | ตรวจแค่ `#plan-select` | ตรวจ `#plan-select` และเตือนถ้าไม่พบเมนูด้านซ้าย |
| เรียก `export()` แบบเดิม | ✅ | ✅ ยังใช้ได้ (เท่ากับ `--no-json`) — `-o/--out/--html` ก็ยังรับ |
| ตรรกะดึงแผน/หมวดวิชา | — | **ไม่แก้** (คงเดิมทุกบรรทัด) |

JSON ที่ได้ยังใช้กับเครื่องมือเดิมได้ทันที เช่น
`py add_plans_to_tree.py data_tree_2569.json schedule_view.html --out build/data_tree.json`
(สคริปต์นั้นรับทั้ง `.html` และ `.json` อยู่แล้ว)
