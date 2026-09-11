import os
import secrets
import sqlite3
import string
from pathlib import Path

DB_PATH = Path(os.getenv("AI_TEACHER_DB", "./data/ai_teacher.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  email TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  role TEXT NOT NULL DEFAULT 'teacher',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS auth_sessions (
  token_hash TEXT PRIMARY KEY,
  user_id INTEGER NOT NULL,
  expires_at TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS classrooms (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  grade INTEGER NOT NULL DEFAULT 3,
  owner_user_id INTEGER NOT NULL,
  class_code TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS students (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  classroom_id INTEGER,
  name TEXT NOT NULL,
  grade INTEGER NOT NULL DEFAULT 3,
  pin_hash TEXT,
  login_code TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS student_auth_sessions (
  token_hash TEXT PRIMARY KEY,
  student_id INTEGER NOT NULL,
  expires_at TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS learning_sessions (
  id TEXT PRIMARY KEY,
  student_id INTEGER NOT NULL,
  status TEXT NOT NULL DEFAULT 'active',
  lesson_skill_id TEXT,
  started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  ended_at TEXT,
  summary_json TEXT
);
CREATE TABLE IF NOT EXISTS session_messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT NOT NULL,
  student_id INTEGER NOT NULL,
  role TEXT NOT NULL,
  content TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS diagnostic_assessments (
  id TEXT PRIMARY KEY,
  student_id INTEGER NOT NULL,
  questions_json TEXT NOT NULL,
  results_json TEXT,
  status TEXT NOT NULL DEFAULT 'created',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  completed_at TEXT
);
CREATE TABLE IF NOT EXISTS skill_progress (
  student_id INTEGER NOT NULL,
  skill_id TEXT NOT NULL,
  attempts INTEGER NOT NULL DEFAULT 0,
  correct INTEGER NOT NULL DEFAULT 0,
  mastery REAL NOT NULL DEFAULT 0,
  last_error_type TEXT,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (student_id, skill_id)
);
CREATE TABLE IF NOT EXISTS attempts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  student_id INTEGER NOT NULL,
  skill_id TEXT NOT NULL,
  question_json TEXT NOT NULL,
  student_answer TEXT NOT NULL,
  is_correct INTEGER NOT NULL,
  error_type TEXT,
  feedback TEXT,
  worksheet_id TEXT,
  session_id TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS worksheets (
  id TEXT PRIMARY KEY,
  student_id INTEGER NOT NULL,
  session_id TEXT,
  questions_json TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'created',
  image_path TEXT,
  processed_image_path TEXT,
  vision_json TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_classrooms_owner ON classrooms(owner_user_id);
CREATE INDEX IF NOT EXISTS idx_students_classroom ON students(classroom_id);
CREATE INDEX IF NOT EXISTS idx_auth_sessions_user ON auth_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_student_auth_sessions_student ON student_auth_sessions(student_id);
CREATE INDEX IF NOT EXISTS idx_session_messages_session ON session_messages(session_id,id);
"""


def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_column(conn, table: str, column: str, definition: str):
    columns = {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def _new_class_code(conn) -> str:
    alphabet = string.ascii_uppercase + string.digits
    while True:
        code = "".join(secrets.choice(alphabet) for _ in range(6))
        if not conn.execute("SELECT 1 FROM classrooms WHERE class_code=?", (code,)).fetchone():
            return code


def _new_student_login_code(conn) -> str:
    while True:
        code = secrets.token_urlsafe(12)
        if not conn.execute("SELECT 1 FROM students WHERE login_code=?", (code,)).fetchone():
            return code


def init_db():
    with connect() as conn:
        conn.executescript(SCHEMA)
        _ensure_column(conn, "classrooms", "class_code", "TEXT")
        _ensure_column(conn, "students", "classroom_id", "INTEGER")
        _ensure_column(conn, "students", "pin_hash", "TEXT")
        _ensure_column(conn, "students", "login_code", "TEXT")
        _ensure_column(conn, "learning_sessions", "lesson_skill_id", "TEXT")
        _ensure_column(conn, "attempts", "worksheet_id", "TEXT")
        _ensure_column(conn, "attempts", "session_id", "TEXT")
        _ensure_column(conn, "worksheets", "processed_image_path", "TEXT")
        _ensure_column(conn, "worksheets", "vision_json", "TEXT")
        _ensure_column(conn, "worksheets", "session_id", "TEXT")
        for row in conn.execute("SELECT id FROM classrooms WHERE class_code IS NULL OR class_code='' ").fetchall():
            conn.execute("UPDATE classrooms SET class_code=? WHERE id=?", (_new_class_code(conn), row["id"]))
        for row in conn.execute("SELECT id FROM students WHERE login_code IS NULL OR login_code='' ").fetchall():
            conn.execute("UPDATE students SET login_code=? WHERE id=?", (_new_student_login_code(conn), row["id"]))
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_classrooms_code ON classrooms(class_code)")
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_students_login_code ON students(login_code)")


def get_or_create_student(name: str = "Demo Student", grade: int = 3):
    with connect() as conn:
        row = conn.execute("SELECT * FROM students WHERE name = ? LIMIT 1", (name,)).fetchone()
        if row:
            return dict(row)
        cur = conn.execute("INSERT INTO students(name, grade, login_code) VALUES (?, ?, ?)", (name, grade, _new_student_login_code(conn)))
        return dict(conn.execute("SELECT * FROM students WHERE id = ?", (cur.lastrowid,)).fetchone())
