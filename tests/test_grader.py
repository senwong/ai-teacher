from app.assessment.grader import grade


def test_correct_answer():
    q = {"a": 24, "b": 3, "answer": 72}
    result = grade(q, "72")
    assert result["is_correct"] is True
    assert result["error_type"] is None


def test_invalid_answer():
    q = {"a": 24, "b": 3, "answer": 72}
    result = grade(q, "abc")
    assert result["is_correct"] is False
    assert result["error_type"] == "invalid_answer"
