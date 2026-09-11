import json
import math
import uuid
from collections import defaultdict

from app.assessment.generator import generate_questions
from app.assessment.grader import grade
from app.curriculum.grade3_math import SKILL_ORDER, SKILLS
from app.db.sqlite import connect


def create_diagnostic(student_id: int, questions_per_skill: int = 2) -> dict:
    questions = []
    index = 1
    for skill_id in SKILL_ORDER:
        for question in generate_questions(questions_per_skill, skill_id):
            item = dict(question)
            item["id"] = f"d{index}"
            item["diagnostic_skill_id"] = skill_id
            questions.append(item)
            index += 1

    assessment_id = uuid.uuid4().hex[:12]
    with connect() as conn:
        conn.execute(
            "INSERT INTO diagnostic_assessments(id, student_id, questions_json) VALUES (?, ?, ?)",
            (assessment_id, student_id, json.dumps(questions, ensure_ascii=False)),
        )
    return get_diagnostic(assessment_id)


def get_diagnostic(assessment_id: str) -> dict | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM diagnostic_assessments WHERE id=?", (assessment_id,)).fetchone()
    if not row:
        return None
    data = dict(row)
    data["questions"] = json.loads(data.pop("questions_json"))
    data["results"] = json.loads(data["results_json"]) if data.get("results_json") else None
    return data


def latest_diagnostic(student_id: int) -> dict | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT id FROM diagnostic_assessments WHERE student_id=? ORDER BY created_at DESC LIMIT 1",
            (student_id,),
        ).fetchone()
    return get_diagnostic(row["id"]) if row else None


def _seed_skill_progress(student_id: int, skill_id: str, mastery: float):
    skill = SKILLS[skill_id]
    attempts = skill["minimum_attempts"]
    correct = min(attempts, max(0, round(mastery * attempts)))
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO skill_progress(student_id, skill_id, attempts, correct, mastery, last_error_type)
            VALUES (?, ?, ?, ?, ?, NULL)
            ON CONFLICT(student_id, skill_id) DO UPDATE SET
              attempts=excluded.attempts,
              correct=excluded.correct,
              mastery=excluded.mastery,
              last_error_type=NULL,
              updated_at=CURRENT_TIMESTAMP
            """,
            (student_id, skill_id, attempts, correct, mastery),
        )


def complete_diagnostic(assessment_id: str, answers: dict[str, str]) -> dict:
    assessment = get_diagnostic(assessment_id)
    if not assessment:
        raise ValueError("Diagnostic assessment not found")

    grouped = defaultdict(lambda: {"correct": 0, "total": 0, "items": []})
    for question in assessment["questions"]:
        raw = str(answers.get(question["id"], "")).strip()
        result = grade(question, raw)
        skill_id = question["diagnostic_skill_id"]
        grouped[skill_id]["total"] += 1
        grouped[skill_id]["correct"] += int(result["is_correct"])
        grouped[skill_id]["items"].append({
            "question_id": question["id"],
            "prompt": question["prompt"],
            "student_answer": raw,
            "correct_answer": result["correct_answer"],
            "is_correct": result["is_correct"],
        })

    skill_results = []
    for skill_id in SKILL_ORDER:
        bucket = grouped[skill_id]
        mastery = bucket["correct"] / bucket["total"] if bucket["total"] else 0.0
        passed = mastery >= SKILLS[skill_id]["mastery_threshold"]
        _seed_skill_progress(assessment["student_id"], skill_id, mastery)
        skill_results.append({
            "skill_id": skill_id,
            "title": SKILLS[skill_id]["title"],
            "correct": bucket["correct"],
            "total": bucket["total"],
            "mastery": mastery,
            "passed": passed,
            "items": bucket["items"],
        })

    recommended_skill_id = SKILL_ORDER[-1]
    for item in skill_results:
        if not item["passed"]:
            recommended_skill_id = item["skill_id"]
            break

    payload = {
        "skills": skill_results,
        "recommended_skill_id": recommended_skill_id,
        "recommended_skill_title": SKILLS[recommended_skill_id]["title"],
    }
    with connect() as conn:
        conn.execute(
            "UPDATE diagnostic_assessments SET status='completed', results_json=?, completed_at=CURRENT_TIMESTAMP WHERE id=?",
            (json.dumps(payload, ensure_ascii=False), assessment_id),
        )
    return get_diagnostic(assessment_id)
