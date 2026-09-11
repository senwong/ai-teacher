LESSONS = {
    "multiplication.one_digit_facts": {
        "concept": "乘法表示几个相同的数相加。例如 4 × 3，就是 3 个 4 相加。",
        "method": ["先看有几组相同的数", "把重复相加写成乘法", "用乘法口诀快速算出结果"],
        "example_title": "例子：4 × 3",
        "example_steps": ["4 + 4 + 4 = 12", "所以 4 × 3 = 12"],
        "tip": "先理解含义，再记口诀。这样遇到忘记口诀时也能推出来。",
        "check_prompt": "5 × 3 表示 3 个 5 相加，结果是多少？",
        "check_answer": "15",
        "check_hint": "把 5 连续加 3 次：5 + 5 + 5。",
    },
    "multiplication.two_digit_no_carry": {
        "concept": "两位数乘一位数，可以把两位数拆成几十和几个，分别去乘。",
        "method": ["把两位数拆成整十数和个位数", "分别乘同一个一位数", "把两个结果加起来"],
        "example_title": "例子：23 × 3",
        "example_steps": ["20 × 3 = 60", "3 × 3 = 9", "60 + 9 = 69", "所以 23 × 3 = 69"],
        "tip": "不进位时，十位和个位可以很清楚地分开计算。",
        "check_prompt": "21 × 4 等于多少？",
        "check_answer": "84",
        "check_hint": "先算 20 × 4，再算 1 × 4，最后相加。",
    },
    "multiplication.two_digit_by_one_digit": {
        "concept": "当个位相乘超过 9 时，需要把多出来的十位数进到下一位。",
        "method": ["从个位开始乘", "个位乘积满十，把十位数记作进位", "再算十位，并把进位加进去"],
        "example_title": "例子：28 × 3",
        "example_steps": ["8 × 3 = 24，写 4，进 2", "2 × 3 = 6，再加进位 2，得到 8", "所以 28 × 3 = 84"],
        "tip": "最容易忘的是进位。每次个位乘完，都先问自己：有没有需要进到下一位的数？",
        "check_prompt": "26 × 3 等于多少？",
        "check_answer": "78",
        "check_hint": "6 × 3 = 18，先写 8、进 1；再算十位。",
    },
    "multiplication.three_digit_by_one_digit": {
        "concept": "三位数乘一位数和两位数的方法一样，只是需要继续算到百位。",
        "method": ["从个位开始逐位相乘", "每一位都处理当前进位", "一直算到最高位"],
        "example_title": "例子：124 × 3",
        "example_steps": ["4 × 3 = 12，写 2，进 1", "2 × 3 = 6，加 1 得 7", "1 × 3 = 3", "所以 124 × 3 = 372"],
        "tip": "每一位只做两件事：相乘、加进位。按顺序做，不跳步。",
        "check_prompt": "112 × 3 等于多少？",
        "check_answer": "336",
        "check_hint": "从个位开始：2 × 3，然后十位、百位依次计算。",
    },
}


def lesson_for(skill_id: str, progress: dict) -> dict:
    lesson = dict(LESSONS[skill_id])
    if progress.get("last_error_type") == "carry_error":
        lesson["tip"] = "你最近容易在进位上出错。这次每一步都把进位数字单独写出来，再进入下一位。"
    return lesson
