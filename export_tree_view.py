"""
export_tree_view.py
---------------------
ดึงข้อมูลหมวดวิชาของทุกหลักสูตรจากฐานข้อมูล แล้วสร้างไฟล์ HTML แบบ "static" ไฟล์เดียว
(ฝังข้อมูลไว้ข้างในไฟล์เลย) เปิดดูได้ทันทีด้วยการดับเบิลคลิกในเบราว์เซอร์
ไม่ต้องรันเซิร์ฟเวอร์ ไม่ต้องใช้ npm/uvicorn ใดๆ ทั้งสิ้น

วิธีใช้ (จากโฟลเดอร์ project เป็น working directory):
    python export_tree_view.py

จะได้ไฟล์ tree_view.html ขึ้นมา — เปิดไฟล์นี้ด้วยเบราว์เซอร์ได้เลย
ถ้าข้อมูลในฐานข้อมูลเปลี่ยน ให้รันสคริปต์นี้ใหม่อีกครั้งเพื่ออัปเดตไฟล์ (เหมือนรัน seed_data.py)
"""

import json

from data.database import init_db, get_session
from data import repository as repo


def build_curriculum_tree(session, curriculum) -> dict:
    """สร้างโครงสร้าง tree ของ 1 หลักสูตร พร้อมข้อมูลครบสำหรับแสดงผลแบบ static"""
    requirements = {r.group_id: r for r in repo.list_group_requirements(session, curriculum.id)}
    tree = repo.get_group_tree(session, curriculum_id=curriculum.id)

    def enrich(node: dict) -> dict:
        req = requirements.get(node["id"])
        node["min_credits"] = req.min_credits if req else None
        node["max_credits"] = req.max_credits if req else None
        enriched_courses = []
        for c in node["courses"]:
            course = repo.get_course(session, c["code"])
            enriched_courses.append({
                "code": c["code"],
                "name_th": course.name_th if course else c["code"],
                "credits": course.credits if course else 0,
                "is_required": c["is_required"],
                "recommended_year": c["recommended_year"],
                "recommended_semester": c["recommended_semester"],
            })
        node["courses"] = enriched_courses
        node["children"] = [enrich(child) for child in node["children"]]
        return node

    tree = [enrich(node) for node in tree]

    # เรียงให้หมวดของหลักสูตรเองขึ้นก่อน หมวดศึกษาทั่วไป (GenEd, curriculum_id=None) ไว้ล่างสุด
    all_top_groups = {
        g.id: g for g in repo.list_course_groups(session, curriculum_id=curriculum.id, top_level_only=True)
    }
    tree = sorted(tree, key=lambda n: all_top_groups[n["id"]].curriculum_id is None)

    return {
        "id": curriculum.id,
        "name": curriculum.name,
        "faculty": curriculum.faculty,
        "year": curriculum.year,
        "total_credits": curriculum.total_credits,
        "tree": tree,
    }


