"""
seed_data.py
------------
ใส่ข้อมูลตัวอย่างลงฐานข้อมูล อ้างอิงโครงสร้างหลักสูตรจริงจากเอกสารหลักสูตร + แผนการศึกษา (ไฟล์แนบ) ของ:

  1) หลักสูตรวิทยาศาสตรบัณฑิต สาขาวิชาฟิสิกส์อุตสาหกรรม (ปรับปรุง พ.ศ. 2569)   รวม 122 หน่วยกิต
  2) หลักสูตรวิศวกรรมศาสตรบัณฑิต สาขาวิชาวิศวกรรมระบบไอโอทีและสารสนเทศ (ปรับปรุง พ.ศ. 2569)  รวม 138 หน่วยกิต
  3) หลักสูตรวิศวกรรมศาสตรบัณฑิต สาขาวิชาวิศวกรรมคอมพิวเตอร์และไอโอที (ต่อเนื่อง) (ปรับปรุง พ.ศ. 2569)  รวม 118 หน่วยกิต

หมายเหตุสำคัญเกี่ยวกับความถูกต้องของข้อมูล:
- รหัสวิชา ชื่อวิชา หน่วยกิต และ "ปี/เทอมที่เรียน" ของทุกวิชาในไฟล์นี้ ตรงกับไฟล์แผนการศึกษาจริงที่ผู้ใช้แนบมา
- คู่วิชาเทียบเคียง (CourseEquivalency) ทั้งหมดตรงตามไฟล์ตารางเทียบที่แนบมา (แถวที่มีวิชาทั้งสองฝั่ง = เทียบกันได้)
- แต่ "หมวดวิชาย่อยของแต่ละวิชา" (พื้นฐาน/บังคับ/เลือก/บังคับเลือก) เป็น "การจัดกลุ่มโดยประมาณ" ที่ผู้ช่วยจัดให้
  เพราะไฟล์แผนการศึกษาไม่ได้ระบุหมวดย่อยต่อรายวิชาไว้ตรงๆ มีแค่ตัวเลขรวมหน่วยกิตต่อหมวดในเอกสารหลักสูตร
  ผู้ใช้ควรตรวจทานการจัดกลุ่มนี้อีกครั้ง ตัวเลข min_credits ต่อหมวดใน CurriculumGroupRequirement
  ยังคงอ้างอิงจากเอกสารหลักสูตรจริงเป๊ะทุกจุด ไม่ได้เปลี่ยนตามการจัดกลุ่มโดยประมาณนี้
- ปีที่ 4 มี "แผนทางเลือก" (StudyPlan) 2 แบบ: PROJECT (ทำโครงงานพิเศษ) และ COOP (สหกิจศึกษา/ฝึกงานต่างประเทศ)
  วิชาที่ผูกกับ study_plan_id ใดวิชานั้นจะปรากฏเฉพาะแผนนั้น ส่วนวิชาที่ study_plan_id เป็น NULL ใช้ร่วมกันทุกแผน

การปรับปรุงจากเวอร์ชันก่อน:
- เพิ่ม helper function `link_gened_for_curriculum()` ใช้ default + override pattern
  ทำให้เห็นชัดว่าแต่ละหลักสูตรต่างจาก default ตรงไหน โดยไม่ต้องเขียนซ้ำทีละวิชา
- ใช้ `GENED_IDENTITY_DEFAULTS` เก็บค่า default year/semester/is_required/group ของ GenEd กลุ่มอัตลักษณ์ฯ
  ไว้ที่เดียว — แก้ทีเดียวกระทบทุกหลักสูตรที่ใช้ default
"""

from data.database import init_db, get_session, engine
from data.models import (
    Base,
    Course,
    CourseGroup,
    Curriculum,
    CurriculumCourse,
    CurriculumGroupRequirement,
    CourseEquivalency,
    ElectiveTermSlot,
    StudyPlan,
    GroupType,
    EquivalenceType,
)


