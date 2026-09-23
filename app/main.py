import json

from fastapi import FastAPI, Form, Request, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from . import data_store, gemini_client
from .config import ADMIN_PASSWORD, BASE_DIR, PENDING_EXTRACTION_FILE, SESSION_SECRET

app = FastAPI(title="ผู้ช่วยตารางสอนอาจารย์")
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "app" / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))


def is_admin(request: Request) -> bool:
    return bool(request.session.get("admin"))


@app.get("/", response_class=HTMLResponse)
def chat_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/api/chat")
async def chat_api(request: Request):
    body = await request.json()
    question = (body.get("question") or "").strip()
    history = body.get("history") or []
    if not question:
        return JSONResponse({"error": "กรุณาพิมพ์คำถาม"}, status_code=400)

    schedules = data_store.load_schedules()
    if not schedules:
        return {"answer": "ยังไม่มีข้อมูลตารางสอนในระบบ กรุณาให้แอดมินอัปโหลดข้อมูลก่อนครับ"}

    try:
        answer = gemini_client.answer_question(question, schedules, history)
    except gemini_client.QuotaExceededError:
        return JSONResponse(
            {"error": "ขออภัยครับ วันนี้มีผู้ใช้งานเยอะจนครบโควตาการตอบคำถามแล้ว กรุณาลองใหม่พรุ่งนี้ครับ"},
            status_code=503,
        )
    except Exception as e:
        print(f"[chat_api] unexpected error: {e!r}")
        return JSONResponse(
            {"error": "เกิดข้อผิดพลาดในระบบ กรุณาลองใหม่อีกครั้งครับ"}, status_code=500
        )

    return {"answer": answer}


@app.get("/admin/login", response_class=HTMLResponse)
def admin_login_page(request: Request):
    return templates.TemplateResponse("admin_login.html", {"request": request, "error": None})


@app.post("/admin/login")
def admin_login(request: Request, password: str = Form(...)):
    if password == ADMIN_PASSWORD:
        request.session["admin"] = True
        return RedirectResponse("/admin/upload", status_code=303)
    return templates.TemplateResponse(
        "admin_login.html", {"request": request, "error": "รหัสผ่านไม่ถูกต้อง"}, status_code=401
    )


@app.get("/admin/logout")
def admin_logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=303)


@app.get("/admin/upload", response_class=HTMLResponse)
def admin_upload_page(request: Request):
    if not is_admin(request):
        return RedirectResponse("/admin/login", status_code=303)
    saved = request.query_params.get("saved") == "1"
    return templates.TemplateResponse(
        "admin_upload.html", {"request": request, "error": None, "saved": saved}
    )


@app.post("/admin/upload")
async def admin_upload(request: Request, file: UploadFile = File(...)):
    if not is_admin(request):
        return RedirectResponse("/admin/login", status_code=303)

    if file.content_type != "application/pdf":
        return templates.TemplateResponse(
            "admin_upload.html",
            {"request": request, "error": "กรุณาอัปโหลดไฟล์ PDF เท่านั้น", "saved": False},
            status_code=400,
        )

    pdf_bytes = await file.read()
    try:
        extracted = gemini_client.extract_schedule_from_pdf(pdf_bytes)
    except Exception as e:
        return templates.TemplateResponse(
            "admin_upload.html",
            {"request": request, "error": f"สกัดข้อมูลไม่สำเร็จ: {e}", "saved": False},
            status_code=500,
        )

    PENDING_EXTRACTION_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(PENDING_EXTRACTION_FILE, "w", encoding="utf-8") as f:
        json.dump(extracted, f, ensure_ascii=False)
    return RedirectResponse("/admin/review", status_code=303)


@app.get("/admin/review", response_class=HTMLResponse)
def admin_review_page(request: Request):
    if not is_admin(request):
        return RedirectResponse("/admin/login", status_code=303)

    if not PENDING_EXTRACTION_FILE.exists():
        return RedirectResponse("/admin/upload", status_code=303)
    with open(PENDING_EXTRACTION_FILE, "r", encoding="utf-8") as f:
        pending = json.load(f)

    pretty = json.dumps(pending, ensure_ascii=False, indent=2)
    return templates.TemplateResponse(
        "admin_review.html", {"request": request, "data_json": pretty, "error": None}
    )


@app.post("/admin/save")
def admin_save(request: Request, data_json: str = Form(...)):
    if not is_admin(request):
        return RedirectResponse("/admin/login", status_code=303)

    try:
        teacher = json.loads(data_json)
    except json.JSONDecodeError as e:
        return templates.TemplateResponse(
            "admin_review.html",
            {"request": request, "data_json": data_json, "error": f"JSON ไม่ถูกต้อง: {e}"},
            status_code=400,
        )

    schedules = data_store.load_schedules()
    schedules = data_store.upsert_teacher(schedules, teacher)
    data_store.save_schedules(schedules)
    PENDING_EXTRACTION_FILE.unlink(missing_ok=True)
    return RedirectResponse("/admin/upload?saved=1", status_code=303)
