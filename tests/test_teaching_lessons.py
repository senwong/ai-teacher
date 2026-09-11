from app.agent.lesson import lesson_for
from app.agent.state_machine import TeacherState, decide_next_state


def test_new_skill_enters_teaching_before_practice():
    progress = {"attempts": 0, "mastery": 0.0, "last_error_type": None}
    assert decide_next_state(progress, 0.8, 5) == TeacherState.TEACHING


def test_error_enters_reteach():
    progress = {"attempts": 2, "mastery": 0.5, "last_error_type": "carry_error"}
    assert decide_next_state(progress, 0.8, 5) == TeacherState.RETEACH


def test_lesson_has_teaching_structure():
    lesson = lesson_for("multiplication.two_digit_by_one_digit", {"last_error_type": None})
    assert lesson["concept"]
    assert len(lesson["method"]) >= 3
    assert len(lesson["example_steps"]) >= 2
    assert lesson["check_prompt"]
    assert lesson["check_answer"] == "78"


def test_reteach_adapts_to_carry_error():
    lesson = lesson_for("multiplication.two_digit_by_one_digit", {"last_error_type": "carry_error"})
    assert "进位" in lesson["tip"]
