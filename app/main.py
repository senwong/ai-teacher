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
from app.vision.reader import extract_answers, vision_enabled
from app.worksheet.pdf import render_worksheet_pdf
from app.worksheet.service import create_worksheet, get_worksheet, mark_worksheet, pdf_path, upload_path

BASE_DIR = Path(__file__).resolve().parent
app = FastAPI(title="AI Teacher MVP")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

SESSIONS: dict[int, list[dict]] = {}


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


@app.post("/worksheets/{worksheet_id}/upload", response_class=HTMLResponse)
async def upload_worksheet(request: Request, worksheet_id: str, photo: UploadFile = File(...)):
    item = get_worksheet(worksheet_id)
    if not item:
        raise HTTPException(status_code=404, detail="Worksheet not found")
    if photo.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(status_code=400, detail="Please upload JPG, PNG or WEBP")

    target = upload_path(worksheet_id, Path(photo.filename or "answer.jpg").suffix)
    target.write_bytes(await photo.read())
    mark_worksheet(worksheet_id, "uploaded", str(target))

    answers = None
    vision_error = None
    if vision_enabled():
        try:
            answers = extract_answers(target, item["questions"])
        except Exception as exc:
            vision_error = str(exc)

    return templates.TemplateResponse("review.html", {
        **context_for_home(request), "worksheet": item,
        "answers": answers or {q["id"]: "" for q in item["questions"]},
        "vision_error": vision_error,
    })


def grade_answers(student: dict, questions: list[dict], answers: dict[str, str], worksheet_id: str | None = None):
    results = []
    for q in questions:
        raw = str(answers.get(q["id"], ""))
        result = grade(q, raw)
        result["question"] = q
        result["feedback"] = feedback_for(result["error_type"])
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
