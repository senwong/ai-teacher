from app.db.sqlite import connect


def get_progress(student_id: int, skill_id: str):
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM skill_progress WHERE student_id=? AND skill_id=?",
            (student_id, skill_id),
        ).fetchone()
        if not row:
            return {"student_id": student_id, "skill_id": skill_id, "attempts": 0, "correct": 0, "mastery": 0.0, "last_error_type": None}
        return dict(row)


def update_progress(student_id: int, skill_id: str, is_correct: bool, error_type: str | None):
    current = get_progress(student_id, skill_id)
    attempts = current["attempts"] + 1
    correct = current["correct"] + (1 if is_correct else 0)
    mastery = correct / attempts
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO skill_progress(student_id, skill_id, attempts, correct, mastery, last_error_type)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(student_id, skill_id) DO UPDATE SET
              attempts=excluded.attempts,
              correct=excluded.correct,
              mastery=excluded.mastery,
              last_error_type=excluded.last_error_type,
              updated_at=CURRENT_TIMESTAMP
            """,
            (student_id, skill_id, attempts, correct, mastery, error_type),
        )
    return get_progress(student_id, skill_id)
