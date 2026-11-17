import json
from agentic_exam.exam_package import validate_exam_spec
from agentic_exam.grading import grade_answers


def _spec():
    return {
        "questions": [{
            "id": "QX", "week": 7, "type": "visual_workflow", "prompt": "Arrange agents.",
            "marks": 2,
            "workflow_data": {"components": [
                {"id": "intake", "label": "Intake"},
                {"id": "search", "label": "Search"},
                {"id": "inventory", "label": "Inventory"},
                {"id": "order", "label": "Order"}
            ]}
        }],
        "answer_key": {"QX": {"accepted_stages": [
            ["intake"], ["search", "inventory"], ["order"]
        ]}}
    }


def test_parallel_workflow_spec_validation():
    validate_exam_spec(_spec())


def test_parallel_workflow_full_marks():
    spec = _spec()
    q = spec["questions"][0]
    response = {"stages": [["intake"], ["inventory", "search"], ["order"]]}
    result = grade_answers([q], spec["answer_key"], {"QX": json.dumps(response)})
    assert result["earned"] == 2
    assert result["rows"][0]["correct"] is True


def test_parallel_relationship_is_assessed():
    spec = _spec()
    q = spec["questions"][0]
    # Correct sequential order but fails to put Search and Inventory in parallel.
    response = {"stages": [["intake"], ["search"], ["inventory"], ["order"]]}
    result = grade_answers([q], spec["answer_key"], {"QX": json.dumps(response)})
    assert result["earned"] < 2
    assert result["earned"] > 0
