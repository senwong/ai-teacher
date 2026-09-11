import json
import os
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.agent.teacher import teacher_snapshot
from app.assessment.diagnosis import feedback_for
from app.assessment.generator import generate_questions
from app.assessment.grader import grade
from app.auth.service import authenticate, create_login_session, create_user, destroy_login_session, user_from_session
from app.classroom.service import bootstrap_legacy_students, create_classroom, get_classroom_for_user, list_classrooms
from app.curriculum.grade3_math import SKILLS
from app.curriculum.roadmap import current_skill_for_student, roadmap_for_student
from app.db.sqlite import connect, init_db
from app.diagnostic.service import complete_diagnostic, create_diagnostic, get_diagnostic, latest_diagnostic
from app.review.service import learning_plan_for_student, review_queue
from app.session.service import create_session, finish_session, get_session, list_sessions
from app.student.model import get_progress, update_progress
from app.student.service import create_student, get_student_for_user, list_students, student_stats
from app.vision.preprocess import prepare_answer_sheet
from app.vision.reader import extract_submission, vision_enabled
from app.worksheet.pdf import render_worksheet_pdf
from app.worksheet.service import create_worksheet, get_worksheet, incoming_upload_path, mark_worksheet, pdf_path, save_vision_result, upload_path

BASE_DIR = Path(__file__).resolve().parent
app = FastAPI(title="AI Teacher MVP")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")
SESSIONS: dict[str, list[dict]] = {}
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
COOKIE_NAME = "ai_teacher_session"
COOKIE_SECURE = os.getenv("AI_TEACHER_COOKIE_SECURE", "false").lower() == "true"
PUBLIC_PATHS = {"/login", "/register", "/healthz"}


@app.on_event("startup")
def startup():
    init_db()


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    path = request.url.path
    if path.startswith("/static/") or path in PUBLIC_PATHS:
        return await call_next(request)
    user = user_from_session(request.cookies.get(COOKIE_NAME))
    request.state.user = user
    if user:
        return await call_next(request)
    if path.startswith("/api/"):
        return JSONResponse({"detail": "Authentication required"}, status_code=401)
    return RedirectResponse("/login", status_code=303)


def current_user(request: Request) -> dict:
    user = getattr(request.state, "user", None) or user_from_session(request.cookies.get(COOKIE_NAME))
    if not user:
        raise HTTPException(401, "Authentication required")
    return user


def require_classroom(request: Request, classroom_id: int) -> dict:
    classroom = get_classroom_for_user(classroom_id, current_user(request)["id"])
    if not classroom:
        raise HTTPException(404, "Classroom not found")
    return classroom


def require_student(request: Request, student_id: int) -> dict:
    student = get_student_for_user(student_id, current_user(request)["id"])
    if not student:
        raise HTTPException(404, "Student not found")
    return student


def require_session(request: Request, student_id: int, session_id: str):
    require_student(request, student_id)
    session = get_session(session_id)
    if not session or session["student_id"] != student_id:
        raise HTTPException(404, "Learning session not found")
    return session


def learning_context(request: Request, student: dict, session: dict, questions=None):
    plan = learning_plan_for_student(student["id"])
    return {
        "request": request,
        "user": current_user(request),
        "student": student,
        "session": session,
        "plan": plan,
        "skill_id": plan["skill_id"],
        "skill": plan["skill"],
        "snapshot": teacher_snapshot(plan["skill_id"], plan["progress"]),
        "questions": questions if questions is not None else SESSIONS.get(session["id"], []),
        "vision_enabled": vision_enabled(),
    }


def set_auth_cookie(response, token: str):
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=30 * 24 * 60 * 60,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        path="/",
    )


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    if user_from_session(request.cookies.get(COOKIE_NAME)):
        return RedirectResponse("/classes", status_code=303)
    return templates.TemplateResponse("register.html", {"request": request, "error": None})


@app.post("/register")
def register(request: Request, name: str = Form(...), email: str = Form(...), password: str = Form(...)):
    try:
        user = create_user(name, email, password)
        bootstrap_legacy_students(user["id"])
    except ValueError as exc:
        return templates.TemplateResponse("register.html", {"request": request, "error": str(exc)}, status_code=400)
    token = create_login_session(user["id"])
    response = RedirectResponse("/classes", status_code=303)
    set_auth_cookie(response, token)
    return response


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    if user_from_session(request.cookies.get(COOKIE_NAME)):
        return RedirectResponse("/classes", status_code=303)
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@app.post("/login")
def login(request: Request, email: str = Form(...), password: str = Form(...)):
    user = authenticate(email, password)
    if not user:
        return templates.TemplateResponse("login.html", {"request": request, "error": "邮箱或密码错误"}, status_code=400)
    token = create_login_session(user["id"])
    response = RedirectResponse("/classes", status_code=303)
    set_auth_cookie(response, token)
    return response


