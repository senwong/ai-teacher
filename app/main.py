import json
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.agent.teacher import teacher_snapshot
from app.assessment.diagnosis import feedback_for
from app.assessment.generator import generate_questions
from app.assessment.grader import grade
from app.curriculum.grade3_math import DEFAULT_SKILL_ID
from app.db.sqlite import connect, get_or_create_student, init_db
from app.student.model import get_progress, update_progress

BASE_DIR = Path(__file__).resolve().parent
app = FastAPI(title="AI Teacher MVP")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

SESSIONS: dict[int, list[dict]] = {}

@app.on_event("startup")
def startup():
    init_db()

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    student = get_or_create_student()
    progress = get_progress(student["id"], DEFAULT_SKILL_ID)
    snapshot = teacher_snapshot(DEFAULT_SKILL_ID, progress)
    return templates.TemplateResponse("index.html", {
        "request": request,
        "student": student,
        "snapshot": snapshot,
        "questions": SESSIONS.get(student["id"], []),
    })

@app.post("/practice", response_class=HTMLResponse)
def practice(request: Request):
    student = get_or_create_student()
    SESSIONS[student["id"]] = generate_questions(5)
    progress = get_progress(student["id"], DEFAULT_SKILL_ID)
    snapshot = teacher_snapshot(DEFAULT_SKILL_ID, progress)
    return templates.TemplateResponse("index.html", {
        "request": request,
        "student": student,
        "snapshot": snapshot,
        "questions": SESSIONS[student["id"]],
    })

@app.post("/submit", response_class=HTMLResponse)
async def submit(request: Request):
    student = get_or_create_student()
    questions = SESSIONS.get(student["id"], [])
    form = await request.form()
    results = []
    for q in questions:
        raw = str(form.get(q["id"], ""))
        result = grade(q, raw)
        result["question"] = q
        result["feedback"] = feedback_for(result["error_type"])
        update_progress(student["id"], q["skill_id"], result["is_correct"], result["error_type"])
        with connect() as conn:
            conn.execute(
                "INSERT INTO attempts(student_id, skill_id, question_json, student_answer, is_correct, error_type, feedback) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (student["id"], q["skill_id"], json.dumps(q, ensure_ascii=False), raw, int(result["is_correct"]), result["error_type"], result["feedback"]),
            )
        results.append(result)
    SESSIONS[student["id"]] = []
    progress = get_progress(student["id"], DEFAULT_SKILL_ID)
    snapshot = teacher_snapshot(DEFAULT_SKILL_ID, progress)
    return templates.TemplateResponse("results.html", {
        "request": request,
        "student": student,
        "snapshot": snapshot,
        "results": results,
    })

@app.get("/api/student")
def api_student():
    student = get_or_create_student()
    return {"student": student, "progress": get_progress(student["id"], DEFAULT_SKILL_ID)}
