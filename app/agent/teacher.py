from app.agent.state_machine import decide_next_state
from app.curriculum.grade3_math import SKILLS
from app.llm.provider import client, enabled, text_model


def base_teaching_message(skill_id: str, progress: dict) -> str:
    skill = SKILLS[skill_id]
    if progress["attempts"] == 0:
        return f"今天我们学习「{skill['title']}」。{skill['explanation']} 先看例子：24 × 3，可以想成 20 × 3 + 4 × 3 = 72。"
    if progress.get("last_error_type") == "carry_error":
        return "你已经会基本步骤了，我们重点复习进位：个位相乘满十时，把十位数字进到下一位，再继续计算。"
    return f"继续练习「{skill['title']}」。先慢一点，把每一步写清楚，比只追求速度更重要。"


def llm_teaching_message(skill_id: str, progress: dict) -> str | None:
    if not enabled():
        return None
    try:
        skill = SKILLS[skill_id]
        response = client().responses.create(
            model=text_model(),
            input=(
                "你是耐心的小学三年级数学老师。请用80字以内中文讲解当前知识点，不直接给练习答案。"
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
    return {
        "message": teaching_message(skill_id, progress),
        "state": decide_next_state(progress, skill["mastery_threshold"], skill["minimum_attempts"]).value,
        "progress": progress,
    }
