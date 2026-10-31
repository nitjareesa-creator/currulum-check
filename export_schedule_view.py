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
</style>
</head>
<body>
<header>
    <h1>📅 แผนการศึกษารายเทอม</h1>
    <div class="note" id="generated-note"></div>
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
document.getElementById('generated-note').textContent =
    'ข้อมูล ณ ตอนสร้างไฟล์นี้ (สแนปช็อต) — รันสคริปต์ export_schedule_view.py ใหม่หากข้อมูลเปลี่ยน '
    + '| การเลือกวิชา/กรอกวิชาเองในหน้านี้เป็นแค่การดูตัวอย่าง ไม่ได้บันทึกที่ไหน ปิดหน้าเว็บแล้วหายไป';

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
    return tr;
}

function renderElectiveRow(slot, slotIndex) {
    const tr = document.createElement('tr');
    const nameTd = document.createElement('td');
    const creditsTd = document.createElement('td');
    creditsTd.className = 'credits';

    if (slot.is_free_elective) {
        tr.classList.add('free-row');
        const wrap = document.createElement('div');
        wrap.className = 'free-labels';
        const codeInput = document.createElement('input');
        codeInput.className = 'free-input';
        codeInput.placeholder = 'รหัสวิชา';
        codeInput.value = PLACEHOLDER_CODE;
        const nameInput = document.createElement('input');
        nameInput.className = 'free-input';
        nameInput.placeholder = 'พิมพ์ชื่อวิชาเอง หรือรหัสวิชาที่มีในระบบ';
        nameInput.value = slot.group_name;
        wrap.appendChild(codeInput);
        wrap.appendChild(nameInput);
        nameTd.appendChild(wrap);

        creditsTd.dataset.credits = slot.default_credits;
        creditsTd.textContent = slot.default_credits;

        // auto-fill ถ้าพิมพ์รหัสที่ตรงกับวิชาในหลักสูตรนี้ (ค้นจากทุกวิชาที่ปรากฏใน DATA ทั้งไฟล์)
        codeInput.addEventListener('input', () => {
            const code = codeInput.value.trim();
            const found = findCourseByCode(code);
            if (found) {
                nameInput.value = found.name_th;
                creditsTd.textContent = found.credits;
                creditsTd.dataset.credits = found.credits;
                updateSummaryTotal();
            }
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
            opt.textContent = `${o.code} - ${o.name_th} (${o.credits} นก.)`;
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
    hint.textContent = 'แถวรหัส xxxxxxxx คือช่องว่างวิชาเลือก — เลือก/กรอกวิชาเพื่อดูตัวอย่าง (ไม่บันทึก)';
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
</script>
</body>
</html>
"""


if __name__ == "__main__":
    export()