@app.post("/logout")
def logout(request: Request):
    destroy_login_session(request.cookies.get(COOKIE_NAME))
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie(COOKIE_NAME, path="/")
    return response


@app.get("/")
def root():
    return RedirectResponse("/classes", status_code=303)


@app.get("/students")
def old_students_route():
    return RedirectResponse("/classes", status_code=303)


@app.get("/classes", response_class=HTMLResponse)
def classes_page(request: Request):
    user = current_user(request)
    return templates.TemplateResponse("classes.html", {"request": request, "user": user, "classrooms": list_classrooms(user["id"])})


@app.get("/classes/new", response_class=HTMLResponse)
def new_classroom_page(request: Request):
    return templates.TemplateResponse("classroom_new.html", {"request": request, "user": current_user(request), "error": None})


@app.post("/classes")
def create_classroom_route(request: Request, name: str = Form(...), grade: int = Form(...)):
    user = current_user(request)
    try:
        classroom = create_classroom(user["id"], name, grade)
    except ValueError as exc:
        return templates.TemplateResponse("classroom_new.html", {"request": request, "user": user, "error": str(exc)}, status_code=400)
    return RedirectResponse(f"/classes/{classroom['id']}", status_code=303)


@app.get("/classes/{classroom_id}", response_class=HTMLResponse)
def classroom_detail(request: Request, classroom_id: int):
    classroom = require_classroom(request, classroom_id)
    return templates.TemplateResponse(
        "classroom_detail.html",
        {"request": request, "user": current_user(request), "classroom": classroom, "students": list_students(classroom_id)},
    )


@app.get("/classes/{classroom_id}/students/new", response_class=HTMLResponse)
def new_student_page(request: Request, classroom_id: int):
    classroom = require_classroom(request, classroom_id)
    return templates.TemplateResponse("student_new.html", {"request": request, "user": current_user(request), "classroom": classroom, "error": None})


@app.post("/classes/{classroom_id}/students")
def create_student_route(request: Request, classroom_id: int, name: str = Form(...), grade: int = Form(...)):
    classroom = require_classroom(request, classroom_id)
    try:
        student = create_student(name, grade, classroom_id)
    except ValueError as exc:
        return templates.TemplateResponse("student_new.html", {"request": request, "user": current_user(request), "classroom": classroom, "error": str(exc)}, status_code=400)
    return RedirectResponse(f"/students/{student['id']}", status_code=303)


@app.get("/students/{student_id}", response_class=HTMLResponse)
def student_detail(request: Request, student_id: int):
    student = require_student(request, student_id)
    classroom = require_classroom(request, student["classroom_id"])
    current_skill_id = current_skill_for_student(student_id)
    return templates.TemplateResponse("student_detail.html", {
        "request": request, "user": current_user(request), "classroom": classroom,
        "student": student, "stats": student_stats(student_id), "sessions": list_sessions(student_id),
        "roadmap": roadmap_for_student(student_id), "current_skill": SKILLS[current_skill_id],
        "current_skill_id": current_skill_id, "progress": get_progress(student_id, current_skill_id),
        "diagnostic": latest_diagnostic(student_id), "review_queue": review_queue(student_id),
    })


@app.post("/students/{student_id}/diagnostics")
def start_diagnostic(request: Request, student_id: int):
    require_student(request, student_id)
    assessment = create_diagnostic(student_id)
    return RedirectResponse(f"/students/{student_id}/diagnostics/{assessment['id']}", status_code=303)


@app.get("/students/{student_id}/diagnostics/{assessment_id}", response_class=HTMLResponse)
def diagnostic_page(request: Request, student_id: int, assessment_id: str):
    student = require_student(request, student_id)
    assessment = get_diagnostic(assessment_id)
    if not assessment or assessment["student_id"] != student_id:
        raise HTTPException(404, "Diagnostic assessment not found")
    template = "diagnostic_result.html" if assessment["status"] == "completed" else "diagnostic.html"
    return templates.TemplateResponse(template, {"request": request, "student": student, "assessment": assessment, "skills": SKILLS})


