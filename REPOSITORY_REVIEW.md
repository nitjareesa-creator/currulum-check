# รีวิว `data/repository.py` — หลังได้ API จริงของโปรเจกต์

> ## สถานะการแก้ไข (อัปเดตล่าสุด)
>
> | ข้อ | เรื่อง | สถานะ |
> |---|---|---|
> | 1.1 | `get_group_tree()` เพิ่ม `study_plan_id` + `plan_code` | ✅ แก้แล้ว |
> | 1.2 | `check_graduation_progress()` fail-closed เมื่อไม่ระบุแผน | ✅ แก้แล้ว |
> | 1.3 | `update_*` ตรวจ whitelist + แก้ primary key ไม่ได้ | ✅ แก้แล้ว |
> | 1.3b | `update_course(s, "A", code="B")` ต้องคืน `RepositoryError` ไม่ใช่ `TypeError` | ✅ แก้แล้ว (รอบ 2) |
> | 1.4 | เพิ่มพารามิเตอร์ `commit=` ให้ฟังก์ชันเขียนข้อมูลทุกตัว | ✅ แก้แล้ว |
> | 1.5 | เพิ่ม `total_earned_credits_raw` + กัน `min_credits=None` | ✅ แก้แล้ว |
> | 1.6 | กันนับหน่วยกิตซ้ำหลายหมวด + ชุดเทียบเคียงแบบ transitive | ✅ แก้แล้ว |
> | 2.4 | `delete_study_plan()` แจ้ง error ที่อ่านรู้เรื่องก่อนลบ | ✅ แก้แล้ว (แถม) |
> | 2.5 | `create_course_equivalency()` ตรวจว่ามีวิชาจริง | ✅ แก้แล้ว (แถม) |
> | 2.1 | ลด query ใน `check_graduation_progress()` (N+1 ต่อหมวด/ต่อวิชา) | ✅ แก้แล้ว |
> | 2.2 | `find_equivalent_codes()` + `find_equivalent_courses()` 2 query คงที่ | ✅ แก้แล้ว |
> | 2.3 | `get_group_tree()` ประกอบ tree ในหน่วยความจำ | ✅ แก้แล้ว |
>
> **ตรวจผล:** `python verify_plan_patch.py` (ความถูกต้อง 1.1–1.6)
> และ `python verify_queries.py` (2.1–2.3: นับ query จริง + เทียบผลกับ implementation อ้างอิง)
>
> **สรุปผล 2.1–2.3:** `get_group_tree` ~60 → 3 queries · `check_graduation_progress`
> 300+ → 6 queries · `find_equivalent_courses` 1+N → 2 queries ทั้งหมดเป็นค่าคงที่
> ไม่ขึ้นกับจำนวนหมวด/วิชา และสคริปต์ `verify_queries.py` พิสูจน์แล้วว่าผลลัพธ์
> (tree ทุก field, หน่วยกิตต่อหมวด, ยอดรวม) **เหมือนกับ implementation เดิมเป๊ะ**
>
> **ตรวจผล:** `python verify_plan_patch.py` (ครอบคลุม 1.1–1.6 · การทดสอบที่เขียนข้อมูลจะ rollback ทิ้งเสมอ)
>
> **บั๊กใหม่ที่เจอตอนแก้ 1.6:** `find_equivalent_courses()` ไม่กรอง `EquivalenceType`
> ทั้งที่คอมเมนต์ใน `check_graduation_progress` เขียนว่า "FULL เท่านั้น" → คู่เทียบแบบ `PARTIAL`
> ถูกนับเป็นวิชาเดียวกันเต็มจำนวน ตัวใหม่ (`_equivalence_closure`) กรองเฉพาะ FULL แล้ว
> ส่วน `find_equivalent_courses()` ยังคงพฤติกรรมเดิมไว้เพื่อไม่ให้โค้ดที่เรียกอยู่พัง
> (เพิ่มคำเตือนใน docstring แล้ว)
>
> **บั๊กใหม่ที่เจอตอนแก้ 1.3 (รอบ 2):** ตัวตรวจ whitelist ไม่มีโอกาสทำงานเลยถ้าชื่อพารามิเตอร์
> ของรหัสตรงกับชื่อ primary key — `update_course(session, "A", code="B")` โยน
> `TypeError: got multiple values for argument 'code'` ตั้งแต่ Python จับ argument ก่อนเข้า
> ฟังก์ชัน (ข้อมูลยังปลอดภัย แต่ได้ error ที่อ่านไม่รู้เรื่อง) แก้โดยเปลี่ยนชื่อพารามิเตอร์เป็น
> `course_code` แล้วดึงค่าจาก `code=` ใน `**fields` แทน → คืน `RepositoryError` ที่บอกสาเหตุจริง
> และการเรียกแบบเก่า `update_course(session, code="A", credits=3)` ยังทำงานเหมือนเดิม
> พร้อมกันนี้ใส่ `primary_keys=` ให้ `update_curriculum` / `update_course_group` /
> `update_study_plan` / `update_curriculum_course` (คุม `id=`) เป็นการป้องกันชั้นที่สอง


