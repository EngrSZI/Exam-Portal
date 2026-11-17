
import json, zipfile, tempfile, os
from pathlib import Path
from .crypto_utils import encrypt_password_payload, decrypt_password_payload

def create_exam_package(json_path, output_path, exam_password):
    json_path = Path(json_path).resolve()
    spec = json.loads(json_path.read_text(encoding="utf-8"))
    validate_exam_spec(spec)
    root = json_path.parent
    public_questions = {k: v for k, v in spec.items() if k != "answer_key"}
    # Keep the answer key out of the student package entirely.
    # Instructor grading uses the original JSON file, which must remain instructor-only.
    student_questions = []
    for q in public_questions["questions"]:
        safe_q = {k: v for k, v in q.items() if k not in {"answer", "explanation"}}
        student_questions.append(safe_q)
    public_questions["questions"] = student_questions
    payload = json.dumps({"exam": public_questions},
                         ensure_ascii=False).encode("utf-8")
    encrypted = encrypt_password_payload(payload, exam_password)
    # The student app receives only the question set after the password is accepted.
    # The answer key is not returned by the student app; instructor grading uses the source JSON.
    # The package's password encryption is for access control, not a guarantee against a skilled local user.
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("exam.enc", encrypted)
        for q in spec["questions"]:
            for rel in [q.get("image")] + [o.get("image") for o in q.get("options", [])]:
                if rel:
                    # Embedded images are already stored in the encrypted exam JSON.
                    # Do not interpret data URIs as filesystem paths.
                    if isinstance(rel, str) and rel.startswith("data:image/"):
                        continue
                    p = (root / rel).resolve()
                    if not p.exists() or not p.is_file():
                        raise FileNotFoundError(f"Image not found: {rel} (expected {p})")
                    arc = "assets/" + Path(rel).name
                    z.write(p, arcname=arc)
        # Source exam is included only to let instructor recover the key after collection;
        # do not distribute this source JSON to students.
        z.writestr("package_info.json", json.dumps({"format_version": 1}))
    return output_path

def open_exam_package(path, password, temp_dir):
    with zipfile.ZipFile(path, "r") as z:
        blob = z.read("exam.enc")
        decoded = json.loads(decrypt_password_payload(blob, password).decode("utf-8"))
        assets_dir = Path(temp_dir) / "assets"
        assets_dir.mkdir(parents=True, exist_ok=True)
        for name in z.namelist():
            if name.startswith("assets/") and not name.endswith("/"):
                out = assets_dir / Path(name).name
                out.write_bytes(z.read(name))
        exam = decoded["exam"]
        # Store the public key at a deterministic path inside the extracted package directory.
        pub = Path(temp_dir) / "instructor_public.pem"
        if "instructor_public.pem" in z.namelist():
            pub.write_bytes(z.read("instructor_public.pem"))
            exam["_public_key_path"] = str(pub)
        else:
            exam["_public_key_path"] = ""
        # Map bundled asset filenames to extracted local paths.
        for q in exam["questions"]:
            if q.get("image") and not (
                isinstance(q["image"], str) and q["image"].startswith("data:image/")
            ):
                q["image"] = str(assets_dir / Path(q["image"]).name)
            for opt in q.get("options", []):
                if opt.get("image") and not (
                    isinstance(opt["image"], str) and opt["image"].startswith("data:image/")
                ):
                    opt["image"] = str(assets_dir / Path(opt["image"]).name)
        return exam

def validate_exam_spec(spec):
    if not isinstance(spec, dict) or not isinstance(spec.get("questions"), list) or not spec["questions"]:
        raise ValueError("Exam JSON must contain a non-empty questions array.")
    seen = set()
    allowed = {"mcq", "image_mcq", "true_false", "multiple_select", "fill_blank", "matching", "short_answer", "visual_workflow"}
    for q in spec["questions"]:
        for key in ("id", "week", "type", "prompt", "marks"):
            if key not in q:
                raise ValueError(f"Question is missing required field: {key}")
        if q["id"] in seen:
            raise ValueError(f"Duplicate question ID: {q['id']}")
        seen.add(q["id"])
        if q["type"] not in allowed:
            raise ValueError(f"Unsupported question type: {q['type']}")
        if q["type"] in {"mcq", "image_mcq"} and len(q.get("options", [])) < 2:
            raise ValueError(f"{q['id']} needs at least two options.")
        if q["type"] == "multiple_select":
            options = q.get("options", [])
            if not isinstance(options, list) or len(options) < 2:
                raise ValueError(f"{q['id']} needs at least two options.")
            option_ids = []
            for option in options:
                if not isinstance(option, dict) or "id" not in option or "text" not in option:
                    raise ValueError(f"{q['id']} has an invalid multiple-select option.")
                option_ids.append(str(option["id"]))
            if len(option_ids) != len(set(option_ids)):
                raise ValueError(f"{q['id']} contains duplicate option IDs.")
            answer_key = spec.get("answer_key", {}).get(q["id"])
            if answer_key is not None:
                if not isinstance(answer_key, list) or not answer_key:
                    raise ValueError(f"{q['id']} answer_key must be a non-empty list.")
                unknown = set(map(str, answer_key)) - set(option_ids)
                if unknown:
                    raise ValueError(f"{q['id']} answer_key contains unknown option IDs: {sorted(unknown)}")

        if q["type"] == "visual_workflow":
            workflow = q.get("workflow_data", {})
            components = workflow.get("components", []) if isinstance(workflow, dict) else []
            if not isinstance(components, list) or len(components) < 2:
                raise ValueError(f"{q['id']} needs at least two workflow components.")
            component_ids = []
            for component in components:
                if not isinstance(component, dict) or not component.get("id") or not component.get("label"):
                    raise ValueError(f"{q['id']} has an invalid workflow component.")
                component_ids.append(str(component["id"]))
            if len(component_ids) != len(set(component_ids)):
                raise ValueError(f"{q['id']} contains duplicate workflow component IDs.")
            workflow_key = spec.get("answer_key", {}).get(q["id"], {})
            if isinstance(workflow_key, dict) and "accepted_stages" in workflow_key:
                stages = workflow_key["accepted_stages"]
                if not isinstance(stages, list) or not stages or any(not isinstance(stage, list) or not stage for stage in stages):
                    raise ValueError(f"{q['id']} accepted_stages must be a non-empty list of non-empty lists.")
                flattened = [str(agent_id) for stage in stages for agent_id in stage]
                if len(flattened) != len(set(flattened)):
                    raise ValueError(f"{q['id']} repeats an agent in accepted_stages.")
                unknown = set(flattened) - set(component_ids)
                missing = set(component_ids) - set(flattened)
                if unknown or missing:
                    raise ValueError(f"{q['id']} accepted_stages must include every component exactly once; unknown={sorted(unknown)}, missing={sorted(missing)}")