@app.post("/students/{student_id}/diagnostics/{assessment_id}/submit", response_class=HTMLResponse)
async def submit_diagnostic(request: Request, student_id: int, assessment_id: str):
    student = require_student(request, student_id)
    assessment = get_diagnostic(assessment_id)
    if not assessment or assessment["student_id"] != student_id:
        raise HTTPException(404, "Diagnostic assessment not found")
    form = await request.form()
    answers = {q["id"]: str(form.get(q["id"], "")) for q in assessment["questions"]}
    completed = complete_diagnostic(assessment_id, answers)
    return templates.TemplateResponse("diagnostic_result.html", {"request": request, "student": student, "assessment": completed})


@app.post("/students/{student_id}/sessions")
def start_session(request: Request, student_id: int):
    require_student(request, student_id)
    session = create_session(student_id)
    return RedirectResponse(f"/students/{student_id}/sessions/{session['id']}", status_code=303)


@app.get("/students/{student_id}/sessions/{session_id}", response_class=HTMLResponse)
def learning_home(request: Request, student_id: int, session_id: str):
    student = require_student(request, student_id)
    session = require_session(request, student_id, session_id)
    return templates.TemplateResponse("index.html", learning_context(request, student, session))


@app.post("/students/{student_id}/sessions/{session_id}/finish")
def finish_learning(request: Request, student_id: int, session_id: str):
    require_session(request, student_id, session_id)
    finish_session(session_id)
    SESSIONS.pop(session_id, None)
    return RedirectResponse(f"/students/{student_id}", status_code=303)


@app.post("/students/{student_id}/sessions/{session_id}/practice", response_class=HTMLResponse)
def practice(request: Request, student_id: int, session_id: str):
    student = require_student(request, student_id)
    session = require_session(request, student_id, session_id)
    plan = learning_plan_for_student(student_id)
    count = 3 if plan["mode"] == "review" else 5
    SESSIONS[session_id] = generate_questions(count, plan["skill_id"])
    return templates.TemplateResponse("index.html", learning_context(request, student, session, SESSIONS[session_id]))


@app.post("/students/{student_id}/sessions/{session_id}/worksheet", response_class=HTMLResponse)
def worksheet(request: Request, student_id: int, session_id: str):
    student = require_student(request, student_id)
    session = require_session(request, student_id, session_id)
    plan = learning_plan_for_student(student_id)
    count = 3 if plan["mode"] == "review" else 5
    item = create_worksheet(student_id, generate_questions(count, plan["skill_id"]), session_id)
    render_worksheet_pdf(item, pdf_path(item["id"]))
    return templates.TemplateResponse("worksheet.html", {"request": request, "student": student, "session": session, "worksheet": item, "vision_enabled": vision_enabled()})


def require_worksheet(request: Request, worksheet_id: str) -> dict:
    item = get_worksheet(worksheet_id)
    if not item:
        raise HTTPException(404, "Worksheet not found")
    require_student(request, item["student_id"])
    return item


@app.get("/worksheets/{worksheet_id}.pdf")
def worksheet_pdf(request: Request, worksheet_id: str):
    require_worksheet(request, worksheet_id)
    path = pdf_path(worksheet_id)
    if not path.exists():
        raise HTTPException(404, "Worksheet not found")
    return FileResponse(path, media_type="application/pdf", filename=f"worksheet-{worksheet_id}.pdf")


def _check_upload(photo: UploadFile):
    if photo.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(400, "Please upload JPG, PNG or WEBP")


def _review_context(request: Request, item: dict, preprocessing: dict, submission: dict | None, vision_error: str | None):
    student = require_student(request, item["student_id"])
    session = get_session(item.get("session_id")) if item.get("session_id") else None
    detailed = (submission or {}).get("answers", {})
    answers = {q["id"]: detailed.get(q["id"], {}).get("final_answer", "") for q in item["questions"]}
    return templates.TemplateResponse("review.html", {"request": request, "student": student, "session": session, "worksheet": item, "answers": answers, "details": detailed, "preprocessing": preprocessing, "vision_error": vision_error, "vision_enabled": vision_enabled()})


