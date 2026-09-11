def classify_error(a: int, b: int, student_answer: int | None):
    if student_answer is None:
        return "invalid_answer"
    correct = a * b
    if student_answer == correct:
        return None
    ones_product = (a % 10) * b
    if ones_product >= 10 and abs(student_answer - correct) in {10, 20, 30, 40}:
        return "carry_error"
    return "calculation_error"


def grade(question: dict, raw_answer: str):
    try:
        student_answer = int(raw_answer.strip())
    except Exception:
        student_answer = None
    correct_answer = question["answer"]
    is_correct = student_answer == correct_answer
    error_type = classify_error(question["a"], question["b"], student_answer)
    return {
        "student_answer": student_answer,
        "correct_answer": correct_answer,
        "is_correct": is_correct,
        "error_type": error_type,
    }
