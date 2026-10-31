"""
export_schedule_view.py
-------------------------
ดึงข้อมูล "แผนการศึกษารายเทอม" ของทุกหลักสูตร (ทุกแผนทางเลือก) จากฐานข้อมูล
แล้วสร้างไฟล์ HTML แบบ "static" ไฟล์เดียว (ฝังข้อมูลไว้ข้างในไฟล์เลย)
เปิดดูได้ทันทีด้วยการดับเบิลคลิกในเบราว์เซอร์ ไม่ต้องรันเซิร์ฟเวอร์ใดๆ

ยังกด "เลือกวิชา" / "กรอกวิชาเอง" ดูตัวอย่างได้เหมือนโปรแกรม Desktop (แต่เป็นแค่การดูตัวอย่างในเบราว์เซอร์
ไม่บันทึกอะไรลงไฟล์หรือฐานข้อมูล — ปิดหน้าเว็บแล้วค่าที่เลือกไว้จะหายไป เหมือนฝั่ง Desktop ทุกจุด)

วิธีใช้ (จากโฟลเดอร์ project เป็น working directory):
    python export_schedule_view.py

จะได้ไฟล์ schedule_view.html ขึ้นมา — เปิดไฟล์นี้ด้วยเบราว์เซอร์ได้เลย
ถ้าข้อมูลในฐานข้อมูลเปลี่ยน ให้รันสคริปต์นี้ใหม่อีกครั้งเพื่ออัปเดตไฟล์
"""

import json
from collections import Counter

from data.database import init_db, get_session
from data import repository as repo
from data.models import GroupType

SEMESTER_LABELS = {1: "เทอม 1", 2: "เทอม 2", 3: "ภาคฤดูร้อน"}
PLAN_CODE_ORDER = ["PROJECT", "COOP", "OVERSEA_TRAINING"]


def build_plan_schedule(session, curriculum, plan_id) -> dict:
    """สร้างข้อมูลแผนการศึกษารายเทอม 1 ชุด (สำหรับ 1 หลักสูตร + 1 แผนทางเลือก หรือ 'เฉพาะวิชาร่วม')"""
    curriculum_id = curriculum.id

    if plan_id is None:  # เฉพาะวิชาที่ใช้ร่วมกันทุกแผน
        all_links = [l for l in repo.list_courses_for_curriculum(session, curriculum_id) if l.study_plan_id is None]
    else:
        all_links = repo.list_courses_for_curriculum(session, curriculum_id, study_plan_id=plan_id)

    required_links = [l for l in all_links if l.is_required]
    elective_links = [l for l in all_links if not l.is_required]
    elective_by_group = {}
    for link in elective_links:
        elective_by_group.setdefault(link.group_id, []).append(link)

    schedule = {}
    for link in required_links:
        key = (link.recommended_year, link.recommended_semester)
        schedule.setdefault(key, []).append(link)

    # --- กลุ่มวิชาเลือกที่แนะนำต่อเทอม: ใช้ ElectiveTermSlot ถ้ามี ไม่งั้น fallback ---
    term_slots = repo.list_elective_term_slots(session, curriculum_id, study_plan_id=plan_id)
    elective_terms = {}  # (year, sem, group_id) -> (options, slot_count)
    if term_slots:
        for slot in term_slots:
            key = (slot.year, slot.semester, slot.group_id)
            elective_terms[key] = (elective_by_group.get(slot.group_id, []), slot.slot_count)
    else:
        requirements = repo.list_group_requirements(session, curriculum_id)
        required_credits_by_group = {}
        for l in required_links:
            course = repo.get_course(session, l.course_code)
            if course:
                required_credits_by_group[l.group_id] = required_credits_by_group.get(l.group_id, 0) + course.credits
        fully_covered = {
            req.group_id for req in requirements
            if required_credits_by_group.get(req.group_id, 0) >= req.min_credits
        }
        for link in elective_links:
            if link.recommended_year is None or link.recommended_semester is None:
                continue
            if link.group_id in fully_covered:
                continue
            key = (link.recommended_year, link.recommended_semester, link.group_id)
            options, _ = elective_terms.get(key, ([], 1))
            elective_terms[key] = (options + [link], 1)

    years = sorted({k[0] for k in schedule if k[0] is not None} | {k[0] for k in elective_terms})
    years_data = []
    total_credits = 0

    for year in years:
        semesters = sorted(
            {k[1] for k in schedule if k[0] == year and k[1] is not None}
            | {k[1] for k in elective_terms if k[0] == year}
        )
        semester_blocks = []
        year_credits = 0

        for semester in semesters:
            required_rows = []
            for link in sorted(schedule.get((year, semester), []), key=lambda l: l.course_code):
                course = repo.get_course(session, link.course_code)
                group = repo.get_course_group(session, link.group_id)
                if course is None:
                    continue
                required_rows.append({
                    "code": course.code, "name_th": course.name_th, "credits": course.credits,
                    "group_name": group.name if group else "-",
                })
                year_credits += course.credits

            elective_slots = []
            for (y, s, gid), (options, slot_count) in elective_terms.items():
                if y != year or s != semester:
                    continue
                group = repo.get_course_group(session, gid)
                group_name = group.name if group else "-"
                is_free = bool(group and group.group_type == GroupType.FREE_ELECTIVE)
                option_credits = []
                option_list = []
                for l in sorted(options, key=lambda x: x.course_code):
                    c = repo.get_course(session, l.course_code)
                    if c:
                        option_credits.append(c.credits)
                        option_list.append({"code": c.code, "name_th": c.name_th, "credits": c.credits})
                default_credits = Counter(option_credits).most_common(1)[0][0] if option_credits else 3
                elective_slots.append({
                    "group_name": group_name, "slot_count": slot_count,
                    "is_free_elective": is_free, "default_credits": default_credits,
                    "options": option_list,
                })
                year_credits += default_credits * slot_count

            semester_blocks.append({
                "semester": semester, "label": SEMESTER_LABELS.get(semester, "ไม่ระบุเทอม"),
                "required_rows": required_rows, "elective_slots": elective_slots,
            })

        years_data.append({"year": year, "semesters": semester_blocks, "credits": year_credits})
        total_credits += year_credits

    return {"years": years_data, "total_credits": total_credits}


