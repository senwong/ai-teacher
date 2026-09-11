import json
import uuid
from app.db.sqlite import connect


def create_session(student_id: int) -> dict:
    session_id = uuid.uuid4().hex[:12]
    with connect() as conn:
        conn.execute("UPDATE learning_sessions SET status='completed', ended_at=CURRENT_TIMESTAMP WHERE student_id=? AND status='active'", (student_id,))
        conn.execute("INSERT INTO learning_sessions(id, student_id, status) VALUES (?, ?, 'active')", (session_id, student_id))
    return get_session(session_id)


def get_session(session_id: str) -> dict | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM learning_sessions WHERE id=?", (session_id,)).fetchone()
    if not row:
        return None
    data = dict(row)
    data["summary"] = json.loads(data["summary_json"]) if data.get("summary_json") else None
    return data


def mark_lesson_complete(session_id: str, skill_id: str) -> dict | None:
    with connect() as conn:
        conn.execute("UPDATE learning_sessions SET lesson_skill_id=? WHERE id=?", (skill_id, session_id))
    return get_session(session_id)


def list_sessions(student_id: int, limit: int = 20) -> list[dict]:
    with connect() as conn:
        rows = conn.execute("""
            SELECT ls.*,
                   COUNT(a.id) AS attempts,
                   COALESCE(SUM(a.is_correct),0) AS correct
            FROM learning_sessions ls
            LEFT JOIN attempts a ON a.session_id=ls.id
            WHERE ls.student_id=?
            GROUP BY ls.id
            ORDER BY ls.started_at DESC LIMIT ?
        """, (student_id, limit)).fetchall()
    return [dict(r) for r in rows]


def finish_session(session_id: str) -> dict | None:
    with connect() as conn:
        stats = conn.execute("SELECT COUNT(*) attempts, COALESCE(SUM(is_correct),0) correct FROM attempts WHERE session_id=?", (session_id,)).fetchone()
        summary = {"attempts": stats["attempts"], "correct": stats["correct"], "accuracy": stats["correct"] / stats["attempts"] if stats["attempts"] else 0}
        conn.execute("UPDATE learning_sessions SET status='completed', ended_at=CURRENT_TIMESTAMP, summary_json=? WHERE id=?", (json.dumps(summary), session_id))
    return get_session(session_id)
