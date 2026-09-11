from app.db.sqlite import connect


def create_classroom(owner_user_id: int, name: str, grade: int) -> dict:
    name = name.strip()
    if not name:
        raise ValueError("班级名称不能为空")
    if grade < 1 or grade > 12:
        raise ValueError("年级必须在 1 到 12 之间")
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO classrooms(name,grade,owner_user_id) VALUES (?,?,?)",
            (name, grade, owner_user_id),
        )
        row = conn.execute("SELECT * FROM classrooms WHERE id=?", (cur.lastrowid,)).fetchone()
    return dict(row)


def list_classrooms(owner_user_id: int) -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            """SELECT c.*, COUNT(s.id) AS student_count
               FROM classrooms c
               LEFT JOIN students s ON s.classroom_id=c.id
               WHERE c.owner_user_id=?
               GROUP BY c.id
               ORDER BY c.created_at DESC""",
            (owner_user_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_classroom(classroom_id: int) -> dict | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM classrooms WHERE id=?", (classroom_id,)).fetchone()
    return dict(row) if row else None


def get_classroom_for_user(classroom_id: int, user_id: int) -> dict | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM classrooms WHERE id=? AND owner_user_id=?",
            (classroom_id, user_id),
        ).fetchone()
    return dict(row) if row else None


def bootstrap_legacy_students(user_id: int) -> dict | None:
    with connect() as conn:
        user_count = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
        orphan_count = conn.execute("SELECT COUNT(*) AS c FROM students WHERE classroom_id IS NULL").fetchone()["c"]
        if user_count != 1 or orphan_count == 0:
            return None
        cur = conn.execute(
            "INSERT INTO classrooms(name,grade,owner_user_id) VALUES ('历史学生',3,?)",
            (user_id,),
        )
        classroom_id = cur.lastrowid
        conn.execute("UPDATE students SET classroom_id=? WHERE classroom_id IS NULL", (classroom_id,))
        row = conn.execute("SELECT * FROM classrooms WHERE id=?", (classroom_id,)).fetchone()
    return dict(row)
