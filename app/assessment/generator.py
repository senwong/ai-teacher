import random


def generate_questions(count: int = 5):
    questions = []
    for i in range(count):
        a = random.randint(12, 49)
        b = random.randint(2, 9)
        questions.append({
            "id": f"q{i+1}",
            "type": "calculation",
            "prompt": f"{a} × {b} = ?",
            "a": a,
            "b": b,
            "answer": a * b,
            "skill_id": "multiplication.two_digit_by_one_digit",
        })
    return questions