อ่านครบทั้งไฟล์แล้ว สรุปเป็น 3 กลุ่ม: **ของที่ exporter ต้องยึด** → **bug ที่ควรแก้** → **จุดที่ควรปรับปรุง**

---

## 0. ข่าวดี: exporter v4 ใช้ API จริงแล้ว

ตรวจ signature ในไฟล์คุณแล้ว ได้ผลตรงนี้:

| ที่ผมเดาไว้ใน v2 | API จริงใน `repository.py` | ผล |
|---|---|---|
| `list_study_plans(session, curriculum_id)` | ✅ มีจริง `def list_study_plans(session, curriculum_id)` | ใช้ได้ทันที |
| `list_curriculum_courses(...)` | ❌ **ไม่มีฟังก์ชันนี้** ชื่อจริงคือ `list_courses_for_curriculum` | **v2 จึงได้ 0 วิชาที่ผูกแผน** |
| `CurriculumCourse.study_plan_id` | ✅ มีจริง | ใช้ได้ |
| `StudyPlan.id / .code / .name` | ✅ มีจริง | ใช้ได้ |

`export_tree_view.py` v4 จึงเรียง `list_courses_for_curriculum` เป็นตัวเลือกแรก (โค้ดภายในรองรับ attribute access อยู่แล้ว `_get(r, "course_code")` / `_get(r, "study_plan_id")` จึงต่อกันได้เลย ไม่ต้องแก้อะไรเพิ่ม)

> **ถ้าตอนคุณรันแล้วขึ้น `วิชาที่ผูกกับแผน: 0`** — สาเหตุคือข้อนี้ ไม่ใช่ข้อมูลในฐานข้อมูล
> รัน v4 ใหม่แล้วตัวเลขควรขึ้น (หรือถ้าคุณใช้ทางลัด `add_plans_to_tree.py` ไปแล้ว ก็ถือว่าแก้ไปแล้ว)

---

## 1. Bug — เรียงตามความสำคัญ

### 🔴 1.1 `get_group_tree()` ไม่กรองแผน → **ต้นเหตุ +12 นก. อยู่ที่ชั้น repository เอง**

```python
courses = list_courses_for_curriculum(session, curriculum_id, group_id=group.id)
```

ไม่ส่ง `study_plan_id` → `list_courses_for_curriculum` คืน **ทุกแถว** ของหลักสูตร รวมสหกิจ (COOP) + ฝึกงานต่างประเทศ (OVERSEA) + PROJECT พร้อมกัน

ผลคือ **ทุกหน้าจอที่เรียก `get_group_tree` เจอบั๊กเดียวกันทั้งหมด** ไม่ใช่แค่ tree_view — การไปแก้ที่ exporter ทีละที่จึงเป็นการอุดปลายเหตุ

**แพตช์** (เพิ่ม 2 ฟิลด์ ให้ทุกคนที่เรียกใช้รู้ว่าแถวนี้เป็นของแผนไหน):

