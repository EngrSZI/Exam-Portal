import re
import json

def normalize(value):
    value = str(value or "").strip().casefold()
    value = re.sub(r"\s+", " ", value)
    return value

def _manual_answer_grade(question, response):
    """
    Produce a suggested score for a short answer using instructor-authored rubric rules.
    This is deterministic keyword/rule matching, not an LLM judgment. Instructor can adjust.
    Question may define:
      accepted_answers: list of exact accepted answers
      rubric: [{"keywords": ["retrieval", "context"], "marks": 1, "label": "..."}]
      partial_credit: {"minimum_keywords": 2, "marks": 1}
    """
    text = normalize(response)
    max_marks = float(question.get("marks", 1))
    accepted = question.get("accepted_answers", [])
    if isinstance(accepted, str):
        accepted = [accepted]
    if text and any(text == normalize(a) for a in accepted):
        return max_marks, "Exact accepted answer matched", True

    rubric = question.get("rubric", [])
    awarded = 0.0
    matched = []
    for rule in rubric:
        kws = [normalize(k) for k in rule.get("keywords", [])]
        if kws and all(k in text for k in kws):
            mark = float(rule.get("marks", 0))
            awarded += mark
            matched.append(rule.get("label") or ", ".join(kws))
    awarded = min(max_marks, awarded)

    partial = question.get("partial_credit", {})
    if partial and not rubric:
        kws = [normalize(k) for k in partial.get("keywords", [])]
        hits = sum(1 for k in kws if k and k in text)
        minimum = int(partial.get("minimum_keywords", 1))
        if hits >= minimum:
            awarded = min(max_marks, float(partial.get("marks", max_marks)))
            matched = [f"{hits} rubric keywords matched"]

    if not text:
        return 0.0, "No answer provided", False
    if matched:
        return awarded, "Matched rubric: " + "; ".join(matched), False
    return 0.0, "No rubric rule matched; instructor review recommended", False

