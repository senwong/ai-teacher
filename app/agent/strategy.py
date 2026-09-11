from dataclasses import dataclass


@dataclass(frozen=True)
class TeachingStrategy:
    id: str
    label: str
    reason: str


def select_strategy(progress: dict) -> TeachingStrategy:
    """Choose a deterministic teaching strategy from the student's current learning state."""
    attempts = int(progress.get("attempts") or 0)
    mastery = float(progress.get("mastery") or 0)
    last_error = progress.get("last_error_type")

    if attempts == 0:
        return TeachingStrategy(
            id="conceptual",
            label="理解含义",
            reason="第一次学习这个知识点，先建立概念再进入算法。",
        )
    if last_error == "carry_error":
        return TeachingStrategy(
            id="vertical_steps",
            label="竖式分步",
            reason="最近错误集中在进位，需要把每一步和进位位置显式写出来。",
        )
    if last_error:
        return TeachingStrategy(
            id="error_contrast",
            label="错误对比",
            reason="刚才出现了错误，用正确做法和常见错误并排比较更容易发现问题。",
        )
    if attempts >= 3 and mastery < 0.6:
        return TeachingStrategy(
            id="concrete_decomposition",
            label="拆分理解",
            reason="已经练习多次但掌握度仍较低，换成更直观的拆数方法重新建立理解。",
        )
    return TeachingStrategy(
        id="guided_steps",
        label="逐步引导",
        reason="基本概念已经建立，用简洁步骤巩固方法。",
    )
