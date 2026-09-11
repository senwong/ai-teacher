import os
import sqlite3
from pathlib import Path

DB_PATH = Path(os.getenv("AI_TEACHER_DB", "./data/ai_teacher.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS students (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  grade INTEGER NOT NULL DEFAULT 3,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS learning_sessions (
  id TEXT PRIMARY KEY,
  student_id INTEGER NOT NULL,
  status TEXT NOT NULL DEFAULT 'active',
  started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  ended_at TEXT,
  summary_json TEXT
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

def init_db():
    with connect() as conn:
        conn.executescript(SCHEMA)
        _ensure_column(conn, "attempts", "worksheet_id", "TEXT")
        _ensure_column(conn, "attempts", "session_id", "TEXT")
        _ensure_column(conn, "worksheets", "processed_image_path", "TEXT")
        _ensure_column(conn, "worksheets", "vision_json", "TEXT")
        _ensure_column(conn, "worksheets", "session_id", "TEXT")

def get_or_create_student(name: str = "Demo Student", grade: int = 3):
    with connect() as conn:
        row = conn.execute("SELECT * FROM students WHERE name = ? LIMIT 1", (name,)).fetchone()
        if row:
            return dict(row)
        cur = conn.execute("INSERT INTO students(name, grade) VALUES (?, ?)", (name, grade))
        return dict(conn.execute("SELECT * FROM students WHERE id = ?", (cur.lastrowid,)).fetchone())
