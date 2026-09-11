from datetime import datetime, timedelta, timezone

from app.review.service import effective_mastery, learning_plan_for_student, review_queue


def test_effective_mastery_decays_with_time():
    now = datetime(2026, 9, 11, tzinfo=timezone.utc)
    progress = {
        "attempts": 10,
        "mastery": 1.0,
        "updated_at": (now - timedelta(days=20)).isoformat(),
    }
    effective = effective_mastery(progress, now)
    assert 0 < effective < 1.0


def test_review_queue_prioritizes_overdue_mastered_skill(monkeypatch):
    import app.review.service as review

    now = datetime(2026, 9, 11, tzinfo=timezone.utc)
    old = (now - timedelta(days=40)).isoformat()
    fresh = now.isoformat()
    progress_map = {
        "multiplication.one_digit_facts": {"attempts": 10, "correct": 10, "mastery": 1.0, "updated_at": old},
        "multiplication.two_digit_no_carry": {"attempts": 10, "correct": 10, "mastery": 1.0, "updated_at": fresh},
        "multiplication.two_digit_by_one_digit": {"attempts": 0, "correct": 0, "mastery": 0.0, "updated_at": None},
        "multiplication.three_digit_by_one_digit": {"attempts": 0, "correct": 0, "mastery": 0.0, "updated_at": None},
    }
    monkeypatch.setattr(review, "get_progress", lambda student_id, skill_id: progress_map[skill_id])
    queue = review_queue(1, now)
    assert queue
    assert queue[0]["skill_id"] == "multiplication.one_digit_facts"

    plan = learning_plan_for_student(1, now)
    assert plan["mode"] == "review"
    assert plan["skill_id"] == "multiplication.one_digit_facts"
