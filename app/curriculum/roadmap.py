from app.curriculum.grade3_math import ROADMAP, SKILLS
from app.student.model import get_progress


def is_mastered(progress: dict, skill: dict) -> bool:
    return progress["attempts"] >= skill["minimum_attempts"] and progress["mastery"] >= skill["mastery_threshold"]


def roadmap_for_student(student_id: int) -> list[dict]:
    items = []
    unlocked = True
    for skill_id in ROADMAP:
        skill = SKILLS[skill_id]
        progress = get_progress(student_id, skill_id)
        mastered = is_mastered(progress, skill)
        status = "mastered" if mastered else ("current" if unlocked else "locked")
        items.append({"id": skill_id, "skill": skill, "progress": progress, "status": status})
        if not mastered:
            unlocked = False
    return items


def current_skill_for_student(student_id: int) -> str:
    for item in roadmap_for_student(student_id):
        if item["status"] == "current":
            return item["id"]
    return ROADMAP[-1]


def next_skill_id(student_id: int) -> str | None:
    current = current_skill_for_student(student_id)
    try:
        index = ROADMAP.index(current)
    except ValueError:
        return None
    progress = get_progress(student_id, current)
    if not is_mastered(progress, SKILLS[current]):
        return None
    return ROADMAP[index + 1] if index + 1 < len(ROADMAP) else None
