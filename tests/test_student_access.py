import tempfile
from pathlib import Path


def _reset_db(tmp: str):
    import app.db.sqlite as db
    db.DB_PATH = Path(tmp) / "test.db"
    db.init_db()


def test_student_pin_login_and_session_lifecycle():
    with tempfile.TemporaryDirectory() as tmp:
        _reset_db(tmp)

        from app.auth.service import create_user
        from app.classroom.service import create_classroom
        from app.db.sqlite import connect
        from app.student.access import (
            authenticate_student,
            authenticate_student_by_login_code,
            create_student_session,
            destroy_student_session,
            student_from_session,
        )
        from app.student.service import create_student

        teacher = create_user("张老师", "teacher@example.com", "password123")
        classroom = create_classroom(teacher["id"], "三年级一班", 3)
        student = create_student("小明", 3, classroom["id"])
        pin = student["initial_pin"]

        assert len(classroom["class_code"]) == 6
        assert len(pin) == 4 and pin.isdigit()
        assert student["login_code"]

        with connect() as conn:
            row = conn.execute("SELECT pin_hash, login_code FROM students WHERE id=?", (student["id"],)).fetchone()
            assert row["pin_hash"] != pin
            assert row["pin_hash"].startswith("scrypt$")
            assert row["login_code"] == student["login_code"]

        logged_in = authenticate_student(classroom["class_code"].lower(), "小明", pin)
        assert logged_in is not None
        assert logged_in["id"] == student["id"]
        assert authenticate_student_by_login_code(student["login_code"], pin)["id"] == student["id"]
        assert authenticate_student_by_login_code(student["login_code"], "9999") is None
        assert authenticate_student(classroom["class_code"], "小明", "99999") is None
        assert authenticate_student("WRONG1", "小明", pin) is None

        token = create_student_session(student["id"])
        assert student_from_session(token)["id"] == student["id"]
        destroy_student_session(token)
        assert student_from_session(token) is None


def test_student_names_are_unique_inside_a_classroom():
    with tempfile.TemporaryDirectory() as tmp:
        _reset_db(tmp)

        from app.auth.service import create_user
        from app.classroom.service import create_classroom
        from app.student.service import create_student

        teacher = create_user("老师", "teacher@example.com", "password123")
        classroom = create_classroom(teacher["id"], "三年级一班", 3)
        create_student("小明", 3, classroom["id"])

        try:
            create_student("小明", 3, classroom["id"])
            assert False, "duplicate student name should fail"
        except ValueError as exc:
            assert "不能重复" in str(exc)


def test_student_cannot_use_teacher_routes_with_student_cookie():
    with tempfile.TemporaryDirectory() as tmp:
        _reset_db(tmp)

        from fastapi.testclient import TestClient
        from app.auth.service import create_user
        from app.classroom.service import create_classroom
        from app.main import app, STUDENT_COOKIE_NAME
        from app.student.access import create_student_session
        from app.student.service import create_student

        teacher = create_user("老师", "teacher@example.com", "password123")
        classroom = create_classroom(teacher["id"], "三年级一班", 3)
        student = create_student("小明", 3, classroom["id"])
        token = create_student_session(student["id"])

        client = TestClient(app)
        client.cookies.set(STUDENT_COOKIE_NAME, token)
        response = client.get("/classes", follow_redirects=False)
        assert response.status_code == 303
        assert response.headers["location"] == "/learn"

        response = client.get("/learn")
        assert response.status_code == 200
        assert "你好，小明" in response.text


def test_qr_join_page_only_requires_pin_and_logs_student_in():
    with tempfile.TemporaryDirectory() as tmp:
        _reset_db(tmp)

        from fastapi.testclient import TestClient
        from app.auth.service import create_user
        from app.classroom.service import create_classroom
        from app.main import app, STUDENT_COOKIE_NAME
        from app.student.service import create_student

        teacher = create_user("老师", "teacher@example.com", "password123")
        classroom = create_classroom(teacher["id"], "三年级一班", 3)
        student = create_student("小明", 3, classroom["id"])
        pin = student["initial_pin"]

        client = TestClient(app)
        response = client.get(f"/student/join/{student['login_code']}")
        assert response.status_code == 200
        assert "你好，小明" in response.text
        assert "班级码" not in response.text

        response = client.post(
            f"/student/join/{student['login_code']}",
            data={"pin": pin},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers["location"] == "/learn"
        assert STUDENT_COOKIE_NAME in response.cookies


def test_teacher_learning_session_routes_are_removed():
    from app.main import app

    paths = {route.path for route in app.routes}
    assert "/students/{student_id}/sessions" not in paths
    assert "/students/{student_id}/sessions/{session_id}" not in paths
    assert "/students/{student_id}/sessions/{session_id}/practice" not in paths
    assert "/students/{student_id}/sessions/{session_id}/submit" not in paths
    assert "/students/{student_id}/sessions/{session_id}/finish" not in paths
    assert "/students/{student_id}/sessions/{session_id}/worksheet" not in paths
    assert "/learn/start" in paths
    assert "/learn/practice" in paths
    assert "/learn/submit" in paths
