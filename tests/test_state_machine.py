from app.agent.state_machine import TeacherState, decide_next_state


def test_next_skill_when_mastered():
    progress = {"attempts": 5, "mastery": 0.8, "last_error_type": None}
    assert decide_next_state(progress) == TeacherState.NEXT_SKILL


def test_reteach_after_error():
    progress = {"attempts": 2, "mastery": 0.5, "last_error_type": "carry_error"}
    assert decide_next_state(progress) == TeacherState.RETEACH
