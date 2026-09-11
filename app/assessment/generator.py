import random


def generate_questions(count: int = 5, skill_id: str = "multiplication.two_digit_by_one_digit"):
    questions = []
    for i in range(count):
        if skill_id == "multiplication.one_digit_facts":
            a, b = random.randint(2, 9), random.randint(2, 9)
        elif skill_id == "multiplication.two_digit_no_carry":
            b = random.randint(2, 4)
            tens = random.randint(1, 4)
            ones = random.randint(1, max(1, 9 // b))
            a = tens * 10 + ones
        elif skill_id == "multiplication.three_digit_by_one_digit":
            a, b = random.randint(101, 499), random.randint(2, 9)
        else:
            a, b = random.randint(12, 49), random.randint(2, 9)
        questions.append({
            "id": f"q{i+1}",
            "type": "calculation",
            "prompt": f"{a} × {b} = ?",
            "a": a,
            "b": b,
            "answer": a * b,
            "skill_id": skill_id,
        })
    return questions
