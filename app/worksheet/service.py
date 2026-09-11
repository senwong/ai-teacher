import json
import uuid
from pathlib import Path
from app.db.sqlite import connect

WORKSHEET_DIR = Path("./data/worksheets")
UPLOAD_DIR = Path("./data/uploads")

def create_worksheet(student_id: int, questions: list[dict], session_id: str | None = None) -> dict:
    worksheet_id = uuid.uuid4().hex[:12]
    with connect() as conn:
        conn.execute("INSERT INTO worksheets(id, student_id, session_id, questions_json, status) VALUES (?, ?, ?, ?, 'created')", (worksheet_id, student_id, session_id, json.dumps(questions, ensure_ascii=False)))
    return get_worksheet(worksheet_id)

def get_worksheet(worksheet_id: str) -> dict | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM worksheets WHERE id = ?", (worksheet_id,)).fetchone()
    if not row: return None
    data = dict(row); data["questions"] = json.loads(data.pop("questions_json"))
    try: data["vision"] = json.loads(data["vision_json"]) if data.get("vision_json") else None
    except json.JSONDecodeError: data["vision"] = None
    return data

def mark_worksheet(worksheet_id: str, status: str, image_path: str | None = None):
    with connect() as conn:
        conn.execute("UPDATE worksheets SET status=?, image_path=COALESCE(?, image_path), updated_at=CURRENT_TIMESTAMP WHERE id=?", (status, image_path, worksheet_id))

def save_vision_result(worksheet_id: str, result: dict, processed_image_path: str | None = None):
    with connect() as conn:
        conn.execute("UPDATE worksheets SET vision_json=?, processed_image_path=COALESCE(?, processed_image_path), updated_at=CURRENT_TIMESTAMP WHERE id=?", (json.dumps(result, ensure_ascii=False), processed_image_path, worksheet_id))

def pdf_path(worksheet_id: str) -> Path:
    WORKSHEET_DIR.mkdir(parents=True, exist_ok=True); return WORKSHEET_DIR / f"{worksheet_id}.pdf"

def upload_path(worksheet_id: str, suffix: str) -> Path:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True); safe = suffix.lower() if suffix.lower() in {".jpg",".jpeg",".png",".webp"} else ".jpg"; return UPLOAD_DIR / f"{worksheet_id}{safe}"

def incoming_upload_path(suffix: str) -> Path:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True); safe = suffix.lower() if suffix.lower() in {".jpg",".jpeg",".png",".webp"} else ".jpg"; return UPLOAD_DIR / f"incoming-{uuid.uuid4().hex[:12]}{safe}"
