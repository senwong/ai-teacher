from enum import Enum


class TeacherState(str, Enum):
    TEACHING = "teaching"
    PRACTICE = "practice"
    RETEACH = "reteach"
    NEXT_SKILL = "next_skill"


def decide_next_state(progress: dict, mastery_threshold: float = 0.8, minimum_attempts: int = 5):
    if progress["attempts"] == 0:
        return TeacherState.TEACHING
    if progress["attempts"] >= minimum_attempts and progress["mastery"] >= mastery_threshold:
        return TeacherState.NEXT_SKILL
    if progress.get("last_error_type"):
        return TeacherState.RETEACH
    return TeacherState.PRACTICE
