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
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with connect() as conn:
        conn.executescript(SCHEMA)


def get_or_create_student(name: str = "Demo Student", grade: int = 3):
    with connect() as conn:
        row = conn.execute("SELECT * FROM students WHERE name = ? LIMIT 1", (name,)).fetchone()
        if row:
            return dict(row)
        cur = conn.execute("INSERT INTO students(name, grade) VALUES (?, ?)", (name, grade))
        return dict(conn.execute("SELECT * FROM students WHERE id = ?", (cur.lastrowid,)).fetchone())