def reset_db() -> None:
    """ล้างตารางเดิมทั้งหมดแล้วสร้างใหม่ (ใช้สำหรับรัน seed ซ้ำได้เรื่อยๆ ตอนพัฒนา)"""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def seed() -> None:
    reset_db()
    session = get_session()

    try:
        # -------------------------------------------------------------
        # 1) หมวดวิชาศึกษาทั่วไป (GenEd) — หมวดกลางของสถาบัน ใช้ร่วมกันทุกหลักสูตร
        # -------------------------------------------------------------
        gened_root = CourseGroup(name="หมวดวิชาศึกษาทั่วไป", group_type=GroupType.GENED)
        gened_identity = CourseGroup(
            name="กลุ่มทักษะส่งเสริมอัตลักษณ์สถาบันฯ", group_type=GroupType.GENED, parent=gened_root
        )
        gened_language = CourseGroup(
            name="กลุ่มวิชาเลือกด้านภาษาและการสื่อสาร", group_type=GroupType.GENED, parent=gened_root
        )
        gened_elective = CourseGroup(
            name="กลุ่มวิชาเลือกหมวดวิชาศึกษาทั่วไป", group_type=GroupType.GENED, parent=gened_root
        )
        session.add_all([gened_root, gened_identity, gened_language, gened_elective])
        session.flush()

        # กลุ่มทักษะส่งเสริมอัตลักษณ์สถาบันฯ (ข้อมูลจริง รวม 12 หน่วยกิต ตามเอกสาร)
        identity_courses = [
            Course(code="90641004", name_th="โครงงานกลุ่ม 1", name_en="Team-Project 1", credits=1),
            Course(code="90641005", name_th="โครงงานกลุ่ม 2", name_en="Team-Project 2", credits=1),
            Course(code="90641006", name_th="โครงงานกลุ่ม 3", name_en="Team-Project 3", credits=1),
            Course(code="90641007", name_th="พลเมืองดิจิทัล", name_en="Digital Citizen", credits=3),
            Course(
                code="90641008", name_th="พื้นฐานทักษะการสื่อสารภาษาอังกฤษ",
                name_en="Introduction to English Communication Skills", credits=0,
            ),
            Course(
                code="90641009", name_th="ทักษะการสื่อสารภาษาอังกฤษระหว่างวัฒนธรรม 1",
                name_en="Intercultural Communication Skills in English 1", credits=3,
            ),
            Course(
                code="90641010", name_th="ทักษะการสื่อสารภาษาอังกฤษระหว่างวัฒนธรรม 2",
                name_en="Intercultural Communication Skills in English 2", credits=3,
            ),
        ]

        gened_extra_courses = [
            Course(code="90642036", name_th="เตรียมความพร้อมสำหรับวิศวกร", name_en="Pre-Activities for Engineers", credits=1),
            Course(code="90642118", name_th="โปรแกรมคอมพิวเตอร์ประยุกต์ทางธุรกิจ", name_en="Application Software for Business", credits=2),
        ]

        # กลุ่มวิชาเลือกด้านภาษาและการสื่อสาร
        GENED_LANGUAGE_COMMUNICATION_RAW = """
90644001|ปฏิบัติงานตามทักษะด้านการสื่อสาร 1|Practice under Language and Communication Skills 1|1
90644002|ปฏิบัติงานตามทักษะด้านการสื่อสาร 2|Practice under Language and Communication Skills 2|2
90644003|ปฏิบัติงานตามทักษะด้านการสื่อสาร 3|Practice under Language and Communication Skills 3|3
90644009|การออกเสียงภาษาอังกฤษเบื้องต้น|Basic English Pronunciation|3
90644010|การพัฒนาทักษะการอ่านและการเขียนภาษาอังกฤษ|Development of Reading and Writing Skills in English|3
90644011|ภาษาอังกฤษเชิงวิชาการ|English for Academic Purposes|3
90644012|ภาษาอังกฤษเพื่อการสื่อสาร|English for Communication|3
90644013|การเขียนภาษาอังกฤษเพื่อการสื่อสาร|English for Communicative Writing|3
90644014|ภาษาอังกฤษเพื่อการสื่อสารทางวิชาชีพ|English for Professional Communication|3
90644015|ภาษาอังกฤษเพื่อการศึกษาต่อ|English for Further Studies|3
90644016|อังกฤษเพื่ออุตสาหกรรม|English for Industry|3
90644017|ภาษาอังกฤษสำหรับธุรกิจ|English for Business|3
90644018|ภาษาอังกฤษเพื่อการตลาด|English for Marketing|3
90644019|ภาษาอังกฤษเพื่อการจัดการ|English for Management|3
90644020|ภาษาอังกฤษเพื่อความเข้าใจข่าวสาร|English for Media|3
90644022|ภาษาอังกฤษสำหรับมืออาชีพ|English for Professional Purposes|3
90644023|ภาษาอังกฤษเพื่อเตรียมตัวทำงาน|English for Work Preparation|3
90644024|ภาษาอังกฤษเพื่อการท่องเที่ยวและการเดินทาง|English for Tourism and Travelling|3
90644025|ภาษาอังกฤษเพื่อการสื่อสารในงานสถาปัตยกรรม|English for Architectural Arts and Design Communication|3
90644026|ภาษาอังกฤษเพื่อการนำเสนอในงานสถาปัตยกรรม|English for Architectural Arts and Design Presentation|3
90644027|ภาษาอังกฤษสำหรับการเขียนพรรณนา|English for Narrative Writing|3
90644028|ภาษาอังกฤษเพื่อการออกแบบ|English for Design|3
90644029|ภาษาอังกฤษสำหรับวิชาชีพสุขภาพ|English for Health Professions|3
90644030|ภาษาอังกฤษเพื่อการประชาสัมพันธ์|English for Public Relations|3
90644031|ภาษาอังกฤษสำหรับวิทยาศาสตร์และเทคโนโลยี|English for Science and Technology|3
90644032|ภาษาอังกฤษสำหรับการบิน|English for Aviation|3
90644033|การเขียนและการพูดในงานอาชีพ|Writing and Speaking in the Professions|3
90644034|การเขียนทางเทคนิค|Technical Writing|3
90644035|การอ่านและเขียนเชิงวิชาการสำหรับวิทยาศาสตร์สุขภาพ|Academic Reading and Writing for Health Sciences|3
90644036|การพัฒนาทักษะทางภาษาอังกฤษเพื่อการเรียนรู้ตลอดชีวิต|English Skill Development for Life-Long Learning|3
90644037|การสื่อสารข้ามวัฒนธรรม|Cross Cultural Communication|3
90644039|ทักษะการสื่อสารผ่านการอภิปราย|Communication Skills through Debate|3
90644040|ทักษะการสื่อสารผ่านละคร|Communication Skills through Drama|3
90644041|ภาษาอังกฤษจากสื่อบันเทิง|English from Entertainment Media|3
90644042|การสื่อสารและการนำเสนออย่างมืออาชีพ|Professional Communication and Presentation|3
90644043|การพูดในที่สาธารณะ|Public Speaking|3
90644044|พูดได้ พูดดี พูดเป็น|Best Speech|3
90644045|การค้นคว้าและการเขียนรายงาน|Research Paper Writing|3
90644046|การฟังและการอ่านเพื่อพัฒนาคุณภาพชีวิต|Listening and Reading for Improving Life Quality|3
90644047|การพัฒนาทักษะการเขียนภาษาไทยเชิงสร้างสรรค์|Development of Thai Creative Writing Skills|3
90644048|ภาษาในสังคมไทย|Language in Thai Society|3
90644049|ภาษาไทยเพื่อการสร้างสรรค์|Thai Language for Creativity|3
90644050|การเขียนภาษาไทยในที่ทำงาน|Thai Writing in Workplace|3
90644051|ภาษาไทยสำหรับทันตแพทย์|Thai for Dental Professions|3
90644052|ศิลปะการสื่อสารสำหรับมืออาชีพด้านอาหาร|Communication in Thai for Culinary Professionals|3
90644053|การฟังและการพูดภาษาจีนพื้นฐาน|Fundamental Chinese for Listening and Speaking|3
90644054|การอ่านและเขียนภาษาจีนพื้นฐาน|Fundamental Chinese Reading and Writing|3
90644055|ไวยากรณ์ภาษาจีนพื้นฐาน และสำนวนและสุภาษิตภาษาจีน|Basic Chinese Grammar and Chinese Idioms and Proverbs|3
90644056|วัฒนธรรม สำนวนและสุภาษิตจีน|Chinese Culture Idioms and Proverbs|3
90644057|ภาษาจีนเพื่อการสื่อสาร|Chinese for Communication|3
90644058|ภาษาจีนฉบับแฟนดอม|Chinese Fandom|3
90644059|ภาษาจีนเพื่อการท่องเที่ยว|Chinese for Travel|3
90644060|ภาษาเยอรมันเพื่อการสื่อสาร|German for Communication|3
90644061|ภาษาเยอรมันเพื่อการทำงานและธุรกิจ|German for Work and Business|3
90644062|ภาษาญี่ปุ่นเพื่อการสื่อสาร|Japanese for Communication|3
90644063|ภาษาญี่ปุ่นเพื่อการท่องเที่ยว|Japanese for Travel|3
90644064|ภาษาเกาหลีเพื่อการท่องเที่ยว|Korean for Travel|3
90644065|ภาษาเวียดนามเพื่อการท่องเที่ยว|Vietnamese for Travel|3
90644066|ภาษามาเลย์เพื่อการท่องเที่ยว|Malay for Travel|3
90644067|สนทนาภาษาจีนเพื่อไอที|Chinese Conversation for IT|3
90644068|รู้จีนให้ได้เงิน|How to Make Money with Chinese|3
90644069|ภาษาญี่ปุ่นพื้นฐาน|Foundation Japanese|3
90644070|การสื่อสารนวัตกรรม|Innovative Communication|3
90644071|ภาษามือเบื้องต้นเพื่อการสื่อสาร|Introduction to Sign Language for Communication|3
""".strip()

        language_elective_courses = []
        for line in GENED_LANGUAGE_COMMUNICATION_RAW.splitlines():
            code, name_th, name_en, credits = line.split("|")
            language_elective_courses.append(
                Course(code=code, name_th=name_th, name_en=name_en, credits=int(credits))
            )

        # กลุ่มวิชาเลือกหมวดวิชาศึกษาทั่วไป — หมวดย่อย "กลุ่มทักษะบุคคลและส่งเสริมวิชาชีพ"
        GENED_PERSONAL_PROFESSIONAL_RAW = """
90642001|ปฏิบัติงานตามทักษะด้านบุคคลและสนับสนุนวิชาชีพ 1|Practice under Personal and Professional Skills 1|1
90642002|ปฏิบัติงานตามทักษะด้านบุคคลและสนับสนุนวิชาชีพ 2|Practice under Personal and Professional Skills 2|2
90642003|ปฏิบัติงานตามทักษะด้านบุคคลและสนับสนุนวิชาชีพ 3|Practice under Personal and Professional Skills 3|3
90642011|การคิดอย่างมีวิจารณญาณ|Critical Thinking|3
90642012|กระบวนการคิดเชิงออกแบบ|Design Thinking|3
90642013|บูรณาการแห่งการคิด|Integrated Thinking|3
90642014|การคิดเชิงระบบและเชิงนวัตกรรม|Innovative and System Thinking|3
90642015|การคิดสร้างสรรค์และนวัตกรรม|Creative Thinking and Innovation|3
90642017|แกะกล่องนวัตกรรม|Innovation Unboxed|3
90642018|เทคโนโลยีการผลิตงานสร้างสรรค์|Creative Production Technology|3
90642019|การออกแบบสะเต็มอย่างสร้างสรรค์ขั้นพื้นฐาน|Basic Creative STEM Design|3
90642020|การออกแบบสะเต็มอย่างสร้างสรรค์ขั้นสูง|Advance Creative STEM Design|3
90642021|ไอเดียขยะ|Junk Design|3
90642022|ปรัชญาวิทยาศาสตร์|Philosophy of Science|3
90642024|การวิเคราะห์ข้อมูลทางวิชาชีพและการนำเสนอทางวิชาการ|Professional Information Analysis and Academic Presentation|3
90642025|วิเคราะห์ความจริงจากตัวเลข|Facts Behind Numbers|3
90642026|การพัฒนาทักษะเชิงวิจัย|Research Skill Development|3
90642028|รู้เท่าทันการพนัน|Gambling Literacy|3
90642029|จริยธรรมและกฎหมายว่าด้วยความเป็นมืออาชีพทางการแพทย์|Medical Ethics, Laws and Professionalism|3
90642030|จรรยาบรรณและกฎหมายวิศวกรรม|Engineering Ethics and Law|3
90642031|จริยธรรมและกฎหมายแห่งวิชาชีพ|Professional Ethics and Laws|3
90642032|กฎหมายสำหรับผู้ประกอบการ|Law for Entrepreneurs|3
90642033|กฎหมายสำหรับคนรุ่นใหม่|Law for New Generation|3
90642034|กฎหมายและระเบียบในอุตสาหกรรมการบิน|Law and Regulation in Aviation Industry|3
90642035|ประสบการณ์ในอุตสาหกรรมสำหรับวิศวกร|Industrial Experience for Engineers|3
90642037|ประเด็นและทักษะวิชาชีพ|Professional Skills and Issues|3
90642038|ความปลอดภัยในที่ทำงาน|Occupational Safety and Health|3
90642039|ซ่อมได้ภายในบ้าน|Quick-Fix @ Home|3
90642040|คอกาแฟ|Coffee Mania|3
90642041|ครัวเด็กหอ|Dorm Chef|3
90642042|ศาสตร์และศิลป์ของเนื้อสัตว์|Science and Art of Meats|3
90642043|ศาสตร์ของเบอร์เกอร์|Science of Burger|3
90642044|โลกของไส้กรอก|World of Sausages|3
90642045|เรื่องเหล้า|Be My Bev.|3
90642046|ไรซ์-สาระ|Rice-Sara|3
90642047|หมอต้นไม้|Tree Doctor|3
90642048|ยาและสมุนไพรพาเพลิน|Fun with Drugs and Herbs|3
90642049|การใช้ประโยชน์จากจุลินทรีย์ในชีวิตประจำวัน|Microbial Utilization for Daily Life|3
90642050|พืชพรรณที่เป็นยา|Medicinal Plants|3
90642051|เทคโนโลยีชีวภาพเพื่อความเป็นอยู่ที่ดีขึ้น|Biotechnology for Better Living|3
90642052|จากเส้นสาย DNA สู่พันธุกรรม|Genes and Genetics: From Helix to Hereditary|3
90642053|สาระน่ารู้อณูพันธุศาสตร์|Interesting Molecular Genetics|3
90642054|สิ่งพิทักษ์ร่างกาย|Guardians of Our Bodies|3
90642055|จุลินทรีย์ร่วมชีพ|Living with Microbes|3
90642056|โรคระบาดในศตวรรษที่ 21|Epidemics in the 21st Century|3
90642057|ภูมิคุ้มกาย|Immunity Through Media|3
90642058|ความเข้าใจในนโยบายสุขภาพและสวัสดิภาพของประชาชน|Understanding Health Policy and Public Welfare|3
90642059|การแพทย์และวรรณกรรม|Medicine and Literature|3
90642060|ค้นหาตัวตน|Self-Discovery|3
90642061|โลกของแมลง|World of Insects|3
90642062|เรื่องกินเรื่องใหญ่|All About Food|3
90642063|การพัฒนาสุขภาพแบบองค์รวม|Holistic Health Development|3
90642074|อีสปอร์ต|E-Sports|3
90642080|การประพันธ์เพลงเบื้องต้น|Introduction to Music Composition|3
90642081|สุนทรียะเพลงแรป|Rap Appreciation|3
90642082|สุนทรียะดนตรี|Music Appreciation|3
90642083|ศิลปะแห่งภาพยนตร์|Film Appreciation|3
90642084|สุนทรียะภาพถ่าย|Photography Appreciation|3
90642085|วัฒนธรรมร่วมสมัย|Contemporary Culture|3
90642086|วัฒนธรรมการออกแบบเบื้องต้น|Introduction to Design Culture|3
90642087|วัฒนธรรมรอบโลก|World Culture|3
90642088|วัฒนธรรมจีนดั้งเดิม|Traditional Chinese Culture|3
90642089|สังคม เศรษฐกิจ และการเมืองจีน|Chinese Society, Economy and Politics|3
90642090|เจาะลึกประเด็นโลก|Global Inside|3
90642091|เอเชียนศึกษา|Asian Study|3
90642092|การศึกษาเพื่อสร้างพลเมือง|Civic Education|3
90642093|สานสัมพันธ์กับชุมชน|Community Engagement|3
90642094|หลักการพัฒนาชุมชน|Principles of Community Development|3
90642095|การพัฒนาความมั่นคงแห่งชาติ|National Security Development|3
90642096|วิทยาการทางทหาร|Military Science|3
90642097|ภูมิปัญญาไทยประยุกต์|Applied Thai Wisdoms|3
90642098|พลวัตสังคมไทย|Dynamics of Thai Society|3
90642099|สังคมสูงวัยเชิงรุก|Active Aging Society|3
90642101|นักรีวิว|Reviewer|3
90642102|นักสื่อสารผ่านยูทูบ|YouTuber|3
90642103|การดำรงชีพในสังคมดิจิทัล|Living in Digital Society|3
90642106|เล่าเรื่องการเดินทางแบบดิจิทัล|Digital Storytelling in Journey|3
90642107|การผลิตสื่อดิจิทัล|Digital Media Production|3
90642108|เทคโนโลยีการถ่ายภาพดิจิทัล|Digital Photography Technology|3
90642109|การออกแบบอินโฟกราฟิก|Infographic Design|3
90642110|สนุกกับวิทยาศาสตร์ข้อมูล|Fun with Data Science|3
90642111|สนุกกับการเขียนโค้ด|Fun with Coding|3
90642112|สนุกกับปัญญาประดิษฐ์|Fun with AI|3
90642113|หุ่นยนต์และปัญญาประดิษฐ์|Robotics and AI|3
90642114|ฟาร์มอัจฉริยะ|Smart Farming|3
90642115|เทคโนโลยีสีเขียวและพลังงานทดแทน|Green Technology and Alternative Energy|3
90642116|เมืองอัจฉริยะและนวัตกรรมเมือง|Smart City and City Innovation|3
90642117|ทักษะการรู้สารสนเทศแห่งศตวรรษที่ 21|Information Literacy Skills for the 21st Century|3
90642120|เอ็กเซลเพื่อความเป็นมืออาชีพ|From Excel to Excellent|3
90642121|การวิเคราะห์และจัดการข้อมูลด้วยโปรแกรมคอมพิวเตอร์|Data Analysis and Management with Computational Program|3
90642122|การใช้แอปพลิเคชัน ไมโครคอมพิวเตอร์|Introduction to Microcomputer Application|3
90642123|เทคโนโลยีคอมพิวเตอร์ดนตรี|Technology in Musical Sequencing|3
90642124|เทคโนโลยีและนวัตกรรมทางวิทยาศาสตร์สำหรับ SDGs|Science Technology and Science Innovation for SDGs|3
90642125|การดำรงชีพท่ามกลางภัยพิบัติและวิกฤติในอนาคต|Living in Future Disaster and Crisis|3
90642126|วิชาเอาตัวรอด|Survivors|3
90642127|รักษ์โลก|Think Earth|3
90642128|นิเวศวิทยาและการรักษาสิ่งแวดล้อม|Ecology, Conservation and Environmentalism|3
90642129|การท่องเที่ยวทางเลือก|Alternative Tourism|3
90642130|การท่องเที่ยวเชิงกีฬา|Sports Tourism|3
90642131|วัฒนธรรมไทยกับการท่องเที่ยว|Thai Culture and Tourism|3
90642132|ชุมพรศึกษาเพื่อการท่องเที่ยว|Chumphon Study for Tourism|3
90642133|รอบรั้วชุมพรศึกษา|Chumphon Area Study|3
90642134|แผ่นดินพระจอมเกล้าฯ ศึกษา|King Mongkut's Reign Study|3
90642135|ปรัชญาเศรษฐกิจพอเพียง|Philosophy of Sufficiency Economy|3
90642136|จริยศาสตร์และสุนทรียศาสตร์|Ethics and Aesthetics|3
90642137|ดูละครแล้วย้อนดูตัว|Series in Daily Life|3
90642138|สมาธิเพื่อพัฒนาชีวิต|Meditation for Life Development|3
90642140|ภูมิคุ้มกันทางใจ|Immunity of Mind|3
90642142|จิตวิทยาสำหรับการสื่อสาร|Psychology in Communication|3
90642143|ชีวิตออกแบบได้|Designing Your Life|3
90642144|กระจกสองใจ|Magic Mirror|3
90642145|พลังแห่งบุคลิกภาพ|Power of Personality|3
90642146|เปลี่ยนความคิด ชีวิตเปลี่ยน|Power of Change|3
90642147|ทักษะแห่งความสุข|Happiness Skills|3
90642148|ศิลปะการพัฒนาอารมณ์|Arts of Emotion Development|3
90642149|ศิลปะสร้างสรรค์เพื่อพัฒนาอารมณ์และจิตวิญญาณ|Imaginative Art|3
90642150|ศิลปะในชีวิตประจำวัน|Art in Everyday Life|3
90642151|มนุษย์กับศิลปะ|Man and Art|3
90642152|ปันสุข|Joy of Sharing|3
90642153|ความเข้าใจในพฤติกรรมมนุษย์|Understanding Human Behavior|3
90642154|ล้มให้เป็น|Fail-able|3
90642156|ฮวงจุ้ย|Feng Shui|3
90642157|โหราศาสตร์ไทย|Thai Astrology|3
90642158|มุมมองวิทยาศาสตร์และเทคโนโลยีร่วมสมัย|Contemporary Science and Technology|3
90642159|จิตวิทยาเบื้องต้น|Introduction to Psychology|3
90642160|การเตรียมความพร้อมสหกิจศึกษา|Cooperative Education Preparation|3
90642161|ดนตรีอิเล็กทรอนิกส์|Electronic Music History|3
90642162|พร้อมสู่วัยทำงาน|Ready to Work|3
90642163|โดดเด่นด้วยจุดแข็ง|Stand Out with Strengths|3
90642164|กฎหมายทรัพย์สินทางปัญญาสำหรับผู้ประกอบการ|Intellectual Property Laws for Entrepreneur|3
90642167|จังหวะชีวิต|Slice of Life|3
90642168|เรื่องน่ารู้ของพืชสมุนไพรเพื่อสุขภาพและความงาม|Interesting Topics in Medicinal Plants for Wellness and Aesthetics|3
90642169|กัญชาเพื่อชีวิต|Cannabis for Life|3
90642170|ตรรกศาสตร์เบื้องต้น|Introduction to Logic|3
90642175|เปตอง|Petanque|3
90642176|รักบี้ฟุตบอล|Rugby Football|3
90642177|ฟุตบอล|Soccer|3
90642178|ซอฟต์บอลและเบสบอล|Softball and Baseball|3
90642179|เทนนิส|Tennis|3
90642180|วอลเลย์บอล|Volleyball|3
90642181|กอล์ฟ|Golf|3
90642182|แบดมินตัน|Badminton|3
90642183|บาสเกตบอล|Basketball|3
90642184|หมากกระดาน|Chess|3
90642185|คาราเต้|Karate|3
90642186|ยิงปืน|Shooting|3
90642187|เทเบิลเทนนิส|Table Tennis|3
90642188|เทควันโด|Taekwondo|3
90642189|ยูโด|Judo|3
90642190|วิธีการออกแบบเพื่อสร้างนวัตกรรม|Design Methods for Innovation|3
90642191|การตีความและการใช้เหตุและผล|Interpretation and Argument|3
90642192|ฟันดาบสากล|Fencing|3
90642193|ฟุตซอล|Futsal|3
90642194|ลีลาศ|Dancesport|3
90642195|บริดจ์|Bridge|3
90642196|ผู้ฝึกสอนการออกกำลังกายส่วนบุคคล|Personal Trainer|3
90642197|การดำน้ำเพื่อการท่องเที่ยวเชิงอนุรักษ์|Diving for Ecotourism|3
90642198|ขับร้องประสานเสียง|Chorus|3
90642199|บูรณาการงานสร้างสรรค์ทางศิลปะและการออกแบบ|Integrated Creative Art and Design|3
90642200|ดาราโหราศาสตร์|Astrology|3
""".strip()

        gened_general_courses = []
        for line in GENED_PERSONAL_PROFESSIONAL_RAW.splitlines():
            code, name_th, name_en, credits = line.split("|")
            gened_general_courses.append(
                Course(code=code, name_th=name_th, name_en=name_en, credits=int(credits))
            )

        # หมวดย่อย "กลุ่มทักษะการจัดการและภาวะความเป็นผู้นำ"
        GENED_MANAGEMENT_LEADERSHIP_RAW = """
90643001|ปฏิบัติงานตามทักษะด้านการจัดการ 1|Practice under Management Skills 1|1
90643002|ปฏิบัติงานตามทักษะด้านการจัดการ 2|Practice under Management Skills 2|2
90643003|ปฏิบัติงานตามทักษะด้านการจัดการ 3|Practice under Management Skills 3|3
90643004|ผู้นำพลังบวก|Positive Power Leader|3
90643005|นักเปลี่ยนโลก|The Disruptor|3
90643006|การจัดการและผู้นำสมัยใหม่|Modern Management and Leadership|3
90643007|ภาวะผู้นำสำหรับคนรุ่นใหม่|Next Gen Leadership|3
90643008|ศาสตร์การต่อรอง|Science of Negotiation|3
90643010|การตลาดร่วมสมัย|Contemporary Marketing|3
90643012|การทำงานเป็นทีม|Teamwork|3
90643013|การจัดการเชิงอุตสาหกรรม|Industrial Management|3
90643014|ความรู้ทั่วไปเกี่ยวกับธุรกิจ|General Business|3
90643015|การบัญชีทางธุรกิจสำหรับคนรุ่นใหม่|Business Accounting for New Gen|3
90643016|สนุกกับธุรกิจออนไลน์|Fun with Online Business|3
90643018|ธุรกิจระหว่างประเทศ|International Business|3
90643019|เศรษฐศาสตร์กับการเป็นผู้ประกอบการ|Economics and Entrepreneurship|3
90643020|นักพัฒนาธุรกิจสร้างสรรค์|Innovative Entrepreneurs|3
90643021|ผู้ประกอบการสมัยใหม่|Modern Entrepreneurs|3
90643022|ผู้ประกอบการทางสังคม|Social Entrepreneurs|3
90643023|ผู้ประกอบการเทคโนโลยี|Technopreneurs|3
90643024|ฟาร์มสุข|Happiness Farms|3
90643025|เส้นทางสู่ IPO|Road to IPO|3
90643026|การวางแผนเพื่อการลงทุน|Investment Planning|3
90643027|มนุษย์ เงิน และคณิตศาสตร์|Man, Money and Math|3
90643028|มือใหม่ (หัด) เล่นหุ้น|Smart Tips for Beginning Investors|3
90643029|เศรษฐกิจดิจิทัล|Digital Economy|3
90643030|เศรษฐศาสตร์ทั่วไป และการศึกษาความเป็นไปได้ของโครงการ|General Economics and Project Feasibility Study|3
90643031|วิถีชีวิตตามแนวคิดเศรษฐกิจหมุนเวียนในศตวรรษที่ 21|Circular Economic Lifestyle for 21st Century|3
90643032|ปักหมุดเศรษฐกิจ|BCG Economy in Action|3
90643034|การจัดการกับความคิดสร้างสรรค์|Management and Creativity|3
90643035|การจัดการความรู้เพื่อการพัฒนานวัตกรรม|Knowledge Management for Innovation Development|3
90643036|การจัดการความรู้เพื่อการบริหารโครงการ|Knowledge Management for Project Management|3
90643037|การบริหารงานภาครัฐและนโยบายสาธารณะในศตวรรษที่ 21|Public Administration and Public Policy in the 21st Century|3
90643038|ศัลยกรรมชีวิต|Rebranding|3
90643039|นวัตกรรม สจล.|KMITL Innovation|3
90643040|ผู้นำในฐานะโคช|Leadership as a Coach|3
90643041|ธรรมาภิบาลสากล|Global Governance|3
90643042|ฮาร์ดเพาเวอร์และซอฟท์เพาเวอร์|Hard Power and Soft Power|3
90643043|ธุรกิจดนตรี|Music Business|3
90643044|ลีนสตาร์ทอัพและแนวคิดธุรกิจแบบคล่องตัว|Lean Startup and Agile Business|3
90643045|การจัดการนวัตกรรม|Innovation Management|3
""".strip()
        for line in GENED_MANAGEMENT_LEADERSHIP_RAW.splitlines():
            code, name_th, name_en, credits = line.split("|")
            gened_general_courses.append(
                Course(code=code, name_th=name_th, name_en=name_en, credits=int(credits))
            )

        session.add_all(
            identity_courses + gened_extra_courses + language_elective_courses + gened_general_courses
        )
        session.flush()

        # ===============================================================
        # 2) หลักสูตร: วท.บ. ฟิสิกส์อุตสาหกรรม / วศ.บ. IoT / วศ.บ. ComIoT (ต่อเนื่อง)
        #    (สร้าง Curriculum, CourseGroup, Course, StudyPlan เหมือนเดิม)
        # ===============================================================

        # --- Physics ---
        physics = Curriculum(
            name="วิทยาศาสตรบัณฑิต สาขาวิชาฟิสิกส์อุตสาหกรรม (หลักสูตรปรับปรุง พ.ศ. 2569)",
            faculty="คณะวิทยาศาสตร์", year=2569, total_credits=122, display_order=3,
        )
        session.add(physics)
        session.flush()

        phy_specific_root = CourseGroup(name="หมวดวิชาเฉพาะ", group_type=GroupType.MAJOR_REQUIRED, curriculum=physics)
        phy_basic = CourseGroup(name="กลุ่มวิชาพื้นฐาน", group_type=GroupType.MAJOR_REQUIRED, parent=phy_specific_root, curriculum=physics)
        phy_required = CourseGroup(name="กลุ่มวิชาบังคับ", group_type=GroupType.MAJOR_REQUIRED, parent=phy_specific_root, curriculum=physics)
        phy_elective = CourseGroup(name="กลุ่มวิชาเลือก", group_type=GroupType.MAJOR_ELECTIVE, parent=phy_specific_root, curriculum=physics)
        phy_guided = CourseGroup(name="กลุ่มวิชาศึกษาทางเลือก", group_type=GroupType.RESTRICTED_ELECTIVE, parent=phy_specific_root, curriculum=physics)
        phy_free = CourseGroup(name="หมวดวิชาเลือกเสรี", group_type=GroupType.FREE_ELECTIVE, curriculum=physics)
        session.add_all([phy_specific_root, phy_basic, phy_required, phy_elective, phy_guided, phy_free])
        session.flush()

        phy_plan_project = StudyPlan(curriculum=physics, code="PROJECT", name="แผนทำโครงงานพิเศษ")
        phy_plan_coop = StudyPlan(curriculum=physics, code="COOP", name="แผนสหกิจศึกษา")
        phy_plan_overseas = StudyPlan(curriculum=physics, code="OVERSEA_TRAINING", name="แผนฝึกงานต่างประเทศ")
        session.add_all([phy_plan_project, phy_plan_coop, phy_plan_overseas])
        session.flush()

        phy_basic_courses = [
            Course(code="05016201", name_th="แคลคูลัส 1", name_en="Calculus 1", credits=3),
            Course(code="05016202", name_th="แคลคูลัส 2", name_en="Calculus 2", credits=3),
            Course(code="05106030", name_th="เคมีทั่วไป", name_en="General Chemistry", credits=3),
            Course(code="05106042", name_th="ปฏิบัติการเคมีทั่วไป", name_en="General Chemistry Laboratory", credits=1),
            Course(code="05366001", name_th="ฟิสิกส์และการประยุกต์ 1", name_en="Physics and Applications 1", credits=3),
            Course(code="05366005", name_th="ปฏิบัติการฟิสิกส์และการประยุกต์ 1", name_en="Physics and Applications Laboratory 1", credits=1),
            Course(code="05366003", name_th="ฟิสิกส์และการประยุกต์ 2", name_en="Physics and Applications 2", credits=3),
            Course(code="05366006", name_th="ปฏิบัติการฟิสิกส์และการประยุกต์ 2", name_en="Physics and Applications Laboratory 2", credits=1),
        ]

        phy_required_courses = [
            Course(code="05366022", name_th="การเขียนโปรแกรมคอมพิวเตอร์", name_en="Computer Programming", credits=3),
            Course(code="05366121", name_th="ทฤษฎีวงจรไฟฟ้าและอิเล็กทรอนิกส์พื้นฐาน", name_en="Electric Circuit Theory and Basic Electronics", credits=3),
            Course(code="05366024", name_th="ปฏิบัติการอิเล็กทรอนิกส์", name_en="Electronic Laboratory", credits=1),
            Course(code="05366143", name_th="การเขียนแบบวิศวกรรม", name_en="Engineering Drawing", credits=1),
            Course(code="05366038", name_th="สถิติในงานอุตสาหกรรม", name_en="Industrial Statistics", credits=3),
            Course(code="05366020", name_th="คณิตศาสตร์สำหรับนักฟิสิกส์", name_en="Mathematics for Physicists", credits=3),
            Course(code="05366025", name_th="อิเล็กทรอนิกส์ดิจิตอล", name_en="Digital Electronics", credits=3),
            Course(code="05366027", name_th="ปฏิบัติการอิเล็กทรอนิกส์ดิจิตอล", name_en="Digital Electronics Laboratory", credits=1),
            Course(code="05366028", name_th="กลศาสตร์", name_en="Mechanics", credits=3),
            Course(code="05366039", name_th="ปฏิบัติการฟิสิกส์ระดับกลาง 1", name_en="Intermediate Physics Laboratory 1", credits=1),
            Course(code="05366123", name_th="วงจรอิเล็กทรอนิกส์", name_en="Electronic Circuits", credits=3),
            Course(code="05366030", name_th="ฟิสิกส์ยุคใหม่", name_en="Modern Physics", credits=3),
            Course(code="05366033", name_th="คลื่นและทัศนศาสตร์", name_en="Waves and Optics", credits=3),
            Course(code="05366034", name_th="เซ็นเซอร์และทรานสดิวเซอร์", name_en="Sensors and Transducers", credits=3),
            Course(code="05366040", name_th="ปฏิบัติการฟิสิกส์ระดับกลาง 2", name_en="Intermediate Physics Laboratory 2", credits=1),
            Course(code="05366032", name_th="สนามแม่เหล็กไฟฟ้า", name_en="Electromagnetic Field", credits=3),
            Course(code="05366036", name_th="ไมโครคอนโทรลเลอร์และการเชื่อมต่อ", name_en="Microcontroller and Interfacing", credits=3),
            Course(code="05366041", name_th="ปฏิบัติการฟิสิกส์อุตสาหกรรม 1", name_en="Industrial Physics Laboratory 1", credits=1),
            Course(code="05366044", name_th="สิ่งประดิษฐ์สารกึ่งตัวนำ", name_en="Semiconductor Devices", credits=3),
            Course(code="05366031", name_th="ฟิสิกส์เชิงความร้อนและเชิงสถิติ", name_en="Thermal and Statistics Physics", credits=3),
            Course(code="05366045", name_th="วิศวกรรมวัสดุและการประยุกต์ใช้ในอุตสาหกรรม", name_en="Materials Engineering and Industrial Applications", credits=3),
            Course(code="05366029", name_th="กลศาสตร์ควอนตัมและเทคโนโลยีควอนตัม", name_en="Quantum Mechanics and Quantum Technology", credits=3),
            Course(code="05366037", name_th="การวัดและเครื่องมือวัด", name_en="Measurement and Instrumentation", credits=3),
            Course(code="05366042", name_th="ปฏิบัติการฟิสิกส์อุตสาหกรรม 2", name_en="Industrial Physics Laboratory 2", credits=1),
            Course(code="05366080", name_th="สัมมนา", name_en="Seminar", credits=1),
            Course(code="05366090", name_th="ฝึกงาน", name_en="Training", credits=0),
        ]

        phy_elective_courses = [
            Course(code="05356100", name_th="ทรานสดิวเซอร์ในงานอุตสาหกรรม", name_en="Industrial Transducers", credits=3),
            Course(code="05356101", name_th="การวัดคุมเสมือนขั้นสูง", name_en="Advanced Virtual Instrumentation", credits=3),
            Course(code="05356102", name_th="การวัดและทดสอบแบบไม่ทำลาย", name_en="Non-Destructive Measurement and Testing", credits=3),
            Course(code="05356103", name_th="มาตรวิทยา", name_en="Metrology", credits=3),
            Course(code="05356104", name_th="ระบบตรวจสอบชิ้นงานด้วยภาพถ่ายแบบอัตโนมัติ", name_en="Automated Visual Inspection System", credits=3),
            Course(code="05356105", name_th="การโปรแกรมภาษาไพธอนสำหรับการวิเคราะห์ข้อมูล", name_en="Programming in Python for Data Analysis", credits=3),
            Course(code="05356106", name_th="ฟิสิกส์สิ่งแวดล้อม", name_en="Environmental Physics", credits=3),
            Course(code="05356120", name_th="กระบวนการผลิตและการทดสอบอุปกรณ์อิเล็กทรอนิกส์และอุปกรณ์ทางแสง", name_en="Manufacturing and Test of Electronics and Optical Devices", credits=3),
            Course(code="05356121", name_th="การตรวจสอบคุณลักษณะของวัสดุสำหรับอุตสาหกรรม", name_en="Materials Characterization for Industry", credits=3),
            Course(code="05356123", name_th="วัสดุแม่เหล็กและเทคโนโลยี", name_en="Magnetic Materials and Technology", credits=3),
            Course(code="05356124", name_th="วิศวกรรมคุณภาพ", name_en="Quality Engineering", credits=3),
            Course(code="05356125", name_th="ฟิสิกส์เพื่อการสร้างนวัตกรรม", name_en="Physics for Innovation", credits=3),
            Course(code="05356126", name_th="ทรัพย์สินทางปัญญาสำหรับนักฟิสิกส์", name_en="Intellectual Property for Physicists", credits=3),
            Course(code="05356140", name_th="ทฤษฎีของเลเซอร์และการออกแบบ", name_en="Lasers Theory Design and Engineering", credits=3),
            Course(code="05356141", name_th="ระบบการสื่อสารทางแสงและอุปกรณ์ของระบบ", name_en="Optical Communication Systems and Devices", credits=3),
            Course(code="05356150", name_th="หัวข้อพิเศษทางฟิสิกส์อุตสาหกรรม", name_en="Special Topic in Industrial Physics", credits=3),
            Course(code="05356160", name_th="สิ่งประดิษฐ์สารกึ่งตัวนำขั้นสูง", name_en="Advanced Semiconductor Devices", credits=3),
            Course(code="05356161", name_th="เทคโนโลยีกระบวนการสร้างสิ่งประดิษฐ์สารกึ่งตัวนำ", name_en="Semiconductor Devices Processing Technology", credits=3),
            Course(code="05356162", name_th="เทคโนโลยีการวัดสารกึ่งตัวนำ", name_en="Semiconductor Measurement Technology", credits=3),
        ]

        phy_guided_project_courses = [
            Course(code="05366091", name_th="โครงงานพิเศษ 1", name_en="Special Project 1", credits=3),
            Course(code="05366092", name_th="โครงงานพิเศษ 2", name_en="Special Project 2", credits=3),
        ]
        phy_guided_coop_courses = [
            Course(code="05366093", name_th="สหกิจศึกษา", name_en="Co-operative Education", credits=6),
            Course(code="05366094", name_th="การฝึกงานต่างประเทศ", name_en="Overseas Training", credits=6),
        ]

        session.add_all(
            phy_basic_courses + phy_required_courses + phy_elective_courses
            + phy_guided_project_courses + phy_guided_coop_courses
        )
        session.flush()

        # --- IoT ---
        iot = Curriculum(
            name="วิศวกรรมศาสตรบัณฑิต สาขาวิชาวิศวกรรมระบบไอโอทีและสารสนเทศ (หลักสูตรปรับปรุง พ.ศ. 2569)",
            faculty="คณะวิศวกรรมศาสตร์", year=2569, total_credits=138, display_order=1,
        )
        session.add(iot)
        session.flush()

        iot_specific_root = CourseGroup(name="หมวดวิชาเฉพาะ", group_type=GroupType.MAJOR_REQUIRED, curriculum=iot)
        iot_basic_math = CourseGroup(name="กลุ่มวิชาพื้นฐานคณิตศาสตร์และวิทยาศาสตร์", group_type=GroupType.MAJOR_REQUIRED, parent=iot_specific_root, curriculum=iot)
        iot_basic_eng = CourseGroup(name="กลุ่มวิชาพื้นฐานทางวิศวกรรม", group_type=GroupType.MAJOR_REQUIRED, parent=iot_specific_root, curriculum=iot)
        iot_required = CourseGroup(name="กลุ่มวิชาบังคับ", group_type=GroupType.MAJOR_REQUIRED, parent=iot_specific_root, curriculum=iot)
        iot_restricted = CourseGroup(name="กลุ่มวิชาบังคับเลือก", group_type=GroupType.RESTRICTED_ELECTIVE, parent=iot_specific_root, curriculum=iot)
        iot_major_elective = CourseGroup(name="กลุ่มวิชาเลือกเฉพาะสาขา", group_type=GroupType.MAJOR_ELECTIVE, parent=iot_specific_root, curriculum=iot)
        iot_guided = CourseGroup(name="กลุ่มวิชาศึกษาทางเลือก", group_type=GroupType.RESTRICTED_ELECTIVE, parent=iot_specific_root, curriculum=iot)
        iot_free = CourseGroup(name="หมวดวิชาเลือกเสรี", group_type=GroupType.FREE_ELECTIVE, curriculum=iot)
        session.add_all([iot_specific_root, iot_basic_math, iot_basic_eng, iot_required, iot_restricted, iot_major_elective, iot_guided, iot_free])
        session.flush()

        iot_plan_project = StudyPlan(curriculum=iot, code="PROJECT", name="แผนทำโครงงานพิเศษ")
        iot_plan_coop = StudyPlan(curriculum=iot, code="COOP", name="แผนสหกิจศึกษา")
        iot_plan_overseas = StudyPlan(curriculum=iot, code="OVERSEA_TRAINING", name="แผนฝึกงานต่างประเทศ")
        session.add_all([iot_plan_project, iot_plan_coop, iot_plan_overseas])
        session.flush()

        iot_basic_math_courses = [
            Course(code="01006030", name_th="แคลคูลัส 1", name_en="Calculus 1", credits=3),
            Course(code="01006020", name_th="ฟิสิกส์ทั่วไป 1", name_en="General Physics 1", credits=3),
            Course(code="01006021", name_th="ปฏิบัติการฟิสิกส์ทั่วไป 1", name_en="General Physics Laboratory 1", credits=1),
            Course(code="01006031", name_th="แคลคูลัส 2", name_en="Calculus 2", credits=3),
            Course(code="01006022", name_th="ฟิสิกส์ทั่วไป 2", name_en="General Physics 2", credits=3),
            Course(code="01006023", name_th="ปฏิบัติการฟิสิกส์ทั่วไป 2", name_en="General Physics Laboratory 2", credits=1),
            Course(code="01236601", name_th="ความน่าจะเป็นและสถิติ", name_en="Probability and Statistics", credits=3),
            Course(code="01236602", name_th="คณิตศาสตร์ดิสครีต", name_en="Discrete Mathematics", credits=3),
            Course(code="01236600", name_th="พีชคณิตเชิงเส้นและสมการเชิงอนุพันธ์", name_en="Linear Algebra and Differential Equations", credits=3),
        ]

        iot_basic_eng_courses = [
            Course(code="01006012", name_th="การเขียนโปรแกรมคอมพิวเตอร์", name_en="Computer Programming", credits=3),
            Course(code="01236604", name_th="วงจรไฟฟ้าและอิเล็กทรอนิกส์", name_en="Circuits and Electronics", credits=3),
            Course(code="01236605", name_th="ปฏิบัติการวงจรไฟฟ้าและอิเล็กทรอนิกส์", name_en="Circuits and Electronics Laboratory", credits=1),
            Course(code="01236610", name_th="ปฏิบัติการเขียนแบบสามมิติทางวิศวกรรม", name_en="Engineering 3D Drawing in Practice", credits=1),
            Course(code="01236603", name_th="พื้นฐานการออกแบบระบบดิจิทัล", name_en="Fundamental of Digital System Design", credits=3),
            Course(code="01236609", name_th="ปฏิบัติการออกแบบระบบดิจิทัล", name_en="Digital System Design Laboratory", credits=1),
            Course(code="01236608", name_th="การออกแบบความคิดรวบยอดทางวิศวกรรมไอโอที", name_en="IoT Engineering Capstone Design", credits=1),
            Course(code="01006004", name_th="การฝึกงานอุตสาหกรรม", name_en="Industrial Training", credits=0),
        ]

        iot_required_courses = [
            Course(code="01236611", name_th="พื้นฐานระบบไอโอที", name_en="Introduction to Internet of Things", credits=3),
            Course(code="01236613", name_th="การเขียนโปรแกรมเชิงวัตถุ", name_en="Object-Oriented Programming", credits=3),
            Course(code="01236619", name_th="การออกแบบเชิงปฏิสัมพันธ์", name_en="Interaction Design", credits=3),
            Course(code="01236615", name_th="หลักการระบบการสื่อสาร", name_en="Principle of Communication Systems", credits=3),
            Course(code="01236626", name_th="การวิเคราะห์และออกแบบระบบ", name_en="System Analysis and Design", credits=3),
            Course(code="01236614", name_th="โครงสร้างข้อมูลและอัลกอริทึม", name_en="Data Structure and Algorithm", credits=3),
            Course(code="01236616", name_th="การสื่อสารข้อมูลและเครือข่ายในระบบไอโอที", name_en="Data Communications and IoT Networks", credits=3),
            Course(code="01236618", name_th="การพัฒนาแอปพลิเคชันบนเว็บและโมไบล์", name_en="Web and Mobile Application Development", credits=3),
            Course(code="01236627", name_th="สถาปัตยกรรมคอมพิวเตอร์และระบบปฏิบัติการ", name_en="Computer Architecture and Operating System", credits=3),
            Course(code="01236630", name_th="ระบบฐานข้อมูล", name_en="Database System", credits=3),
            Course(code="01236628", name_th="การดำเนินการระบบคลาวด์เชิงปฏิบัติ", name_en="Cloud Operations in Practices", credits=1),
            Course(code="01236617", name_th="เซ็นเซอร์และระบบไซเบอร์กายภาพ", name_en="Sensors and Cyber Physical System", credits=3),
            Course(code="01236612", name_th="ไมโครคอนโทรลเลอร์และระบบสมองกลฝังตัว", name_en="Microcontroller and Embedded Systems", credits=3),
            Course(code="01236623", name_th="ปฏิบัติการระบบไอโอทีและสารสนเทศ 1", name_en="IoT and Information Engineering Laboratory 1", credits=1),
            Course(code="01236621", name_th="ปัญญาประดิษฐ์ของทุกสรรพสิ่ง", name_en="Artificial Intelligence of Things", credits=3),
            Course(code="01236622", name_th="ระบบความมั่นคงปลอดภัยทางไซเบอร์", name_en="Cyber Security Systems", credits=3),
            Course(code="01236625", name_th="สัมมนากับผู้เชี่ยวชาญ", name_en="Seminar with Professionals", credits=0),
            Course(code="01236629", name_th="ระบบสื่อสารไร้สายสำหรับไอโอที", name_en="Wireless Communication for IoT System", credits=3),
            Course(code="01236624", name_th="ปฏิบัติการระบบไอโอทีและสารสนเทศ 2", name_en="IoT and Information Engineering Laboratory 2", credits=1),
            Course(code="01236620", name_th="พีแอลซีและไอโอทีในอุตสาหกรรม", name_en="PLC and Industrial Internet of Things", credits=3),
        ]

        iot_restricted_courses = [
            Course(code="01236631", name_th="การมองเห็นของเครื่องและการประมวลผลภาพ", name_en="Computer Vision and Image Processing", credits=3),
            Course(code="01236632", name_th="ระบบอัตโนมัติทางอุตสาหกรรม", name_en="Industrial Automation System", credits=3),
            Course(code="01236633", name_th="การวิเคราะห์ข้อมูล", name_en="Data Analytics", credits=3),
            Course(code="01236634", name_th="การเรียนรู้ของเครื่อง", name_en="Machine Learning", credits=3),
            Course(code="01236635", name_th="การออกแบบการเชื่อมโยงเครือข่ายและการปฏิบัติ", name_en="Internetworking Design and Practice", credits=3),
            Course(code="01236636", name_th="การวัดและเครื่องมือวัดในอุตสาหกรรม", name_en="Measurement and Instrumentation", credits=3),
            Course(code="01236637", name_th="เครือข่ายการสื่อสารโทรศัพท์เคลื่อนที่ยุคหน้า", name_en="Next Generation Mobile Communication", credits=3),
            Course(code="01236638", name_th="วิศวกรรมซอฟต์แวร์", name_en="Software Engineering", credits=3),
            Course(code="01236639", name_th="การประมวลผลคลาวด์", name_en="Cloud Computing", credits=3),
            Course(code="01236640", name_th="แพลตฟอร์มดิจิทัลและการจัดการระบบ", name_en="Digital Platforms and System Administration", credits=3),
        ]

        iot_major_elective_courses = [
            Course(code="01236641", name_th="การออกแบบระบบดิจิทัลขั้นสูงสำหรับไอโอที", name_en="Advanced Digital System Design for IoT", credits=3),
            Course(code="01236642", name_th="การประมวลผลสมรรถนะขั้นสูง", name_en="High Performance Computing", credits=3),
            Course(code="01236643", name_th="หุ่นยนต์ในอุตสาหกรรมของทุกสรรพสิ่ง", name_en="Industrial Robotics of Things", credits=3),
            Course(code="01236644", name_th="เทคโนโลยีระบบสกาดาและโรงงานอัจฉริยะ", name_en="SCADA Technologies and Smart Factory", credits=3),
            Course(code="01236645", name_th="ฟาร์มอัจฉริยะ", name_en="Smart Farming", credits=3),
            Course(code="01236646", name_th="การออกแบบระบบไอโอทีและระบบสมองกลฝังตัวขั้นสูง", name_en="Advanced IoT and Embedded System Design", credits=3),
            Course(code="01236647", name_th="เรื่องคัดสรรทางระบบไอโอทีและสารสนเทศ", name_en="Selected Topic in IoT System and Information Engineering", credits=3),
            Course(code="01236648", name_th="เรื่องคัดสรรทางระบบสมองกลฝังตัวขั้นสูง", name_en="Selected Topic in Advanced Embedded System", credits=3),
            Course(code="01236649", name_th="โซล่าร์เซลล์และเทคโนโลยีการจัดการพลังงานในอาคาร", name_en="Solar Cell and Energy Building Management", credits=3),
            Course(code="01236650", name_th="การออกแบบวงจรรวมสำหรับไอโอที", name_en="Integrated Circuit Design for IoT", credits=3),
            Course(code="01236651", name_th="อิเล็กทรอนิกส์ในอุตสาหกรรม", name_en="Industrial Electronics", credits=3),
            Course(code="01236652", name_th="เอไอโอทีระดับเอดจ์และสมองกลอัจฉริยะ", name_en="Edge AIoT and Embedded Intelligence", credits=3),
            Course(code="01236653", name_th="การมองเห็นของเครื่องจักรในอุตสาหกรรมไอโอที", name_en="Industrial Computer Vision in IoT Industry", credits=3),
            Course(code="01236693", name_th="การปฏิสัมพันธ์ระหว่างมนุษย์และคอมพิวเตอร์", name_en="Human Computer Interaction", credits=3),
            Course(code="01236654", name_th="การเรียนรู้เชิงลึก", name_en="Deep Learning", credits=3),
            Course(code="01236655", name_th="การประมวลผลภาพทางการแพทย์", name_en="Medical Image Processing", credits=3),
            Course(code="01236656", name_th="ข้อมูลขนาดใหญ่และวิศวกรรมข้อมูล", name_en="Big Data and Data Engineering", credits=3),
            Course(code="01236657", name_th="การประมวลผลภาษาธรรมชาติ", name_en="Natural Language Processing", credits=3),
            Course(code="01236658", name_th="เรื่องคัดสรรทางปัญญาประดิษฐ์", name_en="Selected Topic in Artificial Intelligence", credits=3),
            Course(code="01236659", name_th="การวิเคราะห์ข้อมูลอนุกรมเวลาในไอโอที", name_en="Time-Series Analysis Data for IoT", credits=3),
            Course(code="01236660", name_th="โมเดลภาษาขนาดใหญ่", name_en="Large Language Model", credits=3),
            Course(code="01236661", name_th="ปฏิสัมพันธ์ระหว่างมนุษย์และเอไอและเอไอที่อธิบายได้", name_en="Human-AI Interaction and Explainable AI", credits=3),
            Course(code="01236667", name_th="ปัญญาประดิษฐ์สำหรับเชิงธุรกิจ", name_en="Artificial Intelligence for Business", credits=3),
            Course(code="01236662", name_th="ผู้เชี่ยวชาญระบบเครือข่ายเชิงปฏิบัติการ", name_en="Professional Practical Networking", credits=3),
            Course(code="01236663", name_th="การรักษาความปลอดภัยในระบบสารสนเทศและเครือข่าย", name_en="Information and Network Security", credits=3),
            Course(code="01236664", name_th="ความปลอดภัยทางไซเบอร์สำหรับไอโอทีในอุตสาหกรรม", name_en="Cyber Security for Industrial IoT", credits=3),
            Course(code="01236665", name_th="การทดสอบและการประกันคุณภาพซอฟต์แวร์", name_en="Software Quality Assurance and Testing", credits=3),
            Course(code="01236666", name_th="การเจาะระบบและการแฮคอย่างมีจริยธรรม", name_en="Penetration Testing and Ethical Hacking", credits=3),
            Course(code="01236668", name_th="เรื่องคัดสรรทางระบบการสื่อสารและเครือข่าย", name_en="Selected Topic in Communication and Networking System", credits=3),
            Course(code="01236669", name_th="วิทยาการเข้ารหัสลับและเทคโนโลยีบล็อกเชน", name_en="Cryptography and Blockchain Technologies", credits=3),
            Course(code="01236694", name_th="การจัดการศูนย์ความมั่นคงไซเบอร์", name_en="Cybersecurity Operations Center Management", credits=3),
            Course(code="01236670", name_th="การพัฒนาแอปพลิเคชันบนเว็บและโมไบล์ขั้นสูง", name_en="Advanced Mobile and Web Development", credits=3),
            Course(code="01236671", name_th="คลาวด์และการพัฒนาดำเนินงาน", name_en="Cloud and DevOps System", credits=3),
            Course(code="01236672", name_th="การออกแบบอินเตอร์เฟสและประสบการณ์ผู้ใช้งาน", name_en="User Experience and User Interface Design", credits=3),
            Course(code="01236673", name_th="การจำลองเทคโนโลยีภาพเสมือนจริงและคู่แฝดดิจิทัล", name_en="Digital Twin and Virtual Simulation", credits=3),
            Course(code="01236674", name_th="เรื่องคัดสรรทางการพัฒนาซอฟต์แวร์", name_en="Selected Topic in Software Development", credits=3),
            Course(code="01236675", name_th="การออกแบบและจัดการศูนย์ข้อมูล", name_en="Data Center Design and Management", credits=3),
            Course(code="01236676", name_th="กฎหมายสำหรับเทคโนโลยีสารสนเทศ", name_en="Law for Information Technology", credits=3),
            Course(code="01236677", name_th="การบริหารโครงการไอโอทีและไอที", name_en="IoT and IT Project Management", credits=3),
            Course(code="01236678", name_th="นิติวิทยาดิจิทัล", name_en="Digital Forensic", credits=3),
            Course(code="01236679", name_th="การศึกษาเชิงบูรณาการกับการทำงานทางวิศวกรรมไอโอทีและสารสนเทศ", name_en="Work Integrated Learning in IoT and Information Engineering", credits=3),
            Course(code="01236680", name_th="วิศวกรรมสตาร์ทอัพ", name_en="Startup Engineering", credits=3),
            Course(code="01236681", name_th="ระบบอาณัติสัญญาณและการบริหารควบคุมและการสื่อสารของรถไฟเบื้องต้น", name_en="Introduction to Railway Signaling, Operation Control and Communication", credits=3),
            Course(code="01236682", name_th="ทรานสดิวเซอร์ในงานอุตสาหกรรม", name_en="Industrial Transducers", credits=3),
            Course(code="01236683", name_th="ระบบตรวจสอบชิ้นงานด้วยภาพถ่ายแบบอัตโนมัติ", name_en="Automated Visual Inspection System", credits=3),
            Course(code="01236684", name_th="การโปรแกรมภาษาไพธอนสำหรับการวิเคราะห์ข้อมูล", name_en="Programming in Python for Data Analysis", credits=3),
            Course(code="01236685", name_th="กระบวนการผลิตและการทดสอบอุปกรณ์อิเล็กทรอนิกส์และอุปกรณ์ทางแสง", name_en="Manufacturing and Test of Electronics and Optical Devices", credits=3),
            Course(code="01236686", name_th="วิศวกรรมคุณภาพ", name_en="Quality Engineering", credits=3),
            Course(code="01236687", name_th="ระบบการสื่อสารทางแสงและอุปกรณ์ของระบบ", name_en="Optical Communication Systems and Devices", credits=3),
            Course(code="01236688", name_th="สิ่งประดิษฐ์สารกึ่งตัวนำขั้นสูง", name_en="Advanced Semiconductor Devices", credits=3),
            Course(code="01236689", name_th="เทคโนโลยีกระบวนการสร้างสิ่งประดิษฐ์สารกึ่งตัวนำ", name_en="Semiconductor Devices Processing Technology", credits=3),
            Course(code="01236690", name_th="เทคโนโลยีการวัดสารกึ่งตัวนำ", name_en="Semiconductor Measurement Technology", credits=3),
            Course(code="01236691", name_th="การวัดและทดสอบแบบไม่ทำลาย", name_en="Non-Destructive Measurement and Testing", credits=3),
            Course(code="01236692", name_th="มาตรวิทยา", name_en="Metrology", credits=3),
        ]

        iot_guided_project_courses = [
            Course(code="01236606", name_th="โครงงานวิศวกรรมไอโอทีและสารสนเทศ 1", name_en="IoT and Information Engineering Project 1", credits=3),
            Course(code="01236607", name_th="โครงงานวิศวกรรมไอโอทีและสารสนเทศ 2", name_en="IoT and Information Engineering Project 2", credits=3),
        ]
        iot_guided_coop_courses = [
            Course(code="01006029", name_th="สหกิจศึกษา", name_en="Co-operative Education", credits=6),
            Course(code="01006005", name_th="การปฏิบัติการฝึกงานต่างประเทศ", name_en="Oversea Training", credits=6),
        ]

        session.add_all(
            iot_basic_math_courses + iot_basic_eng_courses + iot_required_courses
            + iot_restricted_courses + iot_major_elective_courses
            + iot_guided_project_courses + iot_guided_coop_courses
        )
        session.flush()

        # --- ComIoT ต่อเนื่อง ---
        comiot = Curriculum(
            name="วิศวกรรมศาสตรบัณฑิต สาขาวิชาวิศวกรรมคอมพิวเตอร์และไอโอที (ต่อเนื่อง) (หลักสูตรปรับปรุง พ.ศ. 2569)",
            faculty="คณะวิศวกรรมศาสตร์", year=2569, total_credits=118, display_order=2,
        )
        session.add(comiot)
        session.flush()

        comiot_specific_root = CourseGroup(name="หมวดวิชาเฉพาะ", group_type=GroupType.MAJOR_REQUIRED, curriculum=comiot)
        comiot_basic = CourseGroup(name="กลุ่มวิชาพื้นฐาน", group_type=GroupType.MAJOR_REQUIRED, parent=comiot_specific_root, curriculum=comiot)
        comiot_required = CourseGroup(name="กลุ่มวิชาบังคับ", group_type=GroupType.MAJOR_REQUIRED, parent=comiot_specific_root, curriculum=comiot)
        comiot_major_elective = CourseGroup(name="กลุ่มวิชาเลือกเฉพาะสาขา", group_type=GroupType.MAJOR_ELECTIVE, parent=comiot_specific_root, curriculum=comiot)
        comiot_free = CourseGroup(name="หมวดวิชาเลือกเสรี", group_type=GroupType.FREE_ELECTIVE, curriculum=comiot)
        session.add_all([comiot_specific_root, comiot_basic, comiot_required, comiot_major_elective, comiot_free])
        session.flush()

        course_01006012 = session.query(Course).filter_by(code="01006012").first()

        comiot_basic_courses = [
            Course(code="01446001", name_th="แคลคูลัสสำหรับวิศวกรรมคอมพิวเตอร์", name_en="Calculus for Computer Engineering", credits=3),
            Course(code="01446002", name_th="คณิตศาสตร์วิศวกรรมคอมพิวเตอร์", name_en="Computer Engineering Mathematics", credits=3),
            Course(code="01446003", name_th="สถิติและความน่าจะเป็น", name_en="Probability and Statistics", credits=3),
            course_01006012,
            Course(code="01446004", name_th="การออกแบบระบบดิจิทัล", name_en="Digital System Design", credits=3),
            Course(code="01446005", name_th="วงจรไฟฟ้าและอิเล็กทรอนิกส์", name_en="Circuit and Electronics", credits=3),
            Course(code="01446006", name_th="ปฏิบัติการอิเล็กทรอนิกส์และระบบดิจิทัล", name_en="Electronics and Digital Laboratory", credits=1),
        ]

        comiot_required_courses = [
            Course(code="01446007", name_th="พื้นฐานระบบไอโอที", name_en="Introduction to Internet of Things", credits=3),
            Course(code="01446009", name_th="การเขียนโปรแกรมเชิงวัตถุ", name_en="Object-Oriented Programming", credits=3),
            Course(code="01446025", name_th="หลักการระบบสื่อสาร", name_en="Principle of Communications Systems", credits=3),
            Course(code="01446022", name_th="สถาปัตยกรรมคอมพิวเตอร์และระบบปฏิบัติการ", name_en="Computer Architecture and Operating System", credits=3),
            Course(code="01446015", name_th="การออกแบบเชิงปฏิสัมพันธ์", name_en="Interaction Design", credits=3),
            Course(code="01446024", name_th="การวิเคราะห์และออกแบบระบบ", name_en="System Analysis and Design", credits=3),
            Course(code="01446010", name_th="โครงสร้างข้อมูลและอัลกอริทึม", name_en="Data Structure and Algorithm", credits=3),
            Course(code="01446012", name_th="การสื่อสารข้อมูลและเครือข่ายคอมพิวเตอร์", name_en="Data Communications and Computer Networks", credits=3),
            Course(code="01446008", name_th="ไมโครคอนโทรลเลอร์และระบบสมองกลฝังตัว", name_en="Microcontroller and Embedded Systems", credits=3),
            Course(code="01446020", name_th="ปฏิบัติการทางวิศวกรรมคอมพิวเตอร์และไอโอที 1", name_en="Computer and IoT Engineering Laboratory 1", credits=1),
            Course(code="01446023", name_th="การดำเนินการระบบคลาวด์เชิงปฏิบัติ", name_en="Cloud Operations in Practices", credits=1),
            Course(code="01446019", name_th="เซนเซอร์และระบบไซเบอร์ทางกายภาพ", name_en="Sensor and Cyber-Physical System", credits=3),
            Course(code="01446011", name_th="ระบบฐานข้อมูล", name_en="Database System", credits=3),
            Course(code="01446018", name_th="ระบบความมั่นคงปลอดภัยทางไซเบอร์", name_en="Cyber Security Systems", credits=3),
            Course(code="01446016", name_th="พีแอลซีและระบบไอโอทีในอุตสาหกรรม", name_en="PLC and Industrial Internet of Things", credits=3),
            Course(code="01446014", name_th="การพัฒนาแอปพลิเคชันบนเว็บและโมไบล์", name_en="Web and Mobile Application Development", credits=3),
            Course(code="01446021", name_th="ปฏิบัติการทางวิศวกรรมคอมพิวเตอร์และไอโอที 2", name_en="Computer and IoT Engineering Laboratory 2", credits=1),
            Course(code="01446076", name_th="โครงงาน 1", name_en="Project 1", credits=3),
            Course(code="01446017", name_th="ปัญญาประดิษฐ์ของทุกสรรพสิ่ง", name_en="Artificial Intelligence of Things", credits=3),
            Course(code="01446013", name_th="การออกแบบการเชื่อมโยงเครือข่ายและการปฏิบัติ", name_en="Internetworking Design and Practice", credits=3),
            Course(code="01446077", name_th="โครงงาน 2", name_en="Project 2", credits=3),
        ]

        comiot_elective_courses = [
            Course(code="01446026", name_th="การมองเห็นของเครื่องและการประมวลผลภาพ", name_en="Computer Vision and Image Processing", credits=3),
            Course(code="01446027", name_th="ระบบอัตโนมัติทางอุตสาหกรรม", name_en="Industrial Automation System", credits=3),
            Course(code="01446028", name_th="การวิเคราะห์ข้อมูล", name_en="Data Analytics", credits=3),
            Course(code="01446029", name_th="การเรียนรู้ของเครื่อง", name_en="Machine Learning", credits=3),
            Course(code="01446030", name_th="การวัดและเครื่องมือวัดในอุตสาหกรรม", name_en="Measurement and Instrumentation", credits=3),
            Course(code="01446031", name_th="ระบบสื่อสารไร้สายสำหรับไอโอที", name_en="Wireless Communication for IoT System", credits=3),
            Course(code="01446032", name_th="วิศวกรรมซอฟต์แวร์", name_en="Software Engineering", credits=3),
            Course(code="01446033", name_th="การประมวลผลคลาวด์", name_en="Cloud Computing", credits=3),
            Course(code="01446034", name_th="แพลตฟอร์มดิจิทัลและการจัดการระบบ", name_en="Digital Platforms and System Administration", credits=3),
            Course(code="01446035", name_th="การออกแบบระบบดิจิทัลขั้นสูง", name_en="Advanced Digital System", credits=3),
            Course(code="01446036", name_th="การประมวลผลสมรรถนะขั้นสูง", name_en="High Performance Computing", credits=3),
            Course(code="01446037", name_th="หุ่นยนต์ในอุตสาหกรรม", name_en="Industrial Robotics", credits=3),
            Course(code="01446038", name_th="เทคโนโลยีระบบสกาดาและโรงงานอัจฉริยะ", name_en="SCADA Technologies and Smart Factory", credits=3),
            Course(code="01446039", name_th="ฟาร์มอัจฉริยะ", name_en="Smart Farming", credits=3),
            Course(code="01446040", name_th="การออกแบบระบบไอโอทีและระบบสมองกลฝังตัวขั้นสูง", name_en="Advanced IoT and Embedded System Design", credits=3),
            Course(code="01446041", name_th="เรื่องคัดสรรทางระบบไอโอทีและสารสนเทศ", name_en="Selected Topic in IoT System and Information Engineering", credits=3),
            Course(code="01446042", name_th="เรื่องคัดสรรทางระบบสมองกลฝังตัวขั้นสูง", name_en="Selected Topic in Advanced Embedded System", credits=3),
            Course(code="01446043", name_th="โซล่าร์เซลล์และเทคโนโลยีการจัดการพลังงานในอาคาร", name_en="Solar Cell and Energy Building Management", credits=3),
            Course(code="01446044", name_th="การออกแบบวงจรรวมสำหรับไอโอที", name_en="Integrated Circuit Design for IoT", credits=3),
            Course(code="01446045", name_th="อิเล็กทรอนิกส์ในอุตสาหกรรม", name_en="Industrial Electronics", credits=3),
            Course(code="01446046", name_th="เอไอโอทีระดับเอดจ์และสมองกลอัจฉริยะ", name_en="Edge AIoT and Embedded Intelligence", credits=3),
            Course(code="01446047", name_th="การมองเห็นของเครื่องจักรในอุตสาหกรรมในเชิงปฏิบัติ", name_en="Industrial Computer Vision in Practice", credits=3),
            Course(code="01446048", name_th="การเรียนรู้เชิงลึก", name_en="Deep Learning", credits=3),
            Course(code="01446049", name_th="การประมวลผลภาพทางการแพทย์", name_en="Medical Image Processing", credits=3),
            Course(code="01446050", name_th="ข้อมูลขนาดใหญ่และวิศวกรรมข้อมูล", name_en="Big Data and Data Engineering", credits=3),
            Course(code="01446051", name_th="การประมวลผลภาษาธรรมชาติ", name_en="Natural Language Processing", credits=3),
            Course(code="01446052", name_th="เรื่องคัดสรรทางปัญญาประดิษฐ์", name_en="Selected Topic in Artificial Intelligence", credits=3),
            Course(code="01446053", name_th="เหมืองข้อมูลและการวิเคราะห์อนุกรมเวลา", name_en="Data Mining and Time-Series Analysis", credits=3),
            Course(code="01446054", name_th="โมเดลขนาดใหญ่", name_en="Large Language Model", credits=3),
            Course(code="01446055", name_th="ปฏิสัมพันธ์ระหว่างมนุษย์และเอไอและเอไอที่อธิบายได้", name_en="Human-AI Interaction and Explainable AI", credits=3),
            Course(code="01446056", name_th="ผู้เชี่ยวชาญระบบเครือข่ายเชิงปฏิบัติการ", name_en="Professional Practical Networking", credits=3),
            Course(code="01446057", name_th="การรักษาความปลอดภัยในระบบสารสนเทศและเครือข่าย", name_en="Information and Network Security", credits=3),
            Course(code="01446058", name_th="ความปลอดภัยทางไซเบอร์สำหรับไอโอทีในอุตสาหกรรม", name_en="Cyber Security for Industrial IoT", credits=3),
            Course(code="01446059", name_th="เครือข่ายการสื่อสารโทรศัพท์เคลื่อนที่ยุคหน้า", name_en="Next Generation Mobile Communication", credits=3),
            Course(code="01446060", name_th="การเจาะระบบและการแฮคอย่างมีจริยธรรม", name_en="Penetration Testing and Ethical Hacking", credits=3),
            Course(code="01446061", name_th="ปัญญาประดิษฐ์สำหรับเชิงธุรกิจ", name_en="Artificial Intelligence for Business", credits=3),
            Course(code="01446062", name_th="เรื่องคัดสรรทางระบบการสื่อสารและเครือข่าย", name_en="Selected Topic in Communication and Networking System", credits=3),
            Course(code="01446063", name_th="วิทยาการเข้ารหัสลับและเทคโนโลยีบล็อกเชน", name_en="Cryptography and Blockchain Technologies", credits=3),
            Course(code="01446064", name_th="การพัฒนาแอปพลิเคชันบนเว็บและโมไบล์ขั้นสูง", name_en="Advanced Mobile and Web Development", credits=3),
            Course(code="01446065", name_th="คลาวด์และการพัฒนาดำเนินงาน", name_en="Cloud and DevOps System", credits=3),
            Course(code="01446066", name_th="การออกแบบอินเตอร์เฟสและประสบการณ์ผู้ใช้งาน", name_en="User Experience and Interface Design", credits=3),
            Course(code="01446067", name_th="การจำลองเทคโนโลยีภาพเสมือนจริงและคู่แฝดดิจิทัล", name_en="Digital Twin and Virtual Simulation", credits=3),
            Course(code="01446068", name_th="เรื่องคัดสรรทางการพัฒนาซอฟต์แวร์", name_en="Selected Topic in Software Development", credits=3),
            Course(code="01446069", name_th="การออกแบบและจัดการศูนย์ข้อมูล", name_en="Data Center Design and Management", credits=3),
            Course(code="01446070", name_th="กฎหมายสำหรับเทคโนโลยีสารสนเทศ", name_en="Law for Information Technology", credits=3),
            Course(code="01446071", name_th="การบริหารโครงการระบบไอที", name_en="IT Project Management", credits=3),
            Course(code="01446072", name_th="นิติวิทยาดิจิทัล", name_en="Digital Forensic", credits=3),
            Course(code="01446073", name_th="การศึกษาเชิงบูรณาการกับการทำงานทางวิศวกรรมคอมพิวเตอร์และไอโอที", name_en="Work Integrated Learning in Computer and IoT Engineering", credits=3),
            Course(code="01446074", name_th="วิศวกรรมสตาร์ทอัพ", name_en="Startup Engineering", credits=3),
            Course(code="01446075", name_th="ระบบอาณัติสัญญาณและการบริหารควบคุมและการสื่อสารของรถไฟเบื้องต้น", name_en="Introduction to Railway Signaling, Operation Control and Communication", credits=3),
            Course(code="01006042", name_th="ระบบสิ่งแวดล้อมและความยั่งยืนสำหรับวิศวกร", name_en="Environmental Systems and Sustainability for Engineers", credits=3),
        ]

        session.add_all(
            comiot_basic_courses + comiot_required_courses + comiot_elective_courses
        )
        session.flush()

        # ===============================================================
        # 3) Helper functions สำหรับ link CurriculumCourse
        # ===============================================================

        def link(curriculum, course, group, is_required, year, semester, study_plan=None):
            session.add(
                CurriculumCourse(
                    curriculum_id=curriculum.id,
                    course_code=course.code,
                    group_id=group.id,
                    is_required=is_required,
                    recommended_year=year,
                    recommended_semester=semester,
                    study_plan_id=study_plan.id if study_plan else None,
                )
            )

        # ------------------------------------------------------------------
        # GENED_IDENTITY_DEFAULTS: ค่า default สำหรับ GenEd กลุ่มอัตลักษณ์สถาบันฯ
        #   ใช้เป็น default ของ Physics & IoT
        #   ComIoT ต่อเนื่องใช้ override เฉพาะวิชาที่ต่างจาก default
        # ------------------------------------------------------------------
        # structure: {course_code: (year, semester, is_required, group)}
        # NOTE: 90642036 กับ 90642118 อยู่คนละกลุ่ม จึงต้องระบุ group ต่อรายวิชา
        GENED_IDENTITY_DEFAULTS = {
            # กลุ่มอัตลักษณ์สถาบันฯ (gened_identity)
            "90641008": (1, 1, True, gened_identity),
            "90641007": (1, 2, True, gened_identity),
            "90641004": (1, 2, True, gened_identity),
            "90641009": (2, 1, True, gened_identity),
            "90641005": (2, 2, True, gened_identity),
            "90641010": (3, 2, True, gened_identity),
            "90641006": (3, 2, True, gened_identity),
            "90642036": (1, 1, True, gened_identity),
            # กลุ่มเลือก GenEd (gened_elective)
            "90642118": (1, 2, True, gened_elective),
        }

        # ComIoT override: เฉพาะวิชาที่ year/semester/group ต่างจาก default
        COMIOT_GENED_OVERRIDES = {
            "90641007": (1, 1, True, gened_identity),
            "90641010": (2, 2, True, gened_identity),
            "90642036": (1, 2, True, gened_identity),
            "90642118": (1, 1, True, gened_elective),
        }

        # Physics override: 90642036 ไม่บังคับสำหรับหลักสูตรนี้ (ต่างจากหลักสูตรอื่นที่บังคับ)
        #                   90642118 ไม่ใช้ในหลักสูตรนี้เลย (บังคับเฉพาะบางหลักสูตรเท่านั้น) -> None = ข้ามวิชานี้ไปเลย
        PHYSICS_GENED_OVERRIDES = {
            "90642036": (1, 1, False, gened_identity),
            "90642118": None,
        }

        def link_gened_for_curriculum(curriculum, overrides=None):
            """
            ลงทะเบียน GenEd กลุ่มอัตลักษณ์ + วิชาพิเศษให้หลักสูตร
            ใช้ GENED_IDENTITY_DEFAULTS เป็นค่า default
            overrides = {course_code: (year, sem, is_required, group)} สำหรับวิชาที่ต่างจาก default
                        หรือ {course_code: None} เพื่อ "ข้าม" ไม่ผูกวิชานั้นให้หลักสูตรนี้เลย
            """
            if overrides is None:
                overrides = {}
            for code, default in GENED_IDENTITY_DEFAULTS.items():
                override = overrides.get(code, default)
                if override is None:
                    continue  # ข้ามวิชานี้สำหรับหลักสูตรนี้โดยเฉพาะ
                y, s, req, grp = override
                course = session.query(Course).filter_by(code=code).first()
                if course:
                    link(curriculum, course, grp, req, y, s)

        # ===============================================================
        # 4) ลงทะเบียน GenEd สำหรับแต่ละหลักสูตร
        # ===============================================================
        link_gened_for_curriculum(physics, overrides=PHYSICS_GENED_OVERRIDES)
        link_gened_for_curriculum(iot)  # ใช้ default
        # ComIoT ใช้ override
        link_gened_for_curriculum(comiot, overrides=COMIOT_GENED_OVERRIDES)

        # ภาษาและการสื่อสาร + กลุ่มเลือก GenEd — ใช้ร่วมกันทุกหลักสูตร
        for curriculum in (physics, iot, comiot):
            for c in language_elective_courses:
                link(curriculum, c, gened_language, False, 3, 1)
            for c in gened_general_courses:
                link(curriculum, c, gened_elective, False, 4, 1)

        # ===============================================================
        # 5) CurriculumCourse — วิชาเฉพาะของแต่ละหลักสูตร
        # ===============================================================

        # --- Physics ---
        phy_basic_year_sem = [(1, 1)] * 1 + [(1, 2)] * 1 + [(1, 1)] * 4 + [(1, 2)] * 2
        assert len(phy_basic_year_sem) == len(phy_basic_courses)
        for c, (y, s) in zip(phy_basic_courses, phy_basic_year_sem):
            link(physics, c, phy_basic, True, y, s)

        phy_required_year_sem = (
            [(1, 1)] * 4 + [(1, 2)] * 1
            + [(2, 1)] * 6 + [(2, 2)] * 5
            + [(3, 1)] * 5 + [(3, 2)] * 3
            + [(4, 2)] * 1 + [(3, 3)] * 1
        )
        assert len(phy_required_year_sem) == len(phy_required_courses)
        for c, (y, s) in zip(phy_required_courses, phy_required_year_sem):
            link(physics, c, phy_required, True, y, s)

        for c in phy_elective_courses:
            link(physics, c, phy_elective, False, 3, 2)

        link(physics, phy_guided_project_courses[0], phy_guided, True, 4, 1, phy_plan_project)
        link(physics, phy_guided_project_courses[1], phy_guided, True, 4, 2, phy_plan_project)
        link(physics, phy_guided_coop_courses[0], phy_guided, True, 4, 1, phy_plan_coop)
        link(physics, phy_guided_coop_courses[1], phy_guided, True, 4, 1, phy_plan_overseas)

        # --- IoT ---
        iot_basic_math_year_sem = [(1, 1)] * 3 + [(1, 2)] * 4 + [(2, 1)] * 2
        assert len(iot_basic_math_year_sem) == len(iot_basic_math_courses)
        for c, (y, s) in zip(iot_basic_math_courses, iot_basic_math_year_sem):
            link(iot, c, iot_basic_math, True, y, s)

        iot_basic_eng_year_sem = [(1, 1)] * 4 + [(2, 1)] * 2 + [(4, 2)] * 1 + [(3, 3)] * 1
        assert len(iot_basic_eng_year_sem) == len(iot_basic_eng_courses)
        for c, (y, s) in zip(iot_basic_eng_courses, iot_basic_eng_year_sem):
            link(iot, c, iot_basic_eng, True, y, s)

        iot_required_year_sem = (
            [(1, 1)] * 1 + [(1, 2)] * 2
            + [(2, 1)] * 3 + [(2, 2)] * 6
            + [(3, 1)] * 6 + [(3, 2)] * 2
        )
        assert len(iot_required_year_sem) == len(iot_required_courses)
        for c, (y, s) in zip(iot_required_courses, iot_required_year_sem):
            link(iot, c, iot_required, True, y, s)

        for c in iot_restricted_courses:
            link(iot, c, iot_restricted, False, 3, 2)

        for c in iot_major_elective_courses:
            link(iot, c, iot_major_elective, False, 3, 2)

        link(iot, iot_guided_project_courses[0], iot_guided, True, 4, 1, iot_plan_project)
        link(iot, iot_guided_project_courses[1], iot_guided, True, 4, 2, iot_plan_project)
        link(iot, iot_guided_coop_courses[0], iot_guided, True, 4, 1, iot_plan_coop)
        link(iot, iot_guided_coop_courses[1], iot_guided, True, 4, 1, iot_plan_overseas)

        # --- ComIoT ต่อเนื่อง ---
        comiot_basic_year_sem = [(1, 1)] * 1 + [(1, 2)] * 2  + [(1, 1)] * 4 
        assert len(comiot_basic_year_sem) == len(comiot_basic_courses)
        for c, (y, s) in zip(comiot_basic_courses, comiot_basic_year_sem):
            link(comiot, c, comiot_basic, True, y, s)

        comiot_required_year_sem = (
            [(1, 1)] * 1
            + [(1, 2)] * 4
            + [(2, 1)] * 7
            + [(2, 2)] * 5
            + [(3, 1)] * 3
            + [(3, 2)] * 1
        )
        assert len(comiot_required_year_sem) == len(comiot_required_courses)
        for c, (y, s) in zip(comiot_required_courses, comiot_required_year_sem):
            link(comiot, c, comiot_required, True, y, s)

        for c in comiot_elective_courses:
            link(comiot, c, comiot_major_elective, False, 3, 1)

        # ===============================================================
        # 6) CurriculumGroupRequirement — หน่วยกิตขั้นต่ำต่อหมวด
        # ===============================================================
        requirements = [
            (physics, gened_identity, 12), (physics, gened_language, 3), (physics, gened_elective, 9),
            (physics, phy_basic, 18), (physics, phy_required, 59), (physics, phy_elective, 9),
            (physics, phy_guided, 6), (physics, phy_free, 6),
            (iot, gened_identity, 12), (iot, gened_language, 3), (iot, gened_elective, 9),
            (iot, iot_basic_math, 23), (iot, iot_basic_eng, 13), (iot, iot_required, 51),
            (iot, iot_restricted, 6), (iot, iot_major_elective, 9), (iot, iot_guided, 6), (iot, iot_free, 6),
            (comiot, gened_identity, 12), (comiot, gened_language, 3), (comiot, gened_elective, 9),
            (comiot, comiot_basic, 19), (comiot, comiot_required, 57),
            (comiot, comiot_major_elective, 12), (comiot, comiot_free, 6),
        ]
        for curriculum, group, min_credits in requirements:
            session.add(CurriculumGroupRequirement(curriculum_id=curriculum.id, group_id=group.id, min_credits=min_credits))

        # ===============================================================
        # 7) CourseEquivalency — คู่วิชาเทียบเคียงข้ามหลักสูตร
        # ===============================================================
        # Physics ↔ IoT
        equivalency_pairs = [
            ("01006030", "05016201", "แคลคูลัส 1"),
            ("01006020", "05366001", "ฟิสิกส์ทั่วไป 1 / ฟิสิกส์และการประยุกต์ 1"),
            ("01006021", "05366005", "ปฏิบัติการฟิสิกส์ทั่วไป 1 / ปฏิบัติการฟิสิกส์และการประยุกต์ 1"),
            ("01006012", "05366022", "การเขียนโปรแกรมคอมพิวเตอร์"),
            ("01236604", "05366121", "วงจรไฟฟ้าและอิเล็กทรอนิกส์ / ทฤษฎีวงจรไฟฟ้าและอิเล็กทรอนิกส์พื้นฐาน"),
            ("01236605", "05366024", "ปฏิบัติการวงจรไฟฟ้าและอิเล็กทรอนิกส์ / ปฏิบัติการอิเล็กทรอนิกส์"),
            ("01236610", "05366143", "ปฏิบัติการเขียนแบบสามมิติทางวิศวกรรม / การเขียนแบบวิศวกรรม"),
            ("01006031", "05016202", "แคลคูลัส 2"),
            ("01006022", "05366003", "ฟิสิกส์ทั่วไป 2 / ฟิสิกส์และการประยุกต์ 2"),
            ("01006023", "05366006", "ปฏิบัติการฟิสิกส์ทั่วไป 2 / ปฏิบัติการฟิสิกส์และการประยุกต์ 2"),
            ("01236601", "05366038", "ความน่าจะเป็นและสถิติ / สถิติในงานอุตสาหกรรม"),
            ("01236600", "05366020", "พีชคณิตเชิงเส้นและสมการเชิงอนุพันธ์ / คณิตศาสตร์สำหรับนักฟิสิกส์"),
            ("01236603", "05366025", "พื้นฐานการออกแบบระบบดิจิทัล / อิเล็กทรอนิกส์ดิจิตอล"),
            ("01236609", "05366027", "ปฏิบัติการออกแบบระบบดิจิทัล / ปฏิบัติการอิเล็กทรอนิกส์ดิจิตอล"),
            ("01236617", "05366034", "เซ็นเซอร์และระบบไซเบอร์กายภาพ / เซ็นเซอร์และทรานสดิวเซอร์"),
            ("01236612", "05366036", "ไมโครคอนโทรลเลอร์และระบบสมองกลฝังตัว / ไมโครคอนโทรลเลอร์และการเชื่อมต่อ"),
            ("01236623", "05366041", "ปฏิบัติการระบบไอโอทีและสารสนเทศ 1 / ปฏิบัติการฟิสิกส์อุตสาหกรรม 1"),
            ("01236624", "05366042", "ปฏิบัติการระบบไอโอทีและสารสนเทศ 2 / ปฏิบัติการฟิสิกส์อุตสาหกรรม 2"),
            ("01006004", "05366090", "การฝึกงานอุตสาหกรรม / ฝึกงาน"),
            ("01236606", "05366091", "โครงงานวิศวกรรมไอโอทีและสารสนเทศ 1 / โครงงานพิเศษ 1"),
            ("01236607", "05366092", "โครงงานวิศวกรรมไอโอทีและสารสนเทศ 2 / โครงงานพิเศษ 2"),
            ("01006029", "05366093", "สหกิจศึกษา"),
            ("01006005", "05366094", "การปฏิบัติการฝึกงานต่างประเทศ / การฝึกงานต่างประเทศ"),
            # วิชาเปิดร่วม IoT ↔ Physics
            ("01236682", "05356100", "ทรานสดิวเซอร์ในงานอุตสาหกรรม"),
            ("01236683", "05356104", "ระบบตรวจสอบชิ้นงานด้วยภาพถ่ายแบบอัตโนมัติ"),
            ("01236684", "05356105", "การโปรแกรมภาษาไพธอนสำหรับการวิเคราะห์ข้อมูล"),
            ("01236685", "05356120", "กระบวนการผลิตและการทดสอบอุปกรณ์อิเล็กทรอนิกส์และอุปกรณ์ทางแสง"),
            ("01236686", "05356124", "วิศวกรรมคุณภาพ"),
            ("01236687", "05356141", "ระบบการสื่อสารทางแสงและอุปกรณ์ของระบบ"),
            ("01236688", "05356160", "สิ่งประดิษฐ์สารกึ่งตัวนำขั้นสูง"),
            ("01236689", "05356161", "เทคโนโลยีกระบวนการสร้างสิ่งประดิษฐ์สารกึ่งตัวนำ"),
            ("01236690", "05356162", "เทคโนโลยีการวัดสารกึ่งตัวนำ"),
            ("01236691", "05356102", "การวัดและทดสอบแบบไม่ทำลาย"),
            ("01236692", "05356103", "มาตรวิทยา"),
        ]

        session.add_all([
            CourseEquivalency(
                course_code_a=a, course_code_b=b, equivalence_type=EquivalenceType.FULL,
                note=f"เทียบเคียงตามแผนการศึกษาของทั้งสองหลักสูตร ({desc})",
            )
            for a, b, desc in equivalency_pairs
        ])

        # ComIoT ต่อเนื่อง ↔ IoT หลัก
        comiot_equivalency_pairs = [
            ("01446001", "01006030", "แคลคูลัสสำหรับวิศวกรรมคอมพิวเตอร์ ~ แคลคูลัส 1"),
            ("01446003", "01236601", "สถิติและความน่าจะเป็น ~ ความน่าจะเป็นและสถิติ"),
            ("01446004", "01236603", "การออกแบบระบบดิจิทัล ~ พื้นฐานการออกแบบระบบดิจิทัล"),
            ("01446005", "01236604", "วงจรไฟฟ้าและอิเล็กทรอนิกส์"),
            ("01446006", "01236605", "ปฏิบัติการอิเล็กทรอนิกส์และระบบดิจิทัล ~ ปฏิบัติการวงจรไฟฟ้าและอิเล็กทรอนิกส์"),
            ("01446007", "01236611", "พื้นฐานระบบไอโอที"),
            ("01446008", "01236612", "ไมโครคอนโทรลเลอร์และระบบสมองกลฝังตัว"),
            ("01446009", "01236613", "การเขียนโปรแกรมเชิงวัตถุ"),
            ("01446010", "01236614", "โครงสร้างข้อมูลและอัลกอริทึม"),
            ("01446011", "01236630", "ระบบฐานข้อมูล"),
            ("01446012", "01236616", "การสื่อสารข้อมูลและเครือข่ายคอมพิวเตอร์"),
            ("01446013", "01236635", "การออกแบบการเชื่อมโยงเครือข่ายและการปฏิบัติ"),
            ("01446014", "01236618", "การพัฒนาแอปพลิเคชันบนเว็บและโมไบล์"),
            ("01446015", "01236619", "การออกแบบเชิงปฏิสัมพันธ์"),
            ("01446016", "01236620", "พีแอลซีและระบบไอโอทีในอุตสาหกรรม"),
            ("01446017", "01236621", "ปัญญาประดิษฐ์ของทุกสรรพสิ่ง"),
            ("01446018", "01236622", "ระบบความมั่นคงปลอดภัยทางไซเบอร์"),
            ("01446019", "01236617", "เซนเซอร์และระบบไซเบอร์ทางกายภาพ"),
            ("01446020", "01236623", "ปฏิบัติการทางวิศวกรรมคอมพิวเตอร์และไอโอที 1"),
            ("01446021", "01236624", "ปฏิบัติการทางวิศวกรรมคอมพิวเตอร์และไอโอที 2"),
            ("01446022", "01236627", "สถาปัตยกรรมคอมพิวเตอร์และระบบปฏิบัติการ"),
            ("01446023", "01236628", "การดำเนินการระบบคลาวด์เชิงปฏิบัติ"),
            ("01446024", "01236626", "การวิเคราะห์และออกแบบระบบ"),
            ("01446025", "01236615", "หลักการระบบสื่อสาร"),
            ("01446076", "01236606", "โครงงาน 1 ~ โครงงานวิศวกรรมไอโอทีฯ 1"),
            ("01446077", "01236607", "โครงงาน 2 ~ โครงงานวิศวกรรมไอโอทีฯ 2"),
            ("01446026", "01236631", "การมองเห็นของเครื่องและการประมวลผลภาพ"),
            ("01446027", "01236632", "ระบบอัตโนมัติทางอุตสาหกรรม"),
            ("01446028", "01236633", "การวิเคราะห์ข้อมูล"),
            ("01446029", "01236634", "การเรียนรู้ของเครื่อง"),
            ("01446030", "01236636", "การวัดและเครื่องมือวัดในอุตสาหกรรม"),
            ("01446031", "01236629", "ระบบสื่อสารไร้สายสำหรับไอโอที"),
            ("01446032", "01236638", "วิศวกรรมซอฟต์แวร์"),
            ("01446033", "01236639", "การประมวลผลคลาวด์"),
            ("01446034", "01236640", "แพลตฟอร์มดิจิทัลและการจัดการระบบ"),
            ("01446035", "01236641", "การออกแบบระบบดิจิทัลขั้นสูง"),
            ("01446036", "01236642", "การประมวลผลสมรรถนะขั้นสูง"),
            ("01446037", "01236643", "หุ่นยนต์ในอุตสาหกรรม"),
            ("01446038", "01236644", "เทคโนโลยีระบบสกาดาและโรงงานอัจฉริยะ"),
            ("01446039", "01236645", "ฟาร์มอัจฉริยะ"),
            ("01446040", "01236646", "การออกแบบระบบไอโอทีและสมองกลฝังตัวขั้นสูง"),
            ("01446041", "01236647", "เรื่องคัดสรรทางระบบไอโอทีและสารสนเทศ"),
            ("01446042", "01236648", "เรื่องคัดสรรทางระบบสมองกลฝังตัวขั้นสูง"),
            ("01446043", "01236649", "โซล่าร์เซลล์และเทคโนโลยีการจัดการพลังงานในอาคาร"),
            ("01446044", "01236650", "การออกแบบวงจรรวมสำหรับไอโอที"),
            ("01446045", "01236651", "อิเล็กทรอนิกส์ในอุตสาหกรรม"),
            ("01446046", "01236652", "เอไอโอทีระดับเอดจ์และสมองกลอัจฉริยะ"),
            ("01446047", "01236653", "การมองเห็นของเครื่องจักรในอุตสาหกรรม"),
            ("01446048", "01236654", "การเรียนรู้เชิงลึก"),
            ("01446049", "01236655", "การประมวลผลภาพทางการแพทย์"),
            ("01446050", "01236656", "ข้อมูลขนาดใหญ่และวิศวกรรมข้อมูล"),
            ("01446051", "01236657", "การประมวลผลภาษาธรรมชาติ"),
            ("01446052", "01236658", "เรื่องคัดสรรทางปัญญาประดิษฐ์"),
            ("01446053", "01236659", "เหมืองข้อมูลและการวิเคราะห์อนุกรมเวลา"),
            ("01446054", "01236660", "โมเดลขนาดใหญ่"),
            ("01446055", "01236661", "ปฏิสัมพันธ์ระหว่างมนุษย์และเอไอ"),
            ("01446056", "01236662", "ผู้เชี่ยวชาญระบบเครือข่ายเชิงปฏิบัติการ"),
            ("01446057", "01236663", "การรักษาความปลอดภัยในระบบสารสนเทศและเครือข่าย"),
            ("01446058", "01236664", "ความปลอดภัยทางไซเบอร์สำหรับไอโอทีในอุตสาหกรรม"),
            ("01446059", "01236637", "เครือข่ายการสื่อสารโทรศัพท์เคลื่อนที่ยุคหน้า"),
            ("01446060", "01236666", "การเจาะระบบและการแฮคอย่างมีจริยธรรม"),
            ("01446061", "01236667", "ปัญญาประดิษฐ์สำหรับเชิงธุรกิจ"),
            ("01446062", "01236668", "เรื่องคัดสรรทางระบบการสื่อสารและเครือข่าย"),
            ("01446063", "01236669", "วิทยาการเข้ารหัสลับและเทคโนโลยีบล็อกเชน"),
            ("01446064", "01236670", "การพัฒนาแอปพลิเคชันบนเว็บและโมไบล์ขั้นสูง"),
            ("01446065", "01236671", "คลาวด์และการพัฒนาดำเนินงาน"),
            ("01446066", "01236672", "การออกแบบอินเตอร์เฟสและประสบการณ์ผู้ใช้งาน"),
            ("01446067", "01236673", "การจำลองเทคโนโลยีภาพเสมือนจริงและคู่แฝดดิจิทัล"),
            ("01446068", "01236674", "เรื่องคัดสรรทางการพัฒนาซอฟต์แวร์"),
            ("01446069", "01236675", "การออกแบบและจัดการศูนย์ข้อมูล"),
            ("01446070", "01236676", "กฎหมายสำหรับเทคโนโลยีสารสนเทศ"),
            ("01446071", "01236677", "การบริหารโครงการระบบไอที"),
            ("01446072", "01236678", "นิติวิทยาดิจิทัล"),
            ("01446073", "01236679", "การศึกษาเชิงบูรณาการฯ"),
            ("01446074", "01236680", "วิศวกรรมสตาร์ทอัพ"),
            ("01446075", "01236681", "ระบบอาณัติสัญญาณฯ รถไฟเบื้องต้น"),
        ]

        session.add_all([
            CourseEquivalency(
                course_code_a=a, course_code_b=b, equivalence_type=EquivalenceType.FULL,
                note=f"เทียบเคียงระหว่าง ComIoT ต่อเนื่อง และ IoT หลัก ({desc})",
            )
            for a, b, desc in comiot_equivalency_pairs
        ])

        # -------------------------------------------------------------
        # ElectiveTermSlot — จำนวนช่องวิชาเลือกต่อหมวด ต่อเทอม ของหลักสูตร IoT (ข้อมูลจริงที่ผู้ใช้ยืนยัน)
        # -------------------------------------------------------------
        iot_elective_slots = [
            # (group, year, semester, slot_count, study_plan)
            (gened_language, 3, 1, 1, None),      # วิชาเลือกศึกษาทั่วไปหมวดภาษาและการสื่อสาร
            (iot_restricted, 3, 2, 2, None),      # หมวดวิชาบังคับเลือก
            (gened_elective, 3, 2, 2, None),      # วิชาเลือกหมวดวิชาศึกษาทั่วไป
            (iot_free, 3, 2, 1, None),            # หมวดวิชาเลือกเสรี

            # ปี 4 แผนโครงงาน (PROJECT)
            (iot_major_elective, 4, 1, 2, iot_plan_project),  # หมวดวิชาเลือกเฉพาะสาขา
            (iot_free, 4, 1, 1, iot_plan_project),            # หมวดวิชาเลือกเสรี
            (iot_major_elective, 4, 2, 1, iot_plan_project),  # หมวดวิชาเลือกเฉพาะสาขา

            # ปี 4 แผนสหกิจศึกษา (COOP) — ไม่มีวิชาเลือกในเทอม 1
            (iot_major_elective, 4, 2, 3, iot_plan_coop),     # หมวดวิชาเลือกเฉพาะสาขา
            (iot_free, 4, 2, 1, iot_plan_coop),               # หมวดวิชาเลือกเสรี

            # ปี 4 แผนฝึกงานต่างประเทศ (OVERSEA_TRAINING) — เหมือนแผนสหกิจศึกษาทุกจุด
            (iot_major_elective, 4, 2, 3, iot_plan_overseas),
            (iot_free, 4, 2, 1, iot_plan_overseas),
        ]
        for group, year, semester, slot_count, plan in iot_elective_slots:
            session.add(ElectiveTermSlot(
                curriculum_id=iot.id, group_id=group.id, year=year, semester=semester,
                slot_count=slot_count, study_plan_id=plan.id if plan else None,
            ))

        # -------------------------------------------------------------
        # ElectiveTermSlot — จำนวนช่องวิชาเลือกต่อหมวด ต่อเทอม ของหลักสูตร ComIoT ต่อเนื่อง (ข้อมูลจริงที่ผู้ใช้ยืนยัน)
        # ComIoT ไม่มีแผนทางเลือก (ไม่มี PROJECT/COOP/OVERSEA_TRAINING) จึงใช้ study_plan=None ทุกช่อง
        # -------------------------------------------------------------
        comiot_elective_slots = [
            # (group, year, semester, slot_count)
            (gened_elective, 2, 2, 1),          # วิชาเลือกหมวดวิชาศึกษาทั่วไป
            (comiot_major_elective, 3, 1, 2),   # หมวดวิชาเลือกเฉพาะสาขา
            (comiot_free, 3, 1, 1),             # หมวดวิชาเลือกเสรี
            (gened_language, 3, 1, 1),          # วิชาเลือกศึกษาทั่วไปหมวดภาษาและการสื่อสาร
            (comiot_major_elective, 3, 2, 2),   # หมวดวิชาเลือกเฉพาะสาขา
            (gened_elective, 3, 2, 1),          # วิชาเลือกหมวดวิชาศึกษาทั่วไป
            (comiot_free, 3, 2, 1),             # หมวดวิชาเลือกเสรี
        ]
        for group, year, semester, slot_count in comiot_elective_slots:
            session.add(ElectiveTermSlot(
                curriculum_id=comiot.id, group_id=group.id, year=year, semester=semester,
                slot_count=slot_count, study_plan_id=None,
            ))

        # -------------------------------------------------------------
        # ElectiveTermSlot — จำนวนช่องวิชาเลือกต่อหมวด ต่อเทอม ของหลักสูตรฟิสิกส์อุตสาหกรรม (ข้อมูลจริงที่ผู้ใช้ยืนยัน)
        # ปี 2-3 ใช้ร่วมกันทุกแผน (แผนทางเลือกยังไม่แยกจนถึงปี 4) จึงใช้ study_plan=None ทุกช่อง
        # -------------------------------------------------------------
        phy_elective_slots = [
            # (group, year, semester, slot_count)
            (phy_elective, 2, 2, 1),      # หมวดวิชาเลือก
            (phy_elective, 3, 1, 1),      # หมวดวิชาเลือก
            (phy_elective, 3, 2, 1),      # หมวดวิชาเลือก
            (gened_elective, 3, 1, 2),    # วิชาเลือกหมวดวิชาศึกษาทั่วไป
            (gened_elective, 3, 2, 1),    # วิชาเลือกหมวดวิชาศึกษาทั่วไป
            (phy_free, 3, 1, 1),          # หมวดวิชาเลือกเสรี
            (gened_language, 3, 2, 1),    # วิชาเลือกศึกษาทั่วไปหมวดภาษาและการสื่อสาร
            (phy_free, 3, 2, 1),          # หมวดวิชาเลือกเสรี
        ]
        for group, year, semester, slot_count in phy_elective_slots:
            session.add(ElectiveTermSlot(
                curriculum_id=physics.id, group_id=group.id, year=year, semester=semester,
                slot_count=slot_count, study_plan_id=None,
            ))

        session.commit()
        print("Seed data สำเร็จ:")
        print(f"  - Course ทั้งหมด: {session.query(Course).count()} วิชา")
        print(f"  - CourseGroup ทั้งหมด: {session.query(CourseGroup).count()} กลุ่ม")
        print(f"  - StudyPlan ทั้งหมด: {session.query(StudyPlan).count()} แผน")
        print(f"  - CurriculumCourse ทั้งหมด: {session.query(CurriculumCourse).count()} ความสัมพันธ์")
        print(f"  - CurriculumGroupRequirement ทั้งหมด: {session.query(CurriculumGroupRequirement).count()} เงื่อนไข")
        print(f"  - CourseEquivalency ทั้งหมด: {session.query(CourseEquivalency).count()} คู่วิชา")
        print(f"  - ElectiveTermSlot ทั้งหมด: {session.query(ElectiveTermSlot).count()} ช่อง")

    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    init_db()
    seed()
