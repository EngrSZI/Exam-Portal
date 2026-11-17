
from agentic_exam.grading import grade_answers

def test_mcq_correct_and_wrong():
    qs = [
        {"id":"a","week":1,"type":"mcq","prompt":"x","marks":1},
        {"id":"b","week":1,"type":"mcq","prompt":"y","marks":2}
    ]
    result = grade_answers(qs, {"a":"A","b":"B"}, {"a":"A","b":"C"})
    assert result["earned"] == 1
    assert result["total"] == 3

def test_short_answer_manual():
    qs = [{"id":"s","week":7,"type":"short_answer","prompt":"x","marks":2}]
    result = grade_answers(qs, {}, {"s":"because retrieval matters"})
    assert result["rows"][0]["correct"] is None
