import base64
import json
import mimetypes
import os
from pathlib import Path


def vision_enabled() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))


def extract_answers(image_path: Path, questions: list[dict]) -> dict[str, str]:
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    from openai import OpenAI

    mime = mimetypes.guess_type(image_path.name)[0] or "image/jpeg"
    encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
    question_desc = [{"id": q["id"], "prompt": q["prompt"]} for q in questions]
    prompt = (
        "Read this photographed elementary-school math worksheet. "
        "Extract only the student's final answer for each listed question. "
        "If an answer is blank or unreadable, use an empty string. "
        "Return strict JSON only, shaped like {\"answers\": {\"q1\": \"72\"}}. "
        f"Questions: {json.dumps(question_desc, ensure_ascii=False)}"
    )

    client = OpenAI(api_key=key)
    response = client.responses.create(
        model=os.getenv("OPENAI_VISION_MODEL", os.getenv("OPENAI_MODEL", "gpt-5.6-luna")),
        input=[{
            "role": "user",
            "content": [
                {"type": "input_text", "text": prompt},
                {"type": "input_image", "image_url": f"data:{mime};base64,{encoded}"},
            ],
        }],
    )
    text = response.output_text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:].strip()
    payload = json.loads(text)
    answers = payload.get("answers", {})
    return {q["id"]: str(answers.get(q["id"], "")).strip() for q in questions}
