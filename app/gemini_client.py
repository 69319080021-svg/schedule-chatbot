import json
import time
from typing import Any, Callable

from google import genai
from google.genai import errors, types

from .config import EXTRACTION_MODEL, GEMINI_API_KEY, QUERY_MODEL

_client: genai.Client | None = None

RETRYABLE_CODES = {429, 503}
MAX_RETRIES = 3


class QuotaExceededError(Exception):
    """โควตาฟรีรายวันของ Gemini API หมด — retry ใหม่ไม่ช่วยเพราะโควตาจะรีเซ็ตทีละวันเท่านั้น"""


def get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else genai.Client()
    return _client


def _with_retries(call: Callable[[], Any]) -> Any:
    for attempt in range(MAX_RETRIES + 1):
        try:
            return call()
        except errors.APIError as e:
            if e.code == 429 and "PerDay" in str(e):
                # โควตารายวันหมด ลองใหม่ในไม่กี่วินาทีไม่มีประโยชน์ ต้องแจ้งผู้ใช้ทันที
                raise QuotaExceededError(str(e)) from e
            if e.code not in RETRYABLE_CODES or attempt == MAX_RETRIES:
                raise
            time.sleep(2**attempt)


SCHEDULE_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "description": "ชื่อ-นามสกุลอาจารย์ พร้อมคำนำหน้า เช่น นางสจี พรหมมาศ"},
        "qualification": {"type": "string", "description": "วุฒิการศึกษา"},
        "department": {"type": "string", "description": "สาขาวิชา"},
        "school": {"type": "string", "description": "สถานศึกษา"},
        "semester": {"type": "string", "description": "ภาคเรียนที่ เช่น 1/2569"},
        "special_duty": {"type": "string", "description": "หน้าที่พิเศษ ถ้าไม่มีให้ใส่ค่าว่าง"},
        "courses": {
            "type": "array",
            "description": "รายวิชาที่ทำการสอนทั้งหมด",
            "items": {
                "type": "object",
                "properties": {
                    "code": {"type": "string"},
                    "name": {"type": "string"},
                    "theory_hours": {"type": "number", "description": "จำนวนชั่วโมงทฤษฎี (ท)"},
                    "practice_hours": {"type": "number", "description": "จำนวนชั่วโมงปฏิบัติ (ป)"},
                    "credits": {"type": "number", "description": "หน่วยกิต (น)"},
                    "total_hours": {"type": "number", "description": "จำนวนชั่วโมงรวม (ช)"},
                },
                "required": ["code", "name", "theory_hours", "practice_hours", "credits", "total_hours"],
                "additionalProperties": False,
            },
        },
        "schedule": {
            "type": "array",
            "description": "ตารางสอนรายสัปดาห์ หนึ่งแถวต่อหนึ่งช่วงเวลาสอน",
            "items": {
                "type": "object",
                "properties": {
                    "day": {"type": "string", "description": "ชื่อวันภาษาไทยแบบเต็ม เช่น จันทร์, อังคาร, พุธ, พฤหัสบดี, ศุกร์"},
                    "start_time": {"type": "string", "description": "เวลาเริ่มสอน รูปแบบ HH:MM (24 ชั่วโมง)"},
                    "end_time": {"type": "string", "description": "เวลาสิ้นสุดสอน รูปแบบ HH:MM (24 ชั่วโมง)"},
                    "periods": {"type": "string", "description": "หมายเลขคาบสอน เช่น 1-4"},
                    "type": {"type": "string", "description": "ประเภทการสอน: ท (ทฤษฎี) หรือ ป (ปฏิบัติ)"},
                    "course_code": {"type": "string"},
                    "course_name": {"type": "string"},
                    "location": {"type": "string", "description": "สถานที่/ห้องเรียน"},
                    "group": {"type": "string", "description": "กลุ่มเรียน เช่น สท.5/1-2"},
                    "student_count": {"type": "number", "description": "จำนวนนักศึกษา ถ้าไม่ระบุให้ใส่ 0"},
                },
                "required": [
                    "day", "start_time", "end_time", "periods", "type",
                    "course_code", "course_name", "location", "group", "student_count",
                ],
                "additionalProperties": False,
            },
        },
    },
    "required": [
        "name", "qualification", "department", "school", "semester",
        "special_duty", "courses", "schedule",
    ],
    "additionalProperties": False,
}