def _analyze_upload(request: Request, item: dict, image_path: Path):
    require_student(request, item["student_id"])
    preprocessing = prepare_answer_sheet(image_path)
    detected_id = preprocessing.get("worksheet_id")
    if detected_id and detected_id != item["id"]:
        raise HTTPException(400, f"QR code belongs to worksheet {detected_id}")
    mark_worksheet(item["id"], "uploaded", str(image_path))
    submission = None
    vision_error = None
    if vision_enabled():
        try:
            submission = extract_submission(preprocessing["processed_path"], item["questions"])
        except Exception as exc:
            vision_error = str(exc)
    saved = {"preprocessing": {k: preprocessing.get(k) for k in ("worksheet_id", "qr_raw", "page_detected", "width", "height")}, "submission": submission, "vision_error": vision_error}
    save_vision_result(item["id"], saved, str(preprocessing["processed_path"]))
    return _review_context(request, item, preprocessing, submission, vision_error)


@app.post("/worksheets/{worksheet_id}/upload", response_class=HTMLResponse)
async def upload_worksheet(request: Request, worksheet_id: str, photo: UploadFile = File(...)):
    item = require_worksheet(request, worksheet_id)
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
        raise HTTPException(400, "Worksheet QR code was not detected")
    item = require_worksheet(request, worksheet_id)
    return _analyze_upload(request, item, target)


def grade_answers(student: dict, questions: list[dict], answers: dict[str, str], worksheet_id: str | None = None, session_id: str | None = None):
    results = []
    vision_details = {}
    if worksheet_id:
        ws = get_worksheet(worksheet_id)
        if ws and ws.get("vision"):
            vision_details = (((ws["vision"] or {}).get("submission") or {}).get("answers") or {})
    for q in questions:
        raw = str(answers.get(q["id"], ""))
        result = grade(q, raw)
        result["question"] = q
        result["feedback"] = feedback_for(result["error_type"])
        result["vision_detail"] = vision_details.get(q["id"])
        update_progress(student["id"], q["skill_id"], result["is_correct"], result["error_type"])
        with connect() as conn:
            conn.execute("INSERT INTO attempts(student_id,skill_id,question_json,student_answer,is_correct,error_type,feedback,worksheet_id,session_id) VALUES (?,?,?,?,?,?,?,?,?)", (student["id"], q["skill_id"], json.dumps(q, ensure_ascii=False), raw, int(result["is_correct"]), result["error_type"], result["feedback"], worksheet_id, session_id))
        results.append(result)
    return results


def result_context(request: Request, student: dict, session: dict | None, results: list[dict], worksheet_id: str | None = None):
    plan = learning_plan_for_student(student["id"])
    return {"request": request, "student": student, "session": session, "snapshot": teacher_snapshot(plan["skill_id"], plan["progress"]), "results": results, "worksheet_id": worksheet_id, "next_plan": plan}


@app.post("/worksheets/{worksheet_id}/grade", response_class=HTMLResponse)
async def grade_worksheet(request: Request, worksheet_id: str):
    item = require_worksheet(request, worksheet_id)
    student = require_student(request, item["student_id"])
    session = get_session(item.get("session_id")) if item.get("session_id") else None
    form = await request.form()
    answers = {q["id"]: str(form.get(q["id"], "")) for q in item["questions"]}
    results = grade_answers(student, item["questions"], answers, worksheet_id, item.get("session_id"))
    mark_worksheet(worksheet_id, "graded")
    return templates.TemplateResponse("results.html", result_context(request, student, session, results, worksheet_id))


@app.post("/students/{student_id}/sessions/{session_id}/submit", response_class=HTMLResponse)
async def submit(request: Request, student_id: int, session_id: str):
    student = require_student(request, student_id)
    session = require_session(request, student_id, session_id)
    questions = SESSIONS.get(session_id, [])
    form = await request.form()
    answers = {q["id"]: str(form.get(q["id"], "")) for q in questions}
    results = grade_answers(student, questions, answers, session_id=session_id)
    SESSIONS[session_id] = []
    return templates.TemplateResponse("results.html", result_context(request, student, session, results))


@app.get("/api/students/{student_id}")
def api_student(request: Request, student_id: int):
    student = require_student(request, student_id)
    skill_id = current_skill_for_student(student_id)
    plan = learning_plan_for_student(student_id)
    return {"student": student, "current_skill": skill_id, "progress": get_progress(student_id, skill_id), "roadmap": roadmap_for_student(student_id), "diagnostic": latest_diagnostic(student_id), "review_queue": review_queue(student_id), "learning_plan": plan, "stats": student_stats(student_id), "sessions": list_sessions(student_id)}
