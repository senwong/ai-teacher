from app.agent.lesson import lesson_for
from app.agent.state_machine import decide_next_state
from app.agent.strategy import select_strategy
from app.agent.teaching_flow import TeachingMode, select_teaching_mode
from app.curriculum.grade3_math import SKILLS
from app.llm.provider import client, enabled, text_model


def base_teaching_message(skill_id: str, progress: dict, strategy, teaching_mode: TeachingMode) -> str:
    skill = SKILLS[skill_id]
    if teaching_mode == TeachingMode.FULL_LESSON:
        return f"今天先把「{skill['title']}」真正弄懂。我们先用「{strategy.label}」的方法来学。"
    if teaching_mode == TeachingMode.RETEACH:
        return f"刚才这里还不稳定，我们换成「{strategy.label}」重新讲一遍，再继续练。"
    if teaching_mode == TeachingMode.QUICK_RECAP:
        return f"你已经有一些基础了。先用一个关键概念和例子快速回顾「{skill['title']}」，再开始练习。"
    return f"这个知识点已经比较稳定，直接练习巩固；我会根据结果决定是否需要再讲。"


def llm_teaching_message(skill_id: str, progress: dict, strategy, teaching_mode: TeachingMode) -> str | None:
    if not enabled():
        return None
    try:
        skill = SKILLS[skill_id]
        response = client().responses.create(
            model=text_model(),
            input=(
                "你是耐心的小学三年级数学老师。用自然、鼓励但不幼稚的中文，"
                "用1到2句话告诉学生接下来会怎样学习。这里只做课堂开场，不要代替后面的正式知识讲解，控制在80字以内。"
                f"知识点：{skill['title']}；目标：{skill['objective']}；"
                f"学生尝试次数：{progress['attempts']}；掌握度：{progress['mastery']:.0%}；"
                f"最近错误：{progress.get('last_error_type')}；"
                f"教学强度：{teaching_mode.value}；教学策略：{strategy.label}；选择原因：{strategy.reason}。"
            ),
        )
        return response.output_text.strip()
    except Exception:
        return None


def teaching_message(skill_id: str, progress: dict, strategy, teaching_mode: TeachingMode) -> str:
    return llm_teaching_message(skill_id, progress, strategy, teaching_mode) or base_teaching_message(
        skill_id, progress, strategy, teaching_mode
    )


def teacher_snapshot(skill_id: str, progress: dict):
    skill = SKILLS[skill_id]
    state = decide_next_state(progress, skill["mastery_threshold"], skill["minimum_attempts"])
    strategy = select_strategy(progress)
    teaching_mode = select_teaching_mode(progress, skill["mastery_threshold"])
    lesson = None
    if teaching_mode != TeachingMode.PRACTICE_ONLY:
        lesson = lesson_for(skill_id, progress, strategy)
        lesson["mode"] = teaching_mode.value

    return {
        "message": teaching_message(skill_id, progress, strategy, teaching_mode),
        "state": state.value,
        "teaching_mode": teaching_mode.value,
        "progress": progress,
        "strategy": {"id": strategy.id, "label": strategy.label, "reason": strategy.reason},
        "lesson": lesson,
    }
