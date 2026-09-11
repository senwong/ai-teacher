import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from app.db.sqlite import connect

SESSION_TTL_DAYS = 30


def _hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return f"scrypt${salt.hex()}${digest.hex()}"


def _verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, salt_hex, digest_hex = encoded.split("$", 2)
        if algorithm != "scrypt":
            return False
        expected = bytes.fromhex(digest_hex)
        actual = hashlib.scrypt(password.encode("utf-8"), salt=bytes.fromhex(salt_hex), n=2**14, r=8, p=1, dklen=32)
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def create_user(name: str, email: str, password: str) -> dict:
    name = name.strip()
    email = email.strip().lower()
    if not name:
        raise ValueError("教师姓名不能为空")
    if "@" not in email:
        raise ValueError("请输入有效邮箱")
    if len(password) < 8:
        raise ValueError("密码至少需要 8 位")
    with connect() as conn:
        if conn.execute("SELECT 1 FROM users WHERE email=?", (email,)).fetchone():
            raise ValueError("该邮箱已注册")
        cur = conn.execute(
            "INSERT INTO users(name,email,password_hash,role) VALUES (?,?,?,'teacher')",
            (name, email, _hash_password(password)),
        )
        row = conn.execute("SELECT id,name,email,role,created_at FROM users WHERE id=?", (cur.lastrowid,)).fetchone()
    return dict(row)


def authenticate(email: str, password: str) -> dict | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE email=?", (email.strip().lower(),)).fetchone()
    if not row or not _verify_password(password, row["password_hash"]):
        return None
    return {k: row[k] for k in ("id", "name", "email", "role", "created_at")}


def create_login_session(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    expires_at = (datetime.now(timezone.utc) + timedelta(days=SESSION_TTL_DAYS)).isoformat()
    with connect() as conn:
        conn.execute("INSERT INTO auth_sessions(token_hash,user_id,expires_at) VALUES (?,?,?)", (token_hash, user_id, expires_at))
    return token


def user_from_session(token: str | None) -> dict | None:
    if not token:
        return None
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    with connect() as conn:
        row = conn.execute(
            """SELECT u.id,u.name,u.email,u.role,u.created_at,s.expires_at
               FROM auth_sessions s JOIN users u ON u.id=s.user_id
               WHERE s.token_hash=?""",
            (token_hash,),
        ).fetchone()
    if not row:
        return None
    try:
        expires = datetime.fromisoformat(row["expires_at"])
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires <= datetime.now(timezone.utc):
            destroy_login_session(token)
            return None
    except ValueError:
        return None
    return {k: row[k] for k in ("id", "name", "email", "role", "created_at")}


def destroy_login_session(token: str | None):
    if not token:
        return
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    with connect() as conn:
        conn.execute("DELETE FROM auth_sessions WHERE token_hash=?", (token_hash,))
