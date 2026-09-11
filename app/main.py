import json
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.agent.teacher import teacher_snapshot
from app.assessment.diagnosis import feedback_for
from app.assessment.generator import generate_questions
from app.assessment.grader import grade
from app.curriculum.grade3_math import DEFAULT_SKILL_ID
from app.db.sqlite import connect, get_or_create_student, init_db
from app.student.model import get_progress, update_progress
from app.vision.preprocess import prepare_answer_sheet
from app.vision.reader import extract_submission, vision_enabled
from app.worksheet.pdf import render_worksheet_pdf
from app.worksheet.service import (
    create_worksheet,
    get_worksheet,
    incoming_upload_path,
    mark_worksheet,
    pdf_path,
    save_vision_result,
    upload_path,
)

BASE_DIR = Path(__file__).resolve().parent
app = FastAPI(title="AI Teacher MVP")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

SESSIONS: dict[int, list[dict]] = {}
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


@app.on_event("startup")
def startup():
    init_db()


def context_for_home(request: Request, questions=None, worksheet=None):
    student = get_or_create_student()
    progress = get_progress(student["id"], DEFAULT_SKILL_ID)
    return {
        "request": request,
        "student": student,
        "snapshot": teacher_snapshot(DEFAULT_SKILL_ID, progress),
        "questions": questions if questions is not None else SESSIONS.get(student["id"], []),
        "worksheet": worksheet,
        "vision_enabled": vision_enabled(),
    }


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", context_for_home(request))


@app.post("/practice", response_class=HTMLResponse)
def practice(request: Request):
    student = get_or_create_student()
    SESSIONS[student["id"]] = generate_questions(5)
    return templates.TemplateResponse("index.html", context_for_home(request, SESSIONS[student["id"]]))


@app.post("/worksheet", response_class=HTMLResponse)
def worksheet(request: Request):
    student = get_or_create_student()
    questions = generate_questions(5)
    item = create_worksheet(student["id"], questions)
    render_worksheet_pdf(item, pdf_path(item["id"]))
    return templates.TemplateResponse("worksheet.html", {**context_for_home(request), "worksheet": item, "vision_enabled": vision_enabled()})


@app.get("/worksheets/{worksheet_id}.pdf")
def worksheet_pdf(worksheet_id: str):
    item = get_worksheet(worksheet_id)
    path = pdf_path(worksheet_id)
    if not item or not path.exists():
        raise HTTPException(status_code=404, detail="Worksheet not found")
    return FileResponse(path, media_type="application/pdf", filename=f"worksheet-{worksheet_id}.pdf")


def _check_upload(photo: UploadFile):
    if photo.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Please upload JPG, PNG or WEBP")


def _review_context(request: Request, item: dict, preprocessing: dict, submission: dict | None, vision_error: str | None):
    detailed = (submission or {}).get("answers", {})
    answers = {q["id"]: detailed.get(q["id"], {}).get("final_answer", "") for q in item["questions"]}
    return templates.TemplateResponse("review.html", {
        **context_for_home(request),
        "worksheet": item,
        "answers": answers,
        "details": detailed,
        "preprocessing": preprocessing,
        "vision_error": vision_error,
    })


def _analyze_upload(request: Request, item: dict, image_path: Path):
    preprocessing = prepare_answer_sheet(image_path)
    detected_id = preprocessing.get("worksheet_id")
    if detected_id and detected_id != item["id"]:
        raise HTTPException(status_code=400, detail=f"QR code belongs to worksheet {detected_id}, not {item['id']}")

    mark_worksheet(item["id"], "uploaded", str(image_path))
    submission = None
    vision_error = None
    if vision_enabled():
        try:
            submission = extract_submission(preprocessing["processed_path"], item["questions"])
        except Exception as exc:
            vision_error = str(exc)

    saved = {
        "preprocessing": {
            "worksheet_id": preprocessing.get("worksheet_id"),
            "qr_raw": preprocessing.get("qr_raw"),
            "page_detected": preprocessing.get("page_detected"),
            "width": preprocessing.get("width"),
            "height": preprocessing.get("height"),
        },
        "submission": submission,
        "vision_error": vision_error,
    }
    save_vision_result(item["id"], saved, str(preprocessing["processed_path"]))
    return _review_context(request, item, preprocessing, submission, vision_error)


