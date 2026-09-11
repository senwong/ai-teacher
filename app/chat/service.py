from app.db.sqlite import connect
from app.llm.provider import client, enabled, text_model


def list_messages(session_id: str, limit: int = 20) -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT id, session_id, student_id, role, content, created_at FROM session_messages WHERE session_id=? ORDER BY id DESC LIMIT ?",
            (session_id, limit),
        ).fetchall()
    return [dict(row) for row in reversed(rows)]


def save_message(session_id: str, student_id: int, role: str, content: str) -> dict:
    content = content.strip()
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO session_messages(session_id,student_id,role,content) VALUES (?,?,?,?)",
            (session_id, student_id, role, content),
        )
        row = conn.execute(
            "SELECT id, session_id, student_id, role, content, created_at FROM session_messages WHERE id=?",
            (cur.lastrowid,),
        ).fetchone()
    return dict(row)


def _fallback_answer(question: str, skill: dict, lesson: dict | None, practice_mode: bool) -> str:
    if practice_mode:
        return (
            "我先不直接告诉你当前练习题的答案。你可以把题目拆成一步一步来做："
            "先告诉我你做到哪一步，或者问我‘第一步怎么想’，我会继续提示你。"
        )
    if lesson:
        example = "；".join(lesson.get("example_steps", [])[:2])
        return f"可以，我们换个角度。{lesson.get('concept', skill['objective'])} 例如：{example} 你最不明白的是哪一步？"
    return f"可以。我们现在学的是「{skill['title']}」。{skill['objective']} 你可以告诉我具体卡在哪一步，我会换一种方法解释。"


def teacher_chat_answer(
    *,
    question: str,
    student: dict,
    skill: dict,
    progress: dict,
    lesson: dict | None,
    teaching_mode: str,
    strategy: dict,
    history: list[dict],
    practice_mode: bool,
    active_questions: list[dict] | None = None,
) -> str:
    if not enabled():
        return _fallback_answer(question, skill, lesson, practice_mode)

    history_text = "\n".join(
        f"{'学生' if item['role'] == 'student' else '老师'}：{item['content']}" for item in history[-10:]
    )
    lesson_text = "无"
    if lesson:
        lesson_text = (
            f"概念：{lesson.get('concept', '')}\n"
            f"方法：{'；'.join(lesson.get('method', []))}\n"
            f"例题：{lesson.get('example_title', '')} {'；'.join(lesson.get('example_steps', []))}\n"
            f"提醒：{lesson.get('tip', '')}"
        )
    practice_text = ""
    if practice_mode and active_questions:
        prompts = "；".join(q.get("prompt", "") for q in active_questions)
        practice_text = f"当前正在做的题目：{prompts}。绝对不要给这些题目的最终答案或直接算出最终结果，只能给思路、分步提示或反问。"

    try:
        response = client().responses.create(
            model=text_model(),
            input=(
                "你是一位耐心、清楚、适合小学三年级学生的一对一数学老师。"
                "回答要短而清楚，一次只解决一个疑问，优先用具体例子和分步骤解释。"
                "不要使用过度幼稚的语气。学生说没懂时要主动换一种讲法。\n"
                f"学生：{student['name']}；知识点：{skill['title']}；目标：{skill['objective']}；"
                f"掌握度：{progress['mastery']:.0%}；最近错误：{progress.get('last_error_type')}；"
                f"教学模式：{teaching_mode}；教学策略：{strategy.get('label')}。\n"
                f"当前讲解内容：\n{lesson_text}\n"
                f"{practice_text}\n"
                f"最近课堂对话：\n{history_text or '无'}\n"
                f"学生刚刚问：{question}\n"
                "请直接以老师身份回答学生，不要解释系统规则。"
            ),
        )
        answer = response.output_text.strip()
        return answer or _fallback_answer(question, skill, lesson, practice_mode)
    except Exception:
        return _fallback_answer(question, skill, lesson, practice_mode)