```python
def get_group_tree(session: Session, curriculum_id: Optional[int] = None) -> List[Dict]:
    top_groups = list_course_groups(session, curriculum_id=curriculum_id, top_level_only=True)
    plan_code_by_id = (
        {p.id: p.code for p in list_study_plans(session, curriculum_id)}
        if curriculum_id else {}
    )

    def build_node(group: CourseGroup) -> Dict:
        children = get_group_children(session, group.id)
        courses = list_courses_for_curriculum(session, curriculum_id, group_id=group.id) if curriculum_id else []
        return {
            "id": group.id,
            "name": group.name,
            "group_type": group.group_type.value,
            "children": [build_node(child) for child in children],
            "courses": [
                {
                    "code": link.course_code,
                    "is_required": link.is_required,
                    "recommended_year": link.recommended_year,
                    "recommended_semester": link.recommended_semester,
                    "study_plan_id": link.study_plan_id,                      # ← เพิ่ม
                    "plan_code": plan_code_by_id.get(link.study_plan_id),     # ← เพิ่ม (None = ใช้ร่วมทุกแผน)
                }
                for link in courses
            ],
        }

    return [build_node(g) for g in top_groups]
```

ทำแบบนี้แล้ว `export_tree_view.py` จะเหลือแค่ `c["plan_code"]` บรรทัดเดียว ไม่ต้องเดาชื่อฟังก์ชันอีกเลย — และหน้าจออื่นที่ใช้ `get_group_tree` ก็ได้ประโยชน์ฟรี

---

### 🔴 1.2 `check_graduation_progress()` นับ COOP + OVERSEA ซ้ำ — บั๊กตัวเดียวกับ 1.1

```python
links = list_courses_for_curriculum(
    session, curriculum_id, group_id=req.group_id, study_plan_id=study_plan_id,
)
```

พารามิเตอร์ `study_plan_id` มีค่า default `None` และเมื่อเป็น `None` ฟังก์ชัน **ไม่กรองแผนเลย** → ถ้าอาจารย์/นักศึกษาเรียกแบบไม่ระบุแผน (ซึ่งเป็น default) จะได้หน่วยกิต **COOP 6 + OVERSEA 6 + PROJECT 6** ครบทั้งสามทาง

แย่กว่านั้น: `is_graduated` อาจขึ้น `True` ทั้งที่นักศึกษาเรียนจริงแค่ทางเดียว — **เป็นการรายงานผลจบการศึกษาผิด**

**แพตช์** — เลือกทางใดทางหนึ่ง:

```python
# ทาง A: บังคับให้ระบุแผน (เข้มงวดสุด — แนะนำถ้าหลักสูตรมีแผนจริง)
if study_plan_id is None:
    raise ValueError("หลักสูตรนี้มีแผนทางเลือก ต้องระบุ study_plan_id เพื่อตรวจผลจบ")

# ทาง B: ไม่ระบุแผน = นับเฉพาะวิชาที่ใช้ร่วมทุกแผน (ปลอดภัย แต่เข้มเกินไปเล็กน้อย)
links = list_courses_for_curriculum(session, curriculum_id, group_id=req.group_id, study_plan_id=study_plan_id)
if study_plan_id is None:
    links = [l for l in links if l.study_plan_id is None]
```

---

### 🟠 1.3 `update_*` ทั้งหมด — typo หายเงียบ **และแก้ primary key ได้**

```python
for key, value in fields.items():
    if hasattr(course, key):
        setattr(course, key, value)
```

สองปัญหา:

1. `repo.update_curriculum(session, 1, ttl_credits=120)` → **ไม่ error, ไม่แก้อะไร, return object เดิม** คนเรียกนึกว่าสำเร็จ
2. `repo.update_course(session, "01236611", code="XXX")` → `hasattr` เป็นจริง → **เปลี่ยน primary key** พัง FK ทั้ง DB

**แพตช์** (ใช้ซ้ำได้ทุก `update_*`):

```python
_UPDATABLE_LABEL = "name_th, name_en, credits, description"

def update_course(session: Session, code: str, **fields) -> Optional[Course]:
    allowed = {"name_th", "name_en", "credits", "description"}
    unknown = set(fields) - allowed
    if unknown:
        raise ValueError(f"update_course: แก้ไม่ได้ {sorted(unknown)} (แก้ได้: {_UPDATABLE_LABEL})")
    course = session.get(Course, code)
    if course is None:
        return None
    for key, value in fields.items():
        setattr(course, key, value)
    ...
```

ทำแบบนี้กับ `update_course`, `update_course_group`, `update_curriculum`, `update_study_plan`, `update_curriculum_course` (5 ตัว — ตัวหลังสุดคือ `group_id, is_required, recommended_year, recommended_semester, study_plan_id`)

---

### 🟠 1.4 `session.commit()` ในทุกฟังก์ชัน → งานหลายขั้นไม่ atomic

