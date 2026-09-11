from enum import Enum


class TeachingMode(str, Enum):
    FULL_LESSON = "full_lesson"
    QUICK_RECAP = "quick_recap"
    RETEACH = "reteach"
    PRACTICE_ONLY = "practice_only"


def select_teaching_mode(progress: dict, mastery_threshold: float = 0.8) -> TeachingMode:
    """Choose how much teaching the student needs before practice.

    The state machine still decides curriculum progression. This layer only
    decides the teaching intensity for the current learning moment.
    """
    if progress["attempts"] == 0:
        return TeachingMode.FULL_LESSON
    if progress.get("last_error_type"):
        return TeachingMode.RETEACH
    if progress["mastery"] < mastery_threshold:
        return TeachingMode.QUICK_RECAP
    return TeachingMode.PRACTICE_ONLY
