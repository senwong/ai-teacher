from app.db.sqlite import connect
from app.curriculum.grade3_math import DEFAULT_SKILL_ID
from app.student.access import generate_pin, set_student_pin


def create_student(name: str, grade: int, classroom_id: int | None = None) -> dict:
    name = name.strip()
    if not name:
        raise ValueError("Student name is required")
    if grade < 1 or grade > 12:
        raise ValueError("Grade must be between 1 and 12")
    with connect() as conn:
        if classroom_id is not None and conn.execute(
            "SELECT 1 FROM students WHERE classroom_id=? AND name=?",
            (classroom_id, name),
        ).fetchone():
            raise ValueError("同一班级内学生姓名不能重复")
        cur = conn.execute("INSERT INTO students(name, grade, classroom_id) VALUES (?, ?, ?)", (name, grade, classroom_id))
        row = conn.execute("SELECT * FROM students WHERE id = ?", (cur.lastrowid,)).fetchone()
    student = dict(row)
    pin = generate_pin()
    set_student_pin(student["id"], pin)
    student["initial_pin"] = pin
    return student


def reset_student_pin(student_id: int) -> str:
    pin = generate_pin()
    set_student_pin(student_id, pin)
    return pin


def get_student(student_id: int) -> dict | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
    return dict(row) if row else None


def get_student_for_user(student_id: int, user_id: int) -> dict | None:
    with connect() as conn:
        row = conn.execute(
            """SELECT s.* FROM students s
               JOIN classrooms c ON c.id=s.classroom_id
               WHERE s.id=? AND c.owner_user_id=?""",
            (student_id, user_id),
        ).fetchone()
    return dict(row) if row else None


def list_students(classroom_id: int | None = None) -> list[dict]:
    where = "WHERE s.classroom_id=?" if classroom_id is not None else ""
    params = [DEFAULT_SKILL_ID]
    if classroom_id is not None:
        params.append(classroom_id)
    with connect() as conn:
        rows = conn.execute(f"""
            SELECT s.*,
                   COALESCE(p.mastery, 0) AS mastery,
                   COALESCE(p.attempts, 0) AS attempts,
                   MAX(a.created_at) AS last_activity
            FROM students s
            LEFT JOIN skill_progress p ON p.student_id=s.id AND p.skill_id=?
            LEFT JOIN attempts a ON a.student_id=s.id
            {where}
            GROUP BY s.id
            ORDER BY s.created_at DESC
        """, tuple(params)).fetchall()
    return [dict(r) for r in rows]


def student_stats(student_id: int) -> dict:
    with connect() as conn:
        attempts = conn.execute("SELECT COUNT(*) c, COALESCE(SUM(is_correct),0) correct FROM attempts WHERE student_id=?", (student_id,)).fetchone()
        worksheets = conn.execute("SELECT COUNT(*) c FROM worksheets WHERE student_id=?", (student_id,)).fetchone()
        sessions = conn.execute("SELECT COUNT(*) c FROM learning_sessions WHERE student_id=?", (student_id,)).fetchone()
    total = attempts["c"]
    return {"attempts": total, "correct": attempts["correct"], "accuracy": attempts["correct"] / total if total else 0, "worksheets": worksheets["c"], "sessions": sessions["c"]}
