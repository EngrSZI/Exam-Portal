import json

from agentic_exam.exam_package import validate_exam_spec
from agentic_exam.grading import grade_answers


def make_question():
    return {
        "id": "Q36",
        "week": 3,
        "type": "multiple_select",
        "prompt": "Select all required agents.",
        "marks": 5,
        "options": [{"id": x, "text": f"Agent {x}"} for x in "ABCDE"],
    }


def test_validate_multiple_select_question():
    spec = {
        "questions": [make_question()],
        "answer_key": {"Q36": ["A", "B", "C"]},
    }
    validate_exam_spec(spec)


def test_multiple_select_full_marks():
    q = make_question()
    result = grade_answers([q], {"Q36": ["A", "B", "C"]},
                           {"Q36": json.dumps(["A", "B", "C"])})
    assert result["earned"] == 5


def test_multiple_select_partial_credit_and_penalty():
    q = make_question()
    result = grade_answers([q], {"Q36": ["A", "B", "C"]},
                           {"Q36": json.dumps(["A", "B", "D"])})
    assert abs(result["earned"] - (5 * (1 / 3))) < 1e-9


def test_multiple_select_empty_answer():
    q = make_question()
    result = grade_answers([q], {"Q36": ["A", "B", "C"]}, {})
    assert result["earned"] == 0


def test_multiple_select_rejects_unknown_answer_key_option():
    spec = {
        "questions": [make_question()],
        "answer_key": {"Q36": ["A", "Z"]},
    }
    try:
        validate_exam_spec(spec)
    except ValueError as exc:
        assert "unknown option IDs" in str(exc)
    else:
        raise AssertionError("Expected invalid answer key to be rejected")