def export():
    init_db()
    session = get_session()
    try:
        curricula_data = [build_curriculum_tree(session, c) for c in repo.list_curricula(session)]
    finally:
        session.close()

    data_json = json.dumps(curricula_data, ensure_ascii=False)

    html = HTML_TEMPLATE.replace("__DATA_JSON__", data_json)
    with open("tree_view.html", "w", encoding="utf-8") as f:
        f.write(html)

    print(f"สร้างไฟล์ tree_view.html สำเร็จ ({len(curricula_data)} หลักสูตร)")
    print("เปิดไฟล์ tree_view.html ด้วยเบราว์เซอร์ได้เลย (ดับเบิลคลิก) ไม่ต้องรันเซิร์ฟเวอร์ใดๆ")


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="UTF-8">
<title>หมวดวิชา (Tree View) - ระบบจัดการหลักสูตร</title>
<style>
    * { box-sizing: border-box; }
    body {
        font-family: "Sarabun", "Segoe UI", sans-serif;
        margin: 0; background: #f5f6f8; color: #222;
    }
    header {
        background: #1f2d3d; padding: 16px 24px; color: #fff;
    }
    header h1 { margin: 0; font-size: 18px; }
    header .note { font-size: 12px; color: #9fb0c3; margin-top: 4px; }
    main { max-width: 1000px; margin: 20px auto; padding: 0 20px 40px; }
    .toolbar {
        background: #fff; padding: 14px 18px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        margin-bottom: 16px;
    }
    .toolbar label { font-size: 14px; color: #555; margin-right: 8px; }
    .toolbar select { padding: 6px 10px; border-radius: 6px; border: 1px solid #ccc; font-size: 14px; min-width: 320px; }
    .curriculum-meta { font-size: 13px; color: #777; margin-top: 8px; }
    .card {
        background: #fff; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        padding: 16px 18px;
    }
    ul.tree { list-style: none; margin: 0; padding-left: 0; }
    ul.tree ul { list-style: none; padding-left: 22px; border-left: 1px dashed #ddd; margin-top: 4px; }
    .tree-group {
        font-weight: 600; color: #1f2d3d; padding: 5px 4px; cursor: pointer; user-select: none;
        border-radius: 4px;
    }
    .tree-group:hover { background: #f0f3f7; }
    .tree-group .meta { font-weight: 400; color: #888; font-size: 12px; margin-left: 8px; }
    .tree-group::before { content: "▸ "; color: #999; display: inline-block; width: 12px; }
    .tree-group.open::before { content: "▾ "; }
    .tree-children { margin-left: 4px; }
    .tree-course {
        padding: 3px 4px 3px 24px; font-size: 13.5px; color: #333;
        display: flex; justify-content: space-between; gap: 10px; border-radius: 4px;
    }
    .tree-course:hover { background: #fafbfc; }
    .tree-course .name { flex: 1; }
    .tree-course .info { color: #888; font-size: 12px; white-space: nowrap; }
    .badge { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 11px; margin-left: 6px; }
    .badge.required { background: #dbeafe; color: #1d4ed8; }
    .badge.elective { background: #fef3c7; color: #92400e; }
    .search-box { margin-bottom: 12px; }
    .search-box input {
        width: 100%; padding: 8px 12px; border-radius: 6px; border: 1px solid #ccc; font-size: 14px;
    }
    .hidden { display: none !important; }
</style>
</head>
<body>
<header>
    <h1>📚 หมวดวิชา (Tree View)</h1>
    <div class="note" id="generated-note"></div>
</header>
<main>
    <div class="toolbar">
        <label for="curriculum-select">หลักสูตร:</label>
        <select id="curriculum-select"></select>
        <div class="curriculum-meta" id="curriculum-meta"></div>
    </div>
    <div class="search-box">
        <input type="text" id="search-input" placeholder="ค้นหาชื่อวิชาหรือรหัสวิชา...">
    </div>
    <div class="card">
        <ul class="tree" id="tree-root"></ul>
    </div>
</main>
<script>
const DATA = __DATA_JSON__;

const curriculumSelect = document.getElementById('curriculum-select');
const curriculumMeta = document.getElementById('curriculum-meta');
const treeRoot = document.getElementById('tree-root');
const searchInput = document.getElementById('search-input');
document.getElementById('generated-note').textContent =
    'ข้อมูล ณ ตอนสร้างไฟล์นี้ (สแนปช็อต) — รันสคริปต์ export_tree_view.py ใหม่หากข้อมูลเปลี่ยน';

DATA.forEach((c, idx) => {
    const opt = document.createElement('option');
    opt.value = idx;
    opt.textContent = c.name;
    curriculumSelect.appendChild(opt);
});

function renderCourse(course) {
    const div = document.createElement('div');
    div.className = 'tree-course';
    const badgeClass = course.is_required ? 'required' : 'elective';
    const badgeText = course.is_required ? 'บังคับ' : 'เลือก';
    let termText = '';
    if (course.recommended_year) termText += ' | ปี ' + course.recommended_year;
    if (course.recommended_semester) termText += '/' + course.recommended_semester;
    div.innerHTML = `
        <span class="name">${course.code} - ${course.name_th}</span>
        <span class="info">${course.credits} นก.
            <span class="badge ${badgeClass}">${badgeText}</span>${termText}
        </span>`;
    div.dataset.searchText = (course.code + ' ' + course.name_th).toLowerCase();
    return div;
}

function renderGroup(node) {
    const li = document.createElement('li');

    const groupDiv = document.createElement('div');
    groupDiv.className = 'tree-group open';
    let metaText = node.group_type;
    if (node.min_credits !== null && node.min_credits !== undefined) {
        metaText += ' | ขั้นต่ำ ' + node.min_credits + ' นก.';
        if (node.max_credits) metaText += ' (สูงสุด ' + node.max_credits + ')';
    }
    groupDiv.innerHTML = node.name + '<span class="meta">' + metaText + '</span>';

    const childrenDiv = document.createElement('div');
    childrenDiv.className = 'tree-children';

    if (node.children && node.children.length > 0) {
        const ul = document.createElement('ul');
        ul.className = 'tree';
        node.children.forEach(child => ul.appendChild(renderGroup(child)));
        childrenDiv.appendChild(ul);
    }
    node.courses.forEach(course => childrenDiv.appendChild(renderCourse(course)));

    groupDiv.addEventListener('click', () => {
        groupDiv.classList.toggle('open');
        childrenDiv.style.display = groupDiv.classList.contains('open') ? 'block' : 'none';
    });

    li.appendChild(groupDiv);
    li.appendChild(childrenDiv);
    return li;
}

function renderCurriculum(idx) {
    const c = DATA[idx];
    curriculumMeta.textContent =
        (c.faculty || '-') + ' | ปี พ.ศ. ' + c.year + ' | รวม ' + c.total_credits + ' หน่วยกิต';
    treeRoot.innerHTML = '';
    c.tree.forEach(node => treeRoot.appendChild(renderGroup(node)));
    searchInput.value = '';
}

curriculumSelect.addEventListener('change', () => renderCurriculum(curriculumSelect.value));

searchInput.addEventListener('input', () => {
    const q = searchInput.value.trim().toLowerCase();
    const courseEls = treeRoot.querySelectorAll('.tree-course');
    const groupEls = treeRoot.querySelectorAll('.tree-group');

    if (!q) {
        courseEls.forEach(el => el.classList.remove('hidden'));
        groupEls.forEach(el => {
            el.classList.remove('open');
            el.classList.add('open');
            if (el.nextElementSibling) el.nextElementSibling.style.display = 'block';
        });
        return;
    }

    courseEls.forEach(el => {
        const match = el.dataset.searchText.includes(q);
        el.classList.toggle('hidden', !match);
        if (match) {
            // เปิดหมวดที่เป็นพ่อแม่ทุกชั้น เพื่อให้เห็นวิชาที่ค้นเจอ
            let parent = el.closest('.tree-children');
            while (parent) {
                const groupDiv = parent.previousElementSibling;
                if (groupDiv && groupDiv.classList.contains('tree-group')) {
                    groupDiv.classList.add('open');
                    parent.style.display = 'block';
                }
                const li = parent.closest('li');
                parent = li ? li.parentElement.closest('.tree-children') : null;
            }
        }
    });
});

if (DATA.length > 0) renderCurriculum(0);
</script>
</body>
</html>
"""


if __name__ == "__main__":
    export()