`seed_data.py` ที่สร้างหลักสูตร + 20 หมวด + 60 วิชา ถ้าล้มที่วิชาที่ 40 จะเหลือ **ข้อมูลครึ่งเดียวใน DB** และรันซ้ำจะชน unique constraint

**แพตช์** (ไม่กระทบโค้ดเดิมที่เรียกอยู่ เพราะ default ยังเป็น `True`):

```python
def create_course(..., commit: bool = True) -> Course:
    ...
    session.add(course)
    if commit:
        session.commit()
        session.refresh(course)
    else:
        session.flush()      # ให้ได้ id ไว้ใช้ต่อ โดยยัง rollback ได้
    return course
```

แล้วให้ seed ทำงานใน `try/except` + `session.rollback()` ครั้งเดียว

---

### 🟡 1.5 `total_earned_credits` ตัดหน่วยกิตด้วย `min()` → ตัวเลขที่รายงานไม่ใช่ของจริง

```python
total_earned = sum(min(g["earned_credits"], g["min_credits"]) for g in result_groups)
```

ตั้งใจให้ "ไม่เกินโควตาต่อหมวด" ซึ่งถูกสำหรับตัดสินจบ แต่ถ้า UI เอาค่านี้ไปแสดงว่า "นักศึกษาได้ 108 นก." จะไม่ตรงกับ transcript

**แนะนำ:** คืนสองค่า

```python
"total_earned_credits": total_earned_capped,
"total_earned_credits_raw": sum(g["earned_credits"] for g in result_groups),
```

พร้อมกันนี้ `sum(g["min_credits"] ...)` จะ `TypeError` ถ้าหมวดใดมี `min_credits = None` → ใช้ `(g["min_credits"] or 0)`

---

### 🟡 1.6 วิชาเดียวถูก link หลายหมวด → นับหน่วยกิตซ้ำ

ใน `check_graduation_progress`, `earned` บวกทุก `link` ที่รหัสวิชาอยู่ใน `expanded` โดยไม่เช็กว่าเคยนับไปแล้วในหมวดก่อนหน้า (`used_codes` เป็น `set` แต่ใช้แค่กันไม่ให้นับเป็นเลือกเสรี ไม่ได้กันนับซ้ำในหมวด)

```python
earned = 0
for link in links:
    if link.course_code in expanded:
        earned += ...        # ← ถ้าวิชาเดียวกันอยู่ใน 2 หมวด บวก 2 ครั้ง
```

ถ้า `CurriculumCourse` มี unique constraint `(curriculum_id, course_code, group_id)` เรื่องนี้อาจไม่เกิด — แต่ควรเพิ่ม `if link.course_code in used_codes: continue` เพื่อกันไว้

---

## 2. จุดที่ควรปรับปรุง (ไม่ใช่บั๊ก แต่จะเจ็บตอนข้อมูลโต)

### 2.1 N+1 query ใน `check_graduation_progress`

```python
for code in completed:
    for equivalent in find_equivalent_courses(session, code):   # ← 1 query ต่อวิชา
```
และถูกเรียกซ้ำอีกครั้งในส่วน leftover → **2N queries** ถ้ามี 150 วิชา = 300 queries

**แนะนำ:** โหลดตาราง equivalency ทั้งก้อนครั้งเดียว แล้ว union-find

```python
def _equivalent_sets(session) -> Dict[str, set]:
    rows = session.scalars(select(CourseEquivalency)).all()
    parent = {}
    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb: parent[ra] = rb
    for r in rows:
        if r.equivalence_type == EquivalenceType.FULL:
            union(r.course_code_a, r.course_code_b)
    groups = {}
    for code in list(parent):
        groups.setdefault(find(code), set()).add(code)
    return groups
```

**โบนัสฟรี:** แก้บั๊กที่ `find_equivalent_courses` **ไม่ transitive** — ตอนนี้ A~B, B~C จะได้ A~{B} แต่ไม่ได้ C ส่วน union-find ได้ครบ

### 2.2 `find_equivalent_courses` คืน `Course` object แต่ผู้เรียกใช้แค่ code

ทุกจุดที่เรียกใช้เป็น `{e.code for e in find_equivalent_courses(...)}` → คืน `List[str]` หรือเพิ่ม `find_equivalent_codes()` จะลด query และอ่านง่ายขึ้น (ตอนนี้ `session.get(Course, other_code)` ต่อคู่ = อีก N queries)

