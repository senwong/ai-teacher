import tempfile
from pathlib import Path


def _reset_db(tmp: str):
    import app.db.sqlite as db
    db.DB_PATH = Path(tmp) / "test.db"
    db.init_db()


def test_password_session_and_classroom_isolation():
    with tempfile.TemporaryDirectory() as tmp:
        _reset_db(tmp)

        from app.auth.service import authenticate, create_login_session, create_user, destroy_login_session, user_from_session
        from app.classroom.service import create_classroom, get_classroom_for_user
        from app.db.sqlite import connect
        from app.student.service import create_student, get_student_for_user

        teacher_a = create_user("张老师", "a@example.com", "password123")
        teacher_b = create_user("李老师", "b@example.com", "password456")

        with connect() as conn:
            row = conn.execute("SELECT password_hash FROM users WHERE id=?", (teacher_a["id"],)).fetchone()
            assert row["password_hash"] != "password123"
            assert row["password_hash"].startswith("scrypt$")

        assert authenticate("a@example.com", "password123")["id"] == teacher_a["id"]
        assert authenticate("a@example.com", "wrong-password") is None

        token = create_login_session(teacher_a["id"])
        assert user_from_session(token)["id"] == teacher_a["id"]
        destroy_login_session(token)
        assert user_from_session(token) is None

        class_a = create_classroom(teacher_a["id"], "三年级一班", 3)
        class_b = create_classroom(teacher_b["id"], "三年级二班", 3)
        student_a = create_student("小明", 3, class_a["id"])
        student_b = create_student("小红", 3, class_b["id"])

        assert get_classroom_for_user(class_a["id"], teacher_a["id"])["id"] == class_a["id"]
        assert get_classroom_for_user(class_b["id"], teacher_a["id"]) is None
        assert get_student_for_user(student_a["id"], teacher_a["id"])["id"] == student_a["id"]
        assert get_student_for_user(student_b["id"], teacher_a["id"]) is None


def test_first_teacher_can_adopt_legacy_students():
    with tempfile.TemporaryDirectory() as tmp:
        _reset_db(tmp)

        from app.auth.service import create_user
        from app.classroom.service import bootstrap_legacy_students, list_classrooms
        from app.student.service import create_student, list_students

        create_student("历史学生", 3)
        teacher = create_user("老师", "teacher@example.com", "password123")
        classroom = bootstrap_legacy_students(teacher["id"])

        assert classroom is not None
        assert classroom["name"] == "历史学生"
        assert len(list_classrooms(teacher["id"])) == 1
        assert len(list_students(classroom["id"])) == 1
