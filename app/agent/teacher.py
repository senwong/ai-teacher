from app.agent.lesson import lesson_for
from app.agent.state_machine import decide_next_state
from app.agent.strategy import select_strategy
from app.curriculum.grade3_math import SKILLS
from app.llm.provider import client, enabled, text_model


def base_teaching_message(skill_id: str, progress: dict, strategy) -> str:
    skill = SKILLS[skill_id]
    if progress["attempts"] == 0:
        return f"今天先把「{skill['title']}」真正弄懂。我们先用「{strategy.label}」的方法来学。"
    if progress.get("last_error_type"):
        return f"刚才这里还不稳定，我们换成「{strategy.label}」重新讲一遍，再继续练。"
    return f"你已经有基础了，这次用「{strategy.label}」把方法再巩固一下。"


def llm_teaching_message(skill_id: str, progress: dict, strategy) -> str | None:
    if not enabled():
        return None
    try:
        skill = SKILLS[skill_id]
        response = client().responses.create(
            model=text_model(),
            input=(
                "你是耐心的小学三年级数学老师。用自然、鼓励但不幼稚的中文，"
                "用1到2句话向学生说明为什么这次要采用指定教学策略。不要出题，不要直接给答案，控制在80字以内。"
                f"知识点：{skill['title']}；目标：{skill['objective']}；"
                f"学生尝试次数：{progress['attempts']}；掌握度：{progress['mastery']:.0%}；"
                f"最近错误：{progress.get('last_error_type')}；"
                f"教学策略：{strategy.label}；选择原因：{strategy.reason}。"
            ),
        )
        return response.output_text.strip()
    except Exception:
        return None


def teaching_message(skill_id: str, progress: dict, strategy) -> str:
    return llm_teaching_message(skill_id, progress, strategy) or base_teaching_message(skill_id, progress, strategy)


def teacher_snapshot(skill_id: str, progress: dict):
    skill = SKILLS[skill_id]
    state = decide_next_state(progress, skill["mastery_threshold"], skill["minimum_attempts"])
    strategy = select_strategy(progress)
    return {
        "message": teaching_message(skill_id, progress, strategy),
        "state": state.value,
        "progress": progress,
        "strategy": {"id": strategy.id, "label": strategy.label, "reason": strategy.reason},
        "lesson": lesson_for(skill_id, progress, strategy) if state.value in {"teaching", "reteach"} else None,
    }
