import base64
import json
import mimetypes
from pathlib import Path

from app.llm.provider import client, enabled, vision_model


def vision_enabled() -> bool:
    return enabled()


def _clean_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:].strip()
    return json.loads(text)


def extract_submission(image_path: Path, questions: list[dict]) -> dict:
    if not enabled():
        raise RuntimeError("AI_API_KEY is not configured")

    mime = mimetypes.guess_type(image_path.name)[0] or "image/jpeg"
    encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
    question_desc = [{"id": q["id"], "prompt": q["prompt"]} for q in questions]
    prompt = (
        "You are reading a photographed elementary-school math worksheet. "
        "For every listed question, inspect both the final answer and the handwritten work area. "
        "Return strict JSON only. Do not grade correctness. Do not invent unreadable writing. "
        "Use this exact shape: "
        '{"answers":{"q1":{"final_answer":"72","work_steps":["24 x 3","72"],'
        '"confidence":0.95,"error_hint":""}}}. '
        "confidence must be a number from 0 to 1. If blank or unreadable, use an empty final_answer, "
        "an empty work_steps list, low confidence, and a short error_hint such as 'unreadable'. "
        f"Questions: {json.dumps(question_desc, ensure_ascii=False)}"
    )

    response = client().responses.create(
        model=vision_model(),
        input=[{
            "role": "user",
            "content": [
                {"type": "input_text", "text": prompt},
                {"type": "input_image", "image_url": f"data:{mime};base64,{encoded}"},
            ],
        }],
    )
    payload = _clean_json(response.output_text)
    raw_answers = payload.get("answers", {})
    answers = {}
    for q in questions:
        raw = raw_answers.get(q["id"], {})
        if isinstance(raw, str):
            raw = {"final_answer": raw}
        confidence = raw.get("confidence", 0)
        try:
            confidence = max(0.0, min(1.0, float(confidence)))
        except (TypeError, ValueError):
            confidence = 0.0
        answers[q["id"]] = {
            "final_answer": str(raw.get("final_answer", "")).strip(),
            "work_steps": [str(step).strip() for step in raw.get("work_steps", []) if str(step).strip()],
            "confidence": confidence,
            "error_hint": str(raw.get("error_hint", "")).strip(),
        }
    return {"answers": answers}


def extract_answers(image_path: Path, questions: list[dict]) -> dict[str, str]:
    submission = extract_submission(image_path, questions)
    return {qid: item["final_answer"] for qid, item in submission["answers"].items()}
