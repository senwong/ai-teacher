import tempfile
from pathlib import Path


def test_diagnostic_places_student_at_first_unmastered_skill():
    with tempfile.TemporaryDirectory() as tmp:
        import app.db.sqlite as db
        db.DB_PATH = Path(tmp) / "test.db"
        db.init_db()

        from app.curriculum.grade3_math import ROADMAP
        from app.curriculum.roadmap import current_skill_for_student
        from app.diagnostic.service import complete_diagnostic, create_diagnostic
        from app.student.service import create_student

        student = create_student("诊断学生", 3)
        assessment = create_diagnostic(student["id"], questions_per_skill=2)

        answers = {}
        mastered = set(ROADMAP[:2])
        for question in assessment["questions"]:
            if question["skill_id"] in mastered:
                answers[question["id"]] = str(question["answer"])
            else:
                answers[question["id"]] = "0"

        completed = complete_diagnostic(assessment["id"], answers)
        assert completed["status"] == "completed"
        assert completed["results"]["recommended_skill_id"] == ROADMAP[2]
        assert current_skill_for_student(student["id"]) == ROADMAP[2]