def export():
    init_db()
    session = get_session()
    try:
        curricula_data = []
        for curriculum in repo.list_curricula(session):
            plans = repo.list_study_plans(session, curriculum.id)
            plans = sorted(plans, key=lambda p: PLAN_CODE_ORDER.index(p.code) if p.code in PLAN_CODE_ORDER else 99)

            plan_options = [{"id": p.id, "code": p.code, "name": p.name} for p in plans]
            plan_options.append({"id": "shared", "code": None, "name": "เฉพาะวิชาที่ใช้ร่วมกันทุกแผน"})

            data_by_plan = {}
            for p in plans:
                data_by_plan[str(p.id)] = build_plan_schedule(session, curriculum, p.id)
            data_by_plan["shared"] = build_plan_schedule(session, curriculum, None)

            curricula_data.append({
                "id": curriculum.id, "name": curriculum.name, "faculty": curriculum.faculty,
                "year": curriculum.year, "total_credits": curriculum.total_credits,
                "plans": plan_options, "data_by_plan": data_by_plan,
            })
    finally:
        session.close()

    data_json = json.dumps(curricula_data, ensure_ascii=False)
    html = HTML_TEMPLATE.replace("__DATA_JSON__", data_json)
    with open("schedule_view.html", "w", encoding="utf-8") as f:
        f.write(html)

    print(f"สร้างไฟล์ schedule_view.html สำเร็จ ({len(curricula_data)} หลักสูตร)")
    print("เปิดไฟล์ schedule_view.html ด้วยเบราว์เซอร์ได้เลย (ดับเบิลคลิก) ไม่ต้องรันเซิร์ฟเวอร์ใดๆ")


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="UTF-8">
<title>แผนการศึกษารายเทอม - ระบบจัดการหลักสูตร</title>
<style>
    * { box-sizing: border-box; }
    body { font-family: "Sarabun", "Segoe UI", sans-serif; margin: 0; background: #f5f6f8; color: #222; }
    header { background: #1f2d3d; padding: 16px 24px; color: #fff; }
    header h1 { margin: 0; font-size: 18px; }
    header .note { font-size: 12px; color: #9fb0c3; margin-top: 4px; }
    main { max-width: 1000px; margin: 20px auto; padding: 0 20px 40px; }
    .toolbar {
        background: #fff; padding: 14px 18px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        margin-bottom: 16px; display: flex; gap: 16px; flex-wrap: wrap; align-items: center;
    }
    .toolbar label { font-size: 14px; color: #555; margin-right: 6px; }
    .toolbar select { padding: 6px 10px; border-radius: 6px; border: 1px solid #ccc; font-size: 14px; min-width: 260px; }
    .summary {
        background: #fff; padding: 14px 18px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        margin-bottom: 16px; font-weight: 600;
    }
    .summary .hint { font-weight: 400; color: #777; font-size: 12px; margin-top: 4px; }
    .card { background: #fff; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); padding: 16px 18px; margin-bottom: 16px; }
    .card h2 { margin: 0 0 10px 0; font-size: 18px; color: #1f2d3d; }
    .card h3 { margin: 14px 0 6px 0; font-size: 15px; color: #34495e; border-bottom: 2px solid #edf1f5; padding-bottom: 4px; }
    table { width: 100%; border-collapse: collapse; font-size: 14px; margin-bottom: 6px; }
    th, td { text-align: left; padding: 6px 8px; border-bottom: 1px solid #eee; vertical-align: middle; }
    th { color: #666; font-weight: 600; background: #fafbfc; }
    td.credits, th.credits { text-align: center; width: 90px; }
    td.type, th.type { text-align: center; width: 90px; }
    .badge { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 12px; }
    .badge.required { background: #dbeafe; color: #1d4ed8; }
    .badge.elective { background: #fef3c7; color: #92400e; }
    .term-total { color: #555; font-size: 13px; margin: 4px 0 12px 0; }
    .year-total { font-style: italic; color: #444; margin-top: 4px; }
    .empty { color: #999; padding: 12px 0; text-align: left; font-size: 13px; }
    select.elective-select { padding: 4px 6px; border-radius: 4px; border: 1px solid #ccc; font-size: 13px; width: 100%; }
    input.free-input { padding: 4px 6px; border-radius: 4px; border: 1px solid #ccc; font-size: 13px; width: 100%; }
    .free-row td { padding-top: 8px; padding-bottom: 8px; }
    .free-row .free-labels { display: flex; gap: 6px; }
    .free-row .free-labels input:first-child { width: 110px; flex-shrink: 0; }
    .selected-code { color: #1a56db; font-weight: 600; }

    .toolbar { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; margin: 12px 0; }
    .toolbar button { padding: 6px 14px; border: 1px solid #cbd5e1; border-radius: 6px;
                  background: #fff; cursor: pointer; font-size: 0.9em; }
    .toolbar button:hover { background: #f1f5f9; }
    #btnExport { border-color: #86efac; color: #15803d; }
    #btnImport { border-color: #93c5fd; color: #1d4ed8; }
    #btnReset  { border-color: #fca5a5; color: #dc2626; }
    #saveStatus { font-size: 0.9em; }
    #gpaDisplay { font-weight: 600; font-size: 1.05em; margin: 6px 0 14px; }
    .grade-select { width: 70px; text-align: center; }
    body.dragging { outline: 3px dashed #3b82f6; outline-offset: -8px; }

</style>
</head>
<body>
<header>
    <h1>📅 แผนการศึกษารายเทอม</h1>
    <div class="note" id="generated-note"></div>
    <div class="toolbar">
        <button id="btnExport" type="button">บันทึกเป็นไฟล์</button>
        <button id="btnImport" type="button">เปิดไฟล์ที่บันทึกไว้</button>
        <button id="btnReset" type="button">ล้างตาราง</button>
        <input type="file" id="fileInput" accept=".json,application/json" hidden>
        <span id="saveStatus"></span>
    </div>
    <div id="gpaDisplay"></div>
</header>
<main>
    <div class="toolbar">
        <div>
            <label for="curriculum-select">หลักสูตร:</label>
            <select id="curriculum-select"></select>
        </div>
        <div>
            <label for="plan-select">แผนทางเลือก:</label>
            <select id="plan-select"></select>
        </div>
    </div>
    <div class="summary" id="summary"></div>
    <div id="content"></div>
</main>
<script>
const DATA = __DATA_JSON__;
const PLACEHOLDER_CODE = "xxxxxxxx";

const curriculumSelect = document.getElementById('curriculum-select');
const planSelect = document.getElementById('plan-select');
const summaryEl = document.getElementById('summary');
const contentEl = document.getElementById('content');

DATA.forEach((c, idx) => {
    const opt = document.createElement('option');
    opt.value = idx;
    opt.textContent = c.name;
    curriculumSelect.appendChild(opt);
});

function populatePlanSelect(curriculumIdx) {
    const c = DATA[curriculumIdx];
    planSelect.innerHTML = '';
    c.plans.forEach(p => {
        const opt = document.createElement('option');
        opt.value = p.id;
        opt.textContent = p.code ? (p.code + ' - ' + p.name) : p.name;
        planSelect.appendChild(opt);
    });
    // ค่าเริ่มต้น: แผนแรกในลิสต์ (PROJECT ถ้ามี) ไม่ใช่ "เฉพาะวิชาร่วม"
    planSelect.selectedIndex = 0;
}

function computeTotal(container) {
    let total = 0;
    container.querySelectorAll('td[data-credits]').forEach(el => {
        const val = parseInt(el.dataset.credits, 10);
        if (!isNaN(val)) total += val;
    });
    return total;
}

function updateSummaryTotal() {
    const container = contentEl;
    const total = computeTotal(container);
    const curriculumIdx = curriculumSelect.value;
    const c = DATA[curriculumIdx];
    const totalLine = summaryEl.querySelector('.total-line');
    if (totalLine) {
        totalLine.textContent = `หน่วยกิตตามตารางนี้ (รวมวิชาเลือกที่เลือกไว้/ประมาณการ): ${total} นก. | หน่วยกิตรวมหลักสูตร: ${c.total_credits} นก.`;
    }
}

function renderRequiredRow(row) {
    const tr = document.createElement('tr');
    tr.innerHTML = `
        <td>${row.code}</td>
        <td>${row.name_th}</td>
        <td class="credits" data-credits="${row.credits}">${row.credits}</td>
        <td>${row.group_name}</td>
        <td class="type"><span class="badge required">บังคับ</span></td>`;
        tr.appendChild(createGradeCell()); // เพิ่มช่องใส่เกรด
    return tr;
}

function renderElectiveRow(slot, slotIndex) {
    const tr = document.createElement('tr');
    const nameTd = document.createElement('td');
    const creditsTd = document.createElement('td');
    creditsTd.className = 'credits';

    if (slot.is_free_elective) {
        tr.classList.add('free-row');

        const nameInput = document.createElement('input');
        nameInput.className = 'free-input';
        nameInput.placeholder = 'พิมพ์รหัสวิชาที่มีในระบบ หรือพิมพ์ชื่อวิชาเอง';
        nameInput.value = slot.group_name;
        nameTd.appendChild(nameInput);

        creditsTd.dataset.credits = slot.default_credits;
        creditsTd.textContent = slot.default_credits;

        let matchedName = '';   // จำชื่อวิชาที่ auto-fill ล่าสุดไว้

        nameInput.addEventListener('input', () => {
            const codeCell = tr.cells[0];            // ช่องรหัสวิชา (ทำงานเป็น label)
            const text = nameInput.value.trim();
            const found = findCourseByCode(text);

            if (found) {
                const code = found.code || text;
                codeCell.textContent = code;
                codeCell.classList.add('selected-code');
                tr.dataset.code = code;
                nameInput.value = found.name_th;
                matchedName = found.name_th;
                creditsTd.textContent = found.credits;
                creditsTd.dataset.credits = found.credits;
            } else if (text !== matchedName) {
                // พิมพ์ชื่อเอง หรือแก้ชื่อไปแล้ว → คืนค่าเริ่มต้น
                codeCell.textContent = PLACEHOLDER_CODE;
                codeCell.classList.remove('selected-code');
                tr.dataset.code = '';
                matchedName = '';
                creditsTd.textContent = slot.default_credits;
                creditsTd.dataset.credits = slot.default_credits;
            }
            updateSummaryTotal();
        });
    } else {
        const select = document.createElement('select');
        select.className = 'elective-select';
        const placeholderOpt = document.createElement('option');
        placeholderOpt.value = '';
        placeholderOpt.textContent = `-- เลือกวิชาจาก: ${slot.group_name} (${slot.options.length} วิชาให้เลือก) --`;
        placeholderOpt.dataset.credits = slot.default_credits;
        select.appendChild(placeholderOpt);
        slot.options.forEach(o => {
            const opt = document.createElement('option');
            opt.value = o.code;
            opt.textContent = `${o.name_th} (${o.credits} นก.)`;
            opt.dataset.credits = o.credits;
            select.appendChild(opt);
        });
        creditsTd.dataset.credits = slot.default_credits;
        creditsTd.textContent = slot.default_credits;

        select.addEventListener('change', () => {
            const opt = select.options[select.selectedIndex];
            const credits = opt.dataset.credits || slot.default_credits;
            creditsTd.textContent = credits;
            creditsTd.dataset.credits = credits;

            // ใส่รหัสวิชาที่เลือกลงช่อง "รหัสวิชา"
            codeTd.textContent = opt.value || PLACEHOLDER_CODE;
            codeTd.classList.toggle('selected-code', !!opt.value);
            updateSummaryTotal();
        });
        nameTd.appendChild(select);
    }

    const codeTd = document.createElement('td');
    codeTd.textContent = PLACEHOLDER_CODE;
    const groupTd = document.createElement('td');
    groupTd.textContent = slot.group_name;
    const typeTd = document.createElement('td');
    typeTd.className = 'type';
    typeTd.innerHTML = '<span class="badge elective">เลือก</span>';

    tr.appendChild(codeTd);
    tr.appendChild(nameTd);
    tr.appendChild(creditsTd);
    tr.appendChild(groupTd);
    tr.appendChild(typeTd);
    tr.appendChild(createGradeCell());
    return tr;
}

function findCourseByCode(code) {
    // ค้นจากวิชาทั้งหมดที่ปรากฏใน options ของทุกกลุ่มเลือก + วิชาบังคับทั้งไฟล์ (ครอบคลุมพอสมควรสำหรับ preview)
    for (const c of DATA) {
        for (const key in c.data_by_plan) {
            const plan = c.data_by_plan[key];
            for (const y of plan.years) {
                for (const s of y.semesters) {
                    for (const r of s.required_rows) {
                        if (r.code === code) return r;
                    }
                    for (const slot of s.elective_slots) {
                        for (const o of slot.options) {
                            if (o.code === code) return o;
                        }
                    }
                }
            }
        }
    }
    return null;
}

function renderSchedule() {
    const curriculumIdx = curriculumSelect.value;
    const c = DATA[curriculumIdx];
    const planId = planSelect.value;
    const planData = c.data_by_plan[planId];
    const planObj = c.plans.find(p => String(p.id) === String(planId));

    summaryEl.innerHTML = '';
    const nameLine = document.createElement('div');
    nameLine.textContent = c.name + (planObj && planObj.code ? ` | แผน: ${planObj.code} - ${planObj.name}` : '');
    const totalLine = document.createElement('div');
    totalLine.className = 'total-line';
    summaryEl.appendChild(nameLine);
    summaryEl.appendChild(totalLine);
    const hint = document.createElement('div');
    hint.className = 'hint';
    hint.textContent = 'แถวรหัส xxxxxxxx คือช่องว่างวิชาเลือก — เลือกหรือกรอกรหัสวิชา(เลือกเสรี)';
    summaryEl.appendChild(hint);

    contentEl.innerHTML = '';
    if (planData.years.length === 0) {
        contentEl.innerHTML = '<div class="card"><p class="empty">ไม่มีข้อมูลแผนการศึกษาสำหรับตัวเลือกนี้</p></div>';
        updateSummaryTotal();
        return;
    }

    planData.years.forEach(y => {
        const yearBox = document.createElement('div');
        yearBox.className = 'card';
        const h2 = document.createElement('h2');
        h2.textContent = `ปีที่ ${y.year}`;
        yearBox.appendChild(h2);

        y.semesters.forEach(s => {
            const h3 = document.createElement('h3');
            h3.textContent = s.label;
            yearBox.appendChild(h3);

            const hasRows = s.required_rows.length > 0 || s.elective_slots.some(sl => sl.slot_count > 0);
            if (!hasRows) {
                const p = document.createElement('p');
                p.className = 'empty';
                p.textContent = 'ไม่มีวิชาในเทอมนี้';
                yearBox.appendChild(p);
                return;
            }

            const table = document.createElement('table');
            const thead = document.createElement('thead');
            thead.innerHTML = `<tr><th>รหัสวิชา</th><th>ชื่อวิชา</th><th class="credits">หน่วยกิต</th><th>หมวดวิชา</th><th class="type">ประเภท</th></tr>`;
            const tbody = document.createElement('tbody');
            s.required_rows.forEach(row => tbody.appendChild(renderRequiredRow(row)));
            s.elective_slots.forEach(slot => {
                for (let i = 0; i < slot.slot_count; i++) {
                    tbody.appendChild(renderElectiveRow(slot, i));
                }
            });
            table.appendChild(thead);
            table.appendChild(tbody);
            yearBox.appendChild(table);

            const termTotal = document.createElement('div');
            termTotal.className = 'term-total';
            termTotal.textContent = 'รวม (ประมาณการวิชาเลือกที่ยังไม่ได้เลือกด้วย)';
            yearBox.appendChild(termTotal);
        });

        const yearTotal = document.createElement('div');
        yearTotal.className = 'year-total';
        yearTotal.textContent = `รวมปีที่ ${y.year}: ${y.credits} หน่วยกิต`;
        yearBox.appendChild(yearTotal);

        contentEl.appendChild(yearBox);
    });

    updateSummaryTotal();
}

curriculumSelect.addEventListener('change', () => {
    populatePlanSelect(curriculumSelect.value);
    renderSchedule();
});
planSelect.addEventListener('change', renderSchedule);

if (DATA.length > 0) {
    populatePlanSelect(0);
    renderSchedule();
}
// เพิื่มเติม บันทึกและคำนวนเกรด
function createGradeCell() {
    const td = document.createElement('td');
    const sel = document.createElement('select');
    sel.className = 'grade-select';
    ['', 'A', 'B+', 'B', 'C+', 'C', 'D+', 'D', 'F', 'S', 'U'].forEach(g => {
        const o = document.createElement('option');
        o.value = g;
        o.textContent = g || '-';
        sel.appendChild(o);
    });
    td.appendChild(sel);
    return td;
}

/* ===== อ่าน/เขียน ข้อมูลในแถว ===== */
function readRow(tr) {
    const select    = tr.querySelector('.elective-select');
    const nameInput = tr.querySelector('.free-input');
    const grade     = tr.querySelector('.grade-select');
    const credits   = tr.querySelector('.credits');

    return {
        code:    select ? select.value : (tr.dataset.code || ''),
        name:    nameInput?.value || '',
        credits: credits?.dataset.credits || '',
        grade:   grade ? grade.value : ''
    };
}

function writeRow(tr, d) {
    const select    = tr.querySelector('.elective-select');
    const nameInput = tr.querySelector('.free-input');
    const grade     = tr.querySelector('.grade-select');

    if (select && d.code) {
        select.value = d.code;
        select.dispatchEvent(new Event('change'));
    }
    if (nameInput) {
        if (d.code) {                                  // ให้ auto-fill จากรหัสก่อน
            nameInput.value = d.code;
            nameInput.dispatchEvent(new Event('input'));
        }
        if (d.name) nameInput.value = d.name;          // แล้วใส่ชื่อที่บันทึกไว้
    }
    if (grade) grade.value = d.grade || '';
}

function getPlanRows() {
    return [...document.querySelectorAll('tr')].filter(tr => tr.querySelector('.grade-select'));
}

function getCurriculumName() {
    // 1) จากตัวแปรข้อมูลในไฟล์ (ชื่ออาจต่างจากนี้ ดูหมายเหตุด้านล่าง)
    if (typeof DATA !== 'undefined') {
        const n = DATA.curriculum_name || DATA.curriculum || DATA.name_th || DATA.program_name;
        if (n) return n;
    }
    // 2) จากหัวข้อบนหน้าเว็บ
    const el = document.querySelector('h1, h2, .curriculum-name, #curriculumName');
    if (el && el.textContent.trim()) return el.textContent.trim();

    return 'แผนการเรียน';
}

// ตัดอักขระที่ใช้ตั้งชื่อไฟล์ไม่ได้ออก
function safeFileName(s) {
    return s.replace(/[\\/:*?"<>|]/g, '')   // อักขระต้องห้ามของ Windows
            .replace(/\s+/g, '_')
            .slice(0, 80);                   // กันชื่อยาวเกิน
}


/* ===== บันทึกลงไฟล์ ===== */
async function exportFile() {
    const rows = getPlanRows().map(readRow);
    const filled = rows.filter(r => r.code || r.grade).length;

    if (!filled) {
        showStatus('ยังไม่มีข้อมูลให้บันทึก', true);
        return;
    }

    const curriculum = getCurriculumName();
    const stamp = new Date().toLocaleString('sv-SE').replace(/[: ]/g, '-').slice(0, 16);
    const suggested = `${safeFileName(curriculum)}_${stamp}.json`;

    const payload = {
        app: 'study-plan',
        version: 1,
        curriculum,                         // เก็บชื่อหลักสูตรไว้ในไฟล์ด้วย
        savedAt: new Date().toISOString(),
        rowCount: rows.length,
        rows
    };
    const text = JSON.stringify(payload, null, 2);

    // --- วิธีที่ 1: ให้เลือกตำแหน่งเอง (Chrome / Edge) ---
    if (window.showSaveFilePicker) {
        try {
            const handle = await window.showSaveFilePicker({
                suggestedName: suggested,
                types: [{
                    description: 'ไฟล์แผนการเรียน',
                    accept: { 'application/json': ['.json'] }
                }]
            });
            const w = await handle.createWritable();
            await w.write(text);
            await w.close();
            showStatus(`บันทึกเป็น ${handle.name} แล้ว (${filled} รายการ)`);
            return;
        } catch (err) {
            if (err.name === 'AbortError') {       // ผู้ใช้กดยกเลิก
                showStatus('ยกเลิกการบันทึก');
                return;
            }
            // กรณีอื่นให้ตกไปใช้วิธีสำรองด้านล่าง
        }
    }

    // --- วิธีที่ 2: สำรอง (Firefox / Safari) ---
    const blob = new Blob([text], { type: 'application/json' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = suggested;
    a.click();
    URL.revokeObjectURL(a.href);
    showStatus(`บันทึกไฟล์แล้ว (${filled} รายการ) — ดูในโฟลเดอร์ Downloads`);
}
/* ===== อ่านจากไฟล์ ===== */
function importFile(file) {
    if (!file) return;

    const reader = new FileReader();

    reader.onload = e => {
        let data;
        try {
            data = JSON.parse(e.target.result);
        } catch {
            showStatus('ไฟล์นี้ไม่ใช่ JSON ที่ถูกต้อง', true);
            return;
        }

        if (!data.rows || !Array.isArray(data.rows)) {
            showStatus('ไฟล์นี้ไม่ใช่ไฟล์แผนการเรียน', true);
            return;
        }

        if (data.curriculum && data.curriculum !== getCurriculumName()) {
            const ok = confirm(
                `ไฟล์นี้เป็นของหลักสูตร "${data.curriculum}"\n` +
                `แต่หน้านี้คือ "${getCurriculumName()}"\n\nต้องการโหลดต่อหรือไม่?`
            );
            if (!ok) return;
        }

        const trs = getPlanRows();
        if (data.rowCount && data.rowCount !== trs.length) {
            const ok = confirm(
                `ไฟล์นี้บันทึกไว้ ${data.rowCount} แถว แต่ตารางปัจจุบันมี ${trs.length} แถว\n` +
                `ข้อมูลอาจเลื่อนไม่ตรงแถว ต้องการโหลดต่อหรือไม่?`
            );
            if (!ok) return;
        }

        data.rows.forEach((d, i) => { if (trs[i]) writeRow(trs[i], d); });
        updateGPA();

        const when = data.savedAt ? new Date(data.savedAt).toLocaleString('th-TH') : 'ไม่ทราบเวลา';
        showStatus(`โหลดสำเร็จ (ไฟล์บันทึกเมื่อ ${when})`);
    };

    reader.onerror = () => showStatus('อ่านไฟล์ไม่สำเร็จ', true);
    reader.readAsText(file, 'utf-8');
}

/* ===== ล้างตาราง ===== */
function resetTable() {
    // if (!confirm('ล้างข้อมูลที่กรอกไว้ทั้งหมดในตารางนี้?')) return;

    getPlanRows().forEach(tr => {
        const select = tr.querySelector('.elective-select');
        const grade  = tr.querySelector('.grade-select');
        if (select) { select.selectedIndex = 0; select.dispatchEvent(new Event('change')); }
        if (grade) grade.value = '';
        tr.querySelectorAll('.free-input').forEach(inp => {
            if (inp.classList.contains('free-code')) {
                inp.value = '';
                inp.dispatchEvent(new Event('input'));
            }
        });
    });

    updateGPA();
    showStatus('ล้างตารางแล้ว');
}

function showStatus(msg, isError) {
    const el = document.getElementById('saveStatus');
    if (!el) return;
    el.textContent = msg;
    el.style.color = isError ? '#dc2626' : '#16a34a';
    clearTimeout(showStatus._t);
    showStatus._t = setTimeout(() => el.textContent = '', 5000);
}

/* ===== คำนวณ GPA ===== */
const GRADE_POINT = { 'A': 4.0, 'B+': 3.5, 'B': 3.0, 'C+': 2.5, 'C': 2.0, 'D+': 1.5, 'D': 1.0, 'F': 0.0 };

function updateGPA() {
    let point = 0, credit = 0;

    document.querySelectorAll('.grade-select').forEach(sel => {
        const g = sel.value;
        if (!(g in GRADE_POINT)) return;          // ข้าม '', S, U

        const cell = sel.closest('tr').querySelector('.credits');
        const c = parseFloat(cell?.dataset.credits || 0);
        if (!c) return;

        point  += GRADE_POINT[g] * c;
        credit += c;
    });

    const el = document.getElementById('gpaDisplay');
    if (el) {
        el.textContent = credit
            ? `GPA: ${(point / credit).toFixed(2)}  (หน่วยกิตที่คิดเกรด ${credit})`
            : 'GPA: ยังไม่ได้กรอกเกรด';
    }
}

/* ===== ผูกปุ่ม ===== */
const fileInput = document.getElementById('fileInput');

document.getElementById('btnExport').addEventListener('click', exportFile);
document.getElementById('btnReset').addEventListener('click', resetTable);
document.getElementById('btnImport').addEventListener('click', () => fileInput.click());

fileInput.addEventListener('change', e => {
    importFile(e.target.files[0]);
    e.target.value = '';          // รีเซ็ตเพื่อให้เลือกไฟล์เดิมซ้ำได้
});

document.addEventListener('change', e => {
    if (e.target.classList.contains('grade-select')) updateGPA();
});

/* ===== ลากไฟล์มาวางบนหน้าเว็บก็ได้ ===== */
document.addEventListener('dragover', e => { e.preventDefault(); document.body.classList.add('dragging'); });
document.addEventListener('dragleave', e => { if (e.relatedTarget === null) document.body.classList.remove('dragging'); });
document.addEventListener('drop', e => {
    e.preventDefault();
    document.body.classList.remove('dragging');
    importFile(e.dataTransfer.files[0]);
});

</script>
</body>
</html>
"""


if __name__ == "__main__":
    export()