### 2.3 `get_group_tree` ยัง N+1 (แต่ข้อมูลเล็กไม่เป็นไร)

`build_node` เรียก `get_group_children` + `list_courses_for_curriculum` ต่อโหนด ถ้าหลักสูตรมี 30 หมวด = 60 queries ถ้าอนาคตช้า ค่อยเปลี่ยนเป็นโหลดครั้งเดียวแล้ว group ใน memory

### 2.4 `delete_study_plan` อาจ IntegrityError

ถ้า `CurriculumCourse.study_plan_id` เป็น FK ที่ไม่มี `ondelete` → ลบแผนที่มีวิชาผูกอยู่จะ error ดิบ ๆ แนะนำเช็กก่อน:

```python
def delete_study_plan(session, plan_id):
    plan = session.get(StudyPlan, plan_id)
    if plan is None:
        return False
    used = session.scalars(
        select(CurriculumCourse).where(CurriculumCourse.study_plan_id == plan_id).limit(1)
    ).first()
    if used is not None:
        raise ValueError("ลบไม่ได้: ยังมีรายวิชาผูกกับแผนนี้อยู่ (ย้ายไปแผนอื่นหรือตั้งเป็นใช้ร่วมทุกแผนก่อน)")
    ...
```

### 2.5 `create_course_equivalency` ไม่ตรวจว่ามีรหัสวิชาจริง

ถ้า `models.py` ไม่มี FK ไป `Course.code` → บันทึกคู่เทียบกับวิชาที่ไม่มีอยู่ได้เงียบ ๆ แล้ว `check_graduation_progress` จะนับผิดโดยไม่มีใครรู้ แนะนำ `session.get(Course, code)` เช็กก่อนทั้งสองฝั่ง

---

## 3. สิ่งที่ทำได้ดีอยู่แล้ว (ไม่ต้องแก้)

- ✅ `get_group_tree` คืน **dict** ไม่ใช่ ORM object → ปลอดภัยจาก `DetachedInstanceError` แม้ปิด session แล้ว **(ผมเคยแนะนำผิดว่าต้อง eager-load — ไม่จำเป็นเลยสำหรับฟังก์ชันนี้)**
- ✅ `get_*` คืน `None` แทน raise — คาดเดาง่าย
- ✅ `list_courses_for_curriculum` มี `include_shared_study_plan_courses` ให้เลือกพฤติกรรมได้ชัดเจน
- ✅ แยก `GroupType` / `EquivalenceType` เป็น enum → ไม่มี magic string
- ✅ docstring ทุกฟังก์ชันบอก field ที่แก้ได้ (แค่ยังไม่บังคับใช้ — ดู 1.3)

---

## 4. ลำดับที่แนะนำให้ลงมือ

| ลำดับ | งาน | เวลา | เหตุผล |
|---|---|---|---|
| 1 | แพตช์ 1.1 (`get_group_tree` + `plan_code`) | 5 นาที | ปิดบั๊ก +12 นก. ที่ต้นทาง, ทำให้ exporter เหลือ 1 บรรทัด |
| 2 | แพตช์ 1.2 (`check_graduation_progress`) | 5 นาที | ป้องกันรายงานผลจบผิด — **สำคัญที่สุดในเชิงผลกระทบ** |
| 3 | แพตช์ 1.3 (whitelist `update_*`) | 15 นาที | กัน typo เงียบ + กัน PK พัง |
| 4 | แพตช์ 1.4 (`commit` flag) | 15 นาที | กัน seed ค้างครึ่งทาง |
| 5 | 1.5 / 1.6 / 2.x | ทีหลัง | ปรับคุณภาพ ไม่เร่ง |

---

## 5. ถ้าอยากให้ผมลงมือ

ผมแก้ `export_tree_view.py` เป็น v4 เรียบร้อยแล้ว (ข้อ 0) ถ้าอยากให้แพตช์ `repository.py` ข้อ 1.1–1.4 จริง ๆ บอกได้เลย — บอกแค่ว่า "ลงข้อ 1.1 กับ 1.2" ผมจะแก้ไฟล์ให้ทั้งไฟล์แล้วส่งกลับมา (ก่อนแก้อาจควร `copy repository.py repository_backup.py` ไว้ก่อน)