@app.post("/worksheets/{worksheet_id}/upload", response_class=HTMLResponse)
async def upload_worksheet(request: Request, worksheet_id: str, photo: UploadFile = File(...)):
    item = get_worksheet(worksheet_id)
    if not item:
        raise HTTPException(status_code=404, detail="Worksheet not found")
    _check_upload(photo)
    target = upload_path(worksheet_id, Path(photo.filename or "answer.jpg").suffix)
    target.write_bytes(await photo.read())
    return _analyze_upload(request, item, target)


@app.post("/answer-sheet/upload", response_class=HTMLResponse)
async def upload_unknown_worksheet(request: Request, photo: UploadFile = File(...)):
    _check_upload(photo)
    target = incoming_upload_path(Path(photo.filename or "answer.jpg").suffix)
    target.write_bytes(await photo.read())
    preprocessing = prepare_answer_sheet(target)
    worksheet_id = preprocessing.get("worksheet_id")
    if not worksheet_id:
        raise HTTPException(status_code=400, detail="Worksheet QR code was not detected. Photograph the whole page or upload from the worksheet page.")
    item = get_worksheet(worksheet_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Worksheet {worksheet_id} was not found")
    return _analyze_upload(request, item, target)


def grade_answers(student: dict, questions: list[dict], answers: dict[str, str], worksheet_id: str | None = None):
    results = []
    vision_details = {}
    if worksheet_id:
        worksheet = get_worksheet(worksheet_id)
        if worksheet and worksheet.get("vision"):
            vision_details = (((worksheet["vision"] or {}).get("submission") or {}).get("answers") or {})

    for q in questions:
        raw = str(answers.get(q["id"], ""))
        result = grade(q, raw)
        result["question"] = q
        result["feedback"] = feedback_for(result["error_type"])
        result["vision_detail"] = vision_details.get(q["id"])
        update_progress(student["id"], q["skill_id"], result["is_correct"], result["error_type"])
        with connect() as conn:
            conn.execute(
                "INSERT INTO attempts(student_id, skill_id, question_json, student_answer, is_correct, error_type, feedback, worksheet_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (student["id"], q["skill_id"], json.dumps(q, ensure_ascii=False), raw, int(result["is_correct"]), result["error_type"], result["feedback"], worksheet_id),
            )
        results.append(result)
    return results


@app.post("/worksheets/{worksheet_id}/grade", response_class=HTMLResponse)
async def grade_worksheet(request: Request, worksheet_id: str):
    student = get_or_create_student()
    item = get_worksheet(worksheet_id)
    if not item:
        raise HTTPException(status_code=404, detail="Worksheet not found")
    form = await request.form()
    answers = {q["id"]: str(form.get(q["id"], "")) for q in item["questions"]}
    results = grade_answers(student, item["questions"], answers, worksheet_id)
    mark_worksheet(worksheet_id, "graded")
    progress = get_progress(student["id"], DEFAULT_SKILL_ID)
    return templates.TemplateResponse("results.html", {"request": request, "student": student, "snapshot": teacher_snapshot(DEFAULT_SKILL_ID, progress), "results": results, "worksheet_id": worksheet_id})


@app.post("/submit", response_class=HTMLResponse)
async def submit(request: Request):
    student = get_or_create_student()
    questions = SESSIONS.get(student["id"], [])
    form = await request.form()
    answers = {q["id"]: str(form.get(q["id"], "")) for q in questions}
    results = grade_answers(student, questions, answers)
    SESSIONS[student["id"]] = []
    progress = get_progress(student["id"], DEFAULT_SKILL_ID)
    return templates.TemplateResponse("results.html", {"request": request, "student": student, "snapshot": teacher_snapshot(DEFAULT_SKILL_ID, progress), "results": results})


@app.get("/api/student")
def api_student():
    student = get_or_create_student()
    return {"student": student, "progress": get_progress(student["id"], DEFAULT_SKILL_ID)}
