from app.agent.lesson import lesson_for
from app.agent.state_machine import TeacherState, decide_next_state
from app.agent.strategy import select_strategy
from app.agent.teacher import teacher_snapshot
from app.agent.teaching_flow import TeachingMode, select_teaching_mode


def test_new_skill_enters_teaching_before_practice():
    progress = {"attempts": 0, "mastery": 0.0, "last_error_type": None}
    assert decide_next_state(progress, 0.8, 5) == TeacherState.TEACHING
    assert select_strategy(progress).id == "conceptual"
    assert select_teaching_mode(progress, 0.8) == TeachingMode.FULL_LESSON


def test_error_enters_reteach_with_vertical_strategy_for_carry():
    progress = {"attempts": 2, "mastery": 0.5, "last_error_type": "carry_error"}
    assert decide_next_state(progress, 0.8, 5) == TeacherState.RETEACH
    assert select_strategy(progress).id == "vertical_steps"
    assert select_teaching_mode(progress, 0.8) == TeachingMode.RETEACH


def test_generic_error_uses_error_contrast():
    progress = {"attempts": 2, "mastery": 0.4, "last_error_type": "calculation_error"}
    assert select_strategy(progress).id == "error_contrast"


def test_low_mastery_after_repeated_practice_uses_decomposition():
    progress = {"attempts": 4, "mastery": 0.5, "last_error_type": None}
    assert select_strategy(progress).id == "concrete_decomposition"


def test_partial_mastery_gets_quick_recap_instead_of_bare_practice():
    progress = {"attempts": 7, "mastery": 0.64, "last_error_type": None}
    assert decide_next_state(progress, 0.8, 5) == TeacherState.PRACTICE
    assert select_teaching_mode(progress, 0.8) == TeachingMode.QUICK_RECAP

    snapshot = teacher_snapshot("multiplication.one_digit_facts", progress)
    assert snapshot["teaching_mode"] == "quick_recap"
    assert snapshot["lesson"] is not None
    assert snapshot["lesson"]["concept"]
    assert snapshot["lesson"]["example_steps"]


def test_stable_mastery_can_go_straight_to_practice():
    progress = {"attempts": 8, "mastery": 0.88, "last_error_type": None}
    assert select_teaching_mode(progress, 0.8) == TeachingMode.PRACTICE_ONLY
    snapshot = teacher_snapshot("multiplication.one_digit_facts", progress)
    assert snapshot["lesson"] is None


def test_lesson_has_teaching_structure():
    progress = {"attempts": 0, "mastery": 0.0, "last_error_type": None}
    strategy = select_strategy(progress)
    lesson = lesson_for("multiplication.two_digit_by_one_digit", progress, strategy)
    assert lesson["concept"]
    assert len(lesson["method"]) >= 3
    assert len(lesson["example_steps"]) >= 2
    assert lesson["check_prompt"]
    assert lesson["check_answer"] == "78"
    assert lesson["strategy"]["id"] == "conceptual"


def test_reteach_changes_method_for_carry_error():
    progress = {"attempts": 2, "mastery": 0.5, "last_error_type": "carry_error"}
    lesson = lesson_for("multiplication.two_digit_by_one_digit", progress, select_strategy(progress))
    assert "进位" in lesson["tip"]
    assert "单独写出来" in lesson["method"][1]


def test_error_contrast_changes_explanation():
    progress = {"attempts": 2, "mastery": 0.4, "last_error_type": "calculation_error"}
    lesson = lesson_for("multiplication.two_digit_no_carry", progress, select_strategy(progress))
    assert "错误做法" in lesson["concept"]
    assert "正确步骤" in lesson["method"][1]
