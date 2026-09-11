import os
import tempfile
from pathlib import Path


def test_student_and_session_lifecycle(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        import app.db.sqlite as db
        db.DB_PATH = Path(tmp) / "test.db"
        db.init_db()
        from app.student.service import create_student, get_student
        from app.session.service import create_session, finish_session
        student = create_student("小明", 3)
        assert get_student(student["id"])["name"] == "小明"
        session = create_session(student["id"])
        assert session["status"] == "active"
        done = finish_session(session["id"])
        assert done["status"] == "completed"
