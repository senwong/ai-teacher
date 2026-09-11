import base64
import hashlib
import hmac
import io
import secrets
from datetime import datetime, timedelta, timezone

import qrcode

from app.db.sqlite import connect

STUDENT_SESSION_TTL_DAYS = 30


def _hash_pin(pin: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.scrypt(pin.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return f"scrypt${salt.hex()}${digest.hex()}"


def _verify_pin(pin: str, encoded: str) -> bool:
    try:
        algorithm, salt_hex, digest_hex = encoded.split("$", 2)
        if algorithm != "scrypt":
            return False
        expected = bytes.fromhex(digest_hex)
        actual = hashlib.scrypt(pin.encode("utf-8"), salt=bytes.fromhex(salt_hex), n=2**14, r=8, p=1, dklen=32)
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def generate_pin() -> str:
    return f"{secrets.randbelow(10000):04d}"


def generate_login_code() -> str:
    return secrets.token_urlsafe(12)


def set_student_pin(student_id: int, pin: str) -> None:
    if len(pin) != 4 or not pin.isdigit():
        raise ValueError("学生 PIN 必须是 4 位数字")
    with connect() as conn:
        conn.execute("UPDATE students SET pin_hash=? WHERE id=?", (_hash_pin(pin), student_id))


def authenticate_student(class_code: str, name: str, pin: str) -> dict | None:
    with connect() as conn:
        row = conn.execute(
            """SELECT s.*, c.name AS classroom_name, c.class_code
               FROM students s JOIN classrooms c ON c.id=s.classroom_id
               WHERE UPPER(c.class_code)=UPPER(?) AND s.name=?""",
            (class_code.strip(), name.strip()),
        ).fetchone()
    if not row or not row["pin_hash"] or not _verify_pin(pin.strip(), row["pin_hash"]):
        return None
    return dict(row)


def student_by_login_code(login_code: str) -> dict | None:
    with connect() as conn:
        row = conn.execute(
            """SELECT s.*, c.name AS classroom_name, c.class_code
               FROM students s JOIN classrooms c ON c.id=s.classroom_id
               WHERE s.login_code=?""",
            (login_code.strip(),),
        ).fetchone()
    return dict(row) if row else None


def authenticate_student_by_login_code(login_code: str, pin: str) -> dict | None:
    student = student_by_login_code(login_code)
    if not student or not student.get("pin_hash") or not _verify_pin(pin.strip(), student["pin_hash"]):
        return None
    return student


def qr_data_uri(text: str) -> str:
    image = qrcode.make(text)
    output = io.BytesIO()
    image.save(output, format="PNG")
    encoded = base64.b64encode(output.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def create_student_session(student_id: int) -> str:
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    expires_at = (datetime.now(timezone.utc) + timedelta(days=STUDENT_SESSION_TTL_DAYS)).isoformat()
    with connect() as conn:
        conn.execute("INSERT INTO student_auth_sessions(token_hash,student_id,expires_at) VALUES (?,?,?)", (token_hash, student_id, expires_at))
    return token


def student_from_session(token: str | None) -> dict | None:
    if not token:
        return None
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    with connect() as conn:
        row = conn.execute(
            """SELECT s.*, c.name AS classroom_name, c.class_code, a.expires_at
               FROM student_auth_sessions a
               JOIN students s ON s.id=a.student_id
               JOIN classrooms c ON c.id=s.classroom_id
               WHERE a.token_hash=?""",
            (token_hash,),
        ).fetchone()
    if not row:
        return None
    try:
        expires = datetime.fromisoformat(row["expires_at"])
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires <= datetime.now(timezone.utc):
            destroy_student_session(token)
            return None
    except ValueError:
        return None
    return dict(row)


def destroy_student_session(token: str | None) -> None:
    if not token:
        return
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    with connect() as conn:
        conn.execute("DELETE FROM student_auth_sessions WHERE token_hash=?", (token_hash,))
