from app.agent.lesson import lesson_for
from app.agent.state_machine import decide_next_state
from app.curriculum.grade3_math import SKILLS
from app.llm.provider import client, enabled, text_model


def base_teaching_message(skill_id: str, progress: dict) -> str:
    skill = SKILLS[skill_id]
    if progress["attempts"] == 0:
        return f"今天先把「{skill['title']}」真正弄懂，再开始做题。"
    if progress.get("last_error_type") == "carry_error":
        return "刚才的错误主要出在进位。我们换一种方式重新看一遍步骤，再继续练。"
    if progress.get("last_error_type"):
        return f"刚才有一步还不稳定，我们重新讲一下「{skill['title']}」的关键方法。"
    return f"你已经理解基本方法了，继续用「{skill['title']}」的方法练习。"


def llm_teaching_message(skill_id: str, progress: dict) -> str | None:
    if not enabled():
        return None
    try:
        skill = SKILLS[skill_id]
        response = client().responses.create(
            model=text_model(),
            input=(
                "你是耐心的小学三年级数学老师。用自然、鼓励但不幼稚的中文，"
                "用1到2句话告诉学生接下来为什么要学这个知识点。不要出题，不要直接给答案，控制在80字以内。"
                f"知识点：{skill['title']}；目标：{skill['objective']}；"
                f"学生尝试次数：{progress['attempts']}；掌握度：{progress['mastery']:.0%}；"
                f"最近错误：{progress.get('last_error_type')}。"
            ),
        )
        return response.output_text.strip()
    except Exception:
        return None


def teaching_message(skill_id: str, progress: dict) -> str:
    return llm_teaching_message(skill_id, progress) or base_teaching_message(skill_id, progress)


def teacher_snapshot(skill_id: str, progress: dict):
    skill = SKILLS[skill_id]
    state = decide_next_state(progress, skill["mastery_threshold"], skill["minimum_attempts"])
    return {
        "message": teaching_message(skill_id, progress),
        "state": state.value,
        "progress": progress,
        "lesson": lesson_for(skill_id, progress) if state.value in {"teaching", "reteach"} else None,
    }
