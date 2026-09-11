from app.db.sqlite import get_or_create_student, init_db
from app.assessment.generator import generate_questions
from app.worksheet.service import create_worksheet, get_worksheet
from app.worksheet.pdf import render_worksheet_pdf


def test_worksheet_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr("app.db.sqlite.DB_PATH", tmp_path / "test.db")
    monkeypatch.setattr("app.worksheet.service.connect", __import__("app.db.sqlite", fromlist=["connect"]).connect)
    init_db()
    student = get_or_create_student()
    worksheet = create_worksheet(student["id"], generate_questions(3))
    loaded = get_worksheet(worksheet["id"])
    assert loaded is not None
    assert len(loaded["questions"]) == 3

    out = tmp_path / "worksheet.pdf"
    render_worksheet_pdf(loaded, out)
    assert out.exists()
    assert out.stat().st_size > 500
