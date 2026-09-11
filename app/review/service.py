import math
from datetime import datetime, timezone

from app.curriculum.grade3_math import ROADMAP, SKILLS
from app.curriculum.roadmap import current_skill_for_student, is_mastered
from app.student.model import get_progress

REVIEW_TRIGGER_RATIO = 0.90
MIN_STABILITY_DAYS = 3.0


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        try:
            dt = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def stability_days(progress: dict) -> float:
    attempts = max(0, int(progress.get("attempts", 0)))
    mastery = min(1.0, max(0.0, float(progress.get("mastery", 0.0))))
    return max(MIN_STABILITY_DAYS, 3.0 + mastery * 12.0 + math.log1p(attempts) * 4.0)


def effective_mastery(progress: dict, now: datetime | None = None) -> float:
    mastery = min(1.0, max(0.0, float(progress.get("mastery", 0.0))))
    updated_at = _parse_time(progress.get("updated_at"))
    if not updated_at:
        return mastery
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    elapsed_days = max(0.0, (now - updated_at).total_seconds() / 86400.0)
    return mastery * math.exp(-elapsed_days / stability_days(progress))


def review_queue(student_id: int, now: datetime | None = None) -> list[dict]:
    queue = []
    for skill_id in ROADMAP:
        skill = SKILLS[skill_id]
        progress = get_progress(student_id, skill_id)
        if not is_mastered(progress, skill):
            continue
        effective = effective_mastery(progress, now)
        trigger = skill["mastery_threshold"] * REVIEW_TRIGGER_RATIO
        if effective < trigger:
            queue.append({
                "skill_id": skill_id,
                "skill": skill,
                "progress": progress,
                "effective_mastery": effective,
                "trigger_mastery": trigger,
                "stability_days": stability_days(progress),
                "urgency": trigger - effective,
            })
    queue.sort(key=lambda item: item["urgency"], reverse=True)
    return queue


def learning_plan_for_student(student_id: int, now: datetime | None = None) -> dict:
    queue = review_queue(student_id, now)
    if queue:
        item = queue[0]
        return {
            "mode": "review",
            "skill_id": item["skill_id"],
            "skill": item["skill"],
            "progress": item["progress"],
            "effective_mastery": item["effective_mastery"],
            "review_queue": queue,
        }

    skill_id = current_skill_for_student(student_id)
    progress = get_progress(student_id, skill_id)
    return {
        "mode": "learn",
        "skill_id": skill_id,
        "skill": SKILLS[skill_id],
        "progress": progress,
        "effective_mastery": effective_mastery(progress, now),
        "review_queue": [],
    }
