from app.assessment.generator import generate_questions
from app.curriculum.grade3_math import SKILLS
from app.curriculum.roadmap import is_mastered


def test_is_mastered_requires_attempts_and_threshold():
    skill = SKILLS["multiplication.one_digit_facts"]
    assert is_mastered({"attempts": 5, "mastery": 0.8}, skill)
    assert not is_mastered({"attempts": 4, "mastery": 1.0}, skill)
    assert not is_mastered({"attempts": 10, "mastery": 0.7}, skill)


def test_question_generator_respects_skill_id():
    questions = generate_questions(4, "multiplication.one_digit_facts")
    assert len(questions) == 4
    assert all(q["skill_id"] == "multiplication.one_digit_facts" for q in questions)
    assert all(2 <= q["a"] <= 9 and 2 <= q["b"] <= 9 for q in questions)
