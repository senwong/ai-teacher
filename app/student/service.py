from app.db.sqlite import connect
from app.curriculum.grade3_math import DEFAULT_SKILL_ID


def create_student(name: str, grade: int) -> dict:
    name = name.strip()
    if not name:
        raise ValueError("Student name is required")
    if grade < 1 or grade > 12:
        raise ValueError("Grade must be between 1 and 12")
    with connect() as conn:
        cur = conn.execute("INSERT INTO students(name, grade) VALUES (?, ?)", (name, grade))
        row = conn.execute("SELECT * FROM students WHERE id = ?", (cur.lastrowid,)).fetchone()
    return dict(row)


def get_student(student_id: int) -> dict | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
    return dict(row) if row else None


def list_students() -> list[dict]:
    with connect() as conn:
        rows = conn.execute("""
            SELECT s.*,
                   COALESCE(p.mastery, 0) AS mastery,
                   COALESCE(p.attempts, 0) AS attempts,
                   MAX(a.created_at) AS last_activity
            FROM students s
            LEFT JOIN skill_progress p ON p.student_id=s.id AND p.skill_id=?
            LEFT JOIN attempts a ON a.student_id=s.id
            GROUP BY s.id
            ORDER BY s.created_at DESC
        """, (DEFAULT_SKILL_ID,)).fetchall()
    return [dict(r) for r in rows]


def student_stats(student_id: int) -> dict:
    with connect() as conn:
        attempts = conn.execute("SELECT COUNT(*) c, COALESCE(SUM(is_correct),0) correct FROM attempts WHERE student_id=?", (student_id,)).fetchone()
        worksheets = conn.execute("SELECT COUNT(*) c FROM worksheets WHERE student_id=?", (student_id,)).fetchone()
        sessions = conn.execute("SELECT COUNT(*) c FROM learning_sessions WHERE student_id=?", (student_id,)).fetchone()
    total = attempts["c"]
    return {"attempts": total, "correct": attempts["correct"], "accuracy": attempts["correct"] / total if total else 0, "worksheets": worksheets["c"], "sessions": sessions["c"]}