def grade_answers(questions, answer_key, answers):
    rows, total, earned = [], 0.0, 0.0
    for q in questions:
        qid = q["id"]
        max_marks = float(q.get("marks", 1))
        total += max_marks
        qtype = q["type"]
        response = answers.get(qid, "")
        correct = None
        awarded = 0.0
        note = ""
        if qtype == "multiple_select":
            try:
                submitted_value = json.loads(response) if isinstance(response, str) else response
            except (ValueError, TypeError):
                submitted_value = []
            if not isinstance(submitted_value, list):
                submitted_value = []
            expected_value = answer_key.get(qid, q.get("answer", []))
            if not isinstance(expected_value, list):
                expected_value = []
            submitted = set(map(str, submitted_value))
            expected = set(map(str, expected_value))
            correct_count = len(submitted & expected)
            incorrect_count = len(submitted - expected)
            missing_count = len(expected - submitted)
            raw_score = max(0, correct_count - incorrect_count)
            awarded = max_marks * raw_score / len(expected) if expected else 0.0
            awarded = min(max_marks, awarded)
            correct = submitted == expected
            note = (
                f"Correct selections: {correct_count}; incorrect selections: "
                f"{incorrect_count}; missed correct selections: {missing_count}"
            )
        elif qtype == "visual_workflow":
            try:
                submitted = json.loads(response) if isinstance(response, str) else (response or {})
            except (ValueError, TypeError):
                submitted = {}
            expected = answer_key.get(qid, q.get("answer_key", {}))
            submitted_stages = submitted.get("stages", []) if isinstance(submitted, dict) else []
            if not submitted_stages and isinstance(submitted, dict):
                submitted_stages = [[x] for x in submitted.get("order", [])]
            expected_stages = expected.get("accepted_stages", []) if isinstance(expected, dict) else []
            if expected_stages:
                # Compare every pair of agents: same stage means parallel; lower stage index means prerequisite.
                # This makes ordering and parallel grouping independently assessable.
                def stage_map(stages):
                    return {str(agent): i for i, stage in enumerate(stages)
                            for agent in stage if isinstance(stage, list)}
                submitted_map = stage_map(submitted_stages)
                expected_map = stage_map(expected_stages)
                component_ids = [str(c.get("id")) for c in q.get("workflow_data", {}).get("components", [])]
                pair_total = 0
                pair_correct = 0
                for i, left in enumerate(component_ids):
                    for right in component_ids[i + 1:]:
                        pair_total += 1
                        if left not in expected_map or right not in expected_map:
                            continue
                        expected_relation = (
                            "parallel" if expected_map[left] == expected_map[right]
                            else ("before" if expected_map[left] < expected_map[right] else "after")
                        )
                        if left not in submitted_map or right not in submitted_map:
                            continue
                        submitted_relation = (
                            "parallel" if submitted_map[left] == submitted_map[right]
                            else ("before" if submitted_map[left] < submitted_map[right] else "after")
                        )
                        if submitted_relation == expected_relation:
                            pair_correct += 1
                awarded = max_marks * pair_correct / pair_total if pair_total else 0.0
                correct = pair_total > 0 and pair_correct == pair_total
                note = f"Correct agent ordering/parallel relationships: {pair_correct}/{pair_total}"
            else:
                expected_order = expected.get("accepted_order", []) if isinstance(expected, dict) else []
                expected_edges = expected.get("required_edges", []) if isinstance(expected, dict) else []
                submitted_order = submitted.get("order", []) if isinstance(submitted, dict) else []
                submitted_edges = submitted.get("edges", []) if isinstance(submitted, dict) else []
                components = {c.get("id"): c for c in q.get("workflow_data", {}).get("components", [])}
                placement_points = sum(float(components.get(cid, {}).get("points", 1)) for i, cid in enumerate(submitted_order) if i < len(expected_order) and cid == expected_order[i])
                total_placement_points = sum(float(components.get(cid, {}).get("points", 1)) for cid in expected_order)
                norm_edges = {(str(e.get("from")), str(e.get("to"))) for e in submitted_edges if isinstance(e, dict)}
                required = {(str(e.get("from")), str(e.get("to"))) for e in expected_edges if isinstance(e, dict)}
                edge_points = len(norm_edges & required)
                raw_points = placement_points + edge_points
                raw_total = total_placement_points + len(required)
                awarded = max_marks * raw_points / raw_total if raw_total else 0.0
                correct = raw_total > 0 and raw_points == raw_total
                note = f"Component placement: {placement_points:g}/{total_placement_points:g}; required connections: {edge_points}/{len(required)}"
        elif qtype == "short_answer":
            awarded, note, exact = _manual_answer_grade(q, response)
            correct = exact if exact else None
        elif qtype == "matching":
            expected = answer_key.get(qid, q.get("answer", {}))
            if isinstance(expected, dict):
                def parse_match(s):
                    pairs = {}
                    for item in str(s).split(";"):
                        if "=" in item:
                            k, v = item.split("=", 1)
                            pairs[normalize(k)] = normalize(v)
                    return pairs
                parsed = parse_match(response)
                expected_norm = {normalize(k): normalize(v) for k, v in expected.items()}
                correct_count = sum(1 for k, v in expected_norm.items() if parsed.get(k) == v)
                correct = len(expected_norm) > 0 and correct_count == len(expected_norm)
                awarded = max_marks * correct_count / max(1, len(expected_norm))
                note = f"{correct_count}/{len(expected_norm)} matches correct"
            else:
                correct = normalize(response) == normalize(expected)
                awarded = max_marks if correct else 0.0
        elif qtype == "fill_blank":
            expected = answer_key.get(qid, q.get("answer", ""))
            alternatives = expected if isinstance(expected, list) else [expected]
            correct = any(normalize(response) == normalize(x) for x in alternatives)
            awarded = max_marks if correct else 0.0
            if not correct:
                note = "No accepted answer matched; instructor may adjust"
        else:
            expected = answer_key.get(qid, q.get("answer", ""))
            correct = normalize(response) == normalize(expected)
            awarded = max_marks if correct else 0.0
            if not correct:
                note = "Answer did not match key; instructor may adjust"
        awarded = min(max_marks, max(0.0, float(awarded)))
        earned += awarded
        rows.append({
            "id": qid, "week": q.get("week"), "prompt": q.get("prompt", ""),
            "response": response, "correct": correct, "marks": awarded,
            "max_marks": max_marks, "type": qtype, "grading_note": note,
            "adjusted": False
        })
    return {"rows": rows, "earned": earned, "total": total}
