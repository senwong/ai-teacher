SKILLS = {
    "multiplication.one_digit_facts": {
        "title": "一位数乘法基础",
        "grade": 3,
        "objective": "熟练掌握 2~9 的基础乘法，为多位数乘法做准备。",
        "mastery_threshold": 0.80,
        "minimum_attempts": 5,
        "prerequisites": [],
        "explanation": "先把一位数乘法算准，再追求速度。可以把乘法理解成相同数量的重复相加。",
    },
    "multiplication.two_digit_no_carry": {
        "title": "两位数乘一位数（不进位）",
        "grade": 3,
        "objective": "理解十位和个位分别乘一位数，并正确合并结果。",
        "mastery_threshold": 0.80,
        "minimum_attempts": 5,
        "prerequisites": ["multiplication.one_digit_facts"],
        "explanation": "把两位数拆成几十和几个分别相乘，再把两个结果加起来。先练不需要进位的题。",
    },
    "multiplication.two_digit_by_one_digit": {
        "title": "两位数乘一位数（进位）",
        "grade": 3,
        "objective": "理解两位数乘一位数的竖式计算，并正确处理进位。",
        "mastery_threshold": 0.80,
        "minimum_attempts": 5,
        "prerequisites": ["multiplication.two_digit_no_carry"],
        "explanation": "做竖式时从个位开始，个位乘积满十时，把十位数字进到下一位，再继续计算。",
    },
    "multiplication.three_digit_by_one_digit": {
        "title": "三位数乘一位数",
        "grade": 3,
        "objective": "把两位数乘法的方法迁移到三位数，正确处理连续进位。",
        "mastery_threshold": 0.80,
        "minimum_attempts": 5,
        "prerequisites": ["multiplication.two_digit_by_one_digit"],
        "explanation": "从个位开始逐位相乘并处理进位。每一位都写清楚，避免漏掉进位。",
    },
}

ROADMAP = list(SKILLS.keys())
DEFAULT_SKILL_ID = ROADMAP[0]