EXTRACTION_PROMPT = (
    "อ่านเอกสารตารางสอนของอาจารย์จากไฟล์ที่แนบมา (อาจเป็นภาพสแกน) "
    "แล้วแปลงข้อมูลทั้งหมดให้อยู่ในรูปแบบ JSON ตาม schema ที่กำหนด โดย:\n"
    "- แปลงเวลาให้เป็นรูปแบบ HH:MM (24 ชั่วโมง) เสมอ\n"
    '- ชื่อวันให้เป็นภาษาไทยแบบเต็ม เช่น "จันทร์", "อังคาร"\n'
    "- ถ้าไม่มีข้อมูลของฟิลด์ไหน ให้ใส่ค่าว่าง หรือ 0 ตามชนิดข้อมูลที่เหมาะสม\n"
    "- ตรวจสอบตัวเลขเวลาและคาบสอนให้ตรงกับต้นฉบับอย่างเคร่งครัด ห้ามเดาหรือแต่งข้อมูลเพิ่มเติมโดยเด็ดขาด"
)


def extract_schedule_from_pdf(pdf_bytes: bytes) -> dict[str, Any]:
    client = get_client()
    response = _with_retries(lambda: client.models.generate_content(
        model=EXTRACTION_MODEL,
        contents=[
            types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
            EXTRACTION_PROMPT,
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_json_schema=SCHEDULE_JSON_SCHEMA,
        ),
    ))
    return json.loads(response.text)


QUERY_SYSTEM_TEMPLATE = (
    "คุณเป็นผู้ช่วยตอบคำถามเกี่ยวกับตารางสอนของอาจารย์ในแผนกเทคโนโลยีสารสนเทศ "
    "วิทยาลัยเทคนิคสัตหีบ\n\n"
    "นี่คือข้อมูลตารางสอนทั้งหมดที่คุณมี (รูปแบบ JSON):\n{data}\n\n"
    "กฎการตอบ:\n"
    "1. ตอบจากข้อมูลข้างต้นเท่านั้น ห้ามเดาหรือสร้างข้อมูลที่ไม่มีในนี้เด็ดขาด\n"
    "2. ถ้าถามถึงอาจารย์ วิชา ห้อง หรือกลุ่มเรียนที่ไม่มีในข้อมูล ให้ตอบตรงๆ ว่าไม่พบข้อมูล\n"
    "3. ผู้ใช้อาจพิมพ์ชื่ออาจารย์ไม่ตรงเป๊ะ (เช่นใช้ชื่อเล่นหรือพิมพ์บางส่วน) "
    "ให้พยายามจับคู่กับชื่อที่ใกล้เคียงที่สุดในข้อมูล ถ้าไม่มั่นใจให้ถามกลับเพื่อยืนยันว่าหมายถึงใคร\n"
    "4. ตอบเป็นภาษาไทย กระชับ ชัดเจน ระบุวัน เวลา คาบ วิชา ห้อง ให้ครบตามที่ถูกถาม\n"
    "5. ถ้าคำถามครอบคลุมหลายอาจารย์ (เช่นถามตามวิชาหรือห้อง) ให้ตอบรวมทุกคนที่เกี่ยวข้อง"
)


MAX_HISTORY_TURNS = 10


def answer_question(
    question: str,
    schedules: list[dict[str, Any]],
    history: list[dict[str, str]] | None = None,
) -> str:
    client = get_client()
    data_json = json.dumps(schedules, ensure_ascii=False, separators=(",", ":"))
    system_text = QUERY_SYSTEM_TEMPLATE.format(data=data_json)

    contents: list[types.Content] = []
    for turn in (history or [])[-MAX_HISTORY_TURNS * 2:]:
        role = "model" if turn.get("role") == "bot" else "user"
        text = turn.get("text", "")
        if text:
            contents.append(types.Content(role=role, parts=[types.Part.from_text(text=text)]))
    contents.append(types.Content(role="user", parts=[types.Part.from_text(text=question)]))

    response = _with_retries(lambda: client.models.generate_content(
        model=QUERY_MODEL,
        contents=contents,
        config=types.GenerateContentConfig(system_instruction=system_text),
    ))
    return response.text
