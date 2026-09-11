import tempfile
from pathlib import Path


def _reset_db(tmp: str):
    import app.db.sqlite as db
    db.DB_PATH = Path(tmp) / "test.db"
    db.init_db()


def _disable_ai(monkeypatch):
    for key in (
        "AI_API_KEY", "OPENAI_API_KEY", "DEEPSEEK_API_KEY", "AI_BASE_URL",
    ):
        monkeypatch.delenv(key, raising=False)


def _student_fixture():
    from app.auth.service import create_user
    from app.classroom.service import create_classroom
    from app.session.service import create_session
    from app.student.access import create_student_session
    from app.student.service import create_student

    teacher = create_user("老师", "teacher@example.com", "password123")
    classroom = create_classroom(teacher["id"], "三年级一班", 3)
    student = create_student("小明", 3, classroom["id"])
    session = create_session(student["id"])
    token = create_student_session(student["id"])
    return student, session, token


def test_session_chat_persists_messages(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        _reset_db(tmp)
        _disable_ai(monkeypatch)

        from app.chat.service import list_messages
        from app.main import STUDENT_COOKIE_NAME, app
        from fastapi.testclient import TestClient

        student, session, token = _student_fixture()
        client = TestClient(app)
        client.cookies.set(STUDENT_COOKIE_NAME, token)
        response = client.post(
            "/learn/chat",
            data={"session_id": session["id"], "message": "为什么乘法表示重复相加？"},
        )
        assert response.status_code == 200
        assert response.json()["answer"]

        messages = list_messages(session["id"])
        assert [item["role"] for item in messages] == ["student", "teacher"]
        assert messages[0]["content"] == "为什么乘法表示重复相加？"


def test_websocket_chat_persists_messages(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        _reset_db(tmp)
        _disable_ai(monkeypatch)

        from app.chat.service import list_messages
        from app.main import STUDENT_COOKIE_NAME, app
        from fastapi.testclient import TestClient

        student, session, token = _student_fixture()
        client = TestClient(app)
        client.cookies.set(STUDENT_COOKIE_NAME, token)

        with client.websocket_connect(f"/ws/learn/chat?session_id={session['id']}") as websocket:
            connected = websocket.receive_json()
            assert connected["type"] == "connected"
            websocket.send_json({"type": "chat", "message": "为什么乘法表示重复相加？"})
            assert websocket.receive_json()["type"] == "thinking"
            answer = websocket.receive_json()
            assert answer["type"] == "answer"
            assert answer["answer"]
            assert answer["practice_mode"] is False

        messages = list_messages(session["id"])
        assert [item["role"] for item in messages] == ["student", "teacher"]
        assert messages[0]["student_id"] == student["id"]


def test_practice_chat_fallback_does_not_reveal_final_answer(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        _reset_db(tmp)
        _disable_ai(monkeypatch)

        import app.main as main
        from fastapi.testclient import TestClient

        student, session, token = _student_fixture()
        main.SESSIONS[session["id"]] = [
            {"id": "q1", "prompt": "6 × 7 = ?", "skill_id": "multiplication.one_digit_facts"}
        ]

        client = TestClient(main.app)
        client.cookies.set(main.STUDENT_COOKIE_NAME, token)
        response = client.post(
            "/learn/chat",
            data={"session_id": session["id"], "message": "答案是多少？"},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["practice_mode"] is True
        assert "不直接" in payload["answer"]
        assert "42" not in payload["answer"]
        main.SESSIONS.pop(session["id"], None)


def test_practice_websocket_does_not_reveal_final_answer(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        _reset_db(tmp)
        _disable_ai(monkeypatch)

        import app.main as main
        from fastapi.testclient import TestClient

        student, session, token = _student_fixture()
        main.SESSIONS[session["id"]] = [
            {"id": "q1", "prompt": "6 × 7 = ?", "skill_id": "multiplication.one_digit_facts"}
        ]

        client = TestClient(main.app)
        client.cookies.set(main.STUDENT_COOKIE_NAME, token)
        with client.websocket_connect(f"/ws/learn/chat?session_id={session['id']}") as websocket:
            assert websocket.receive_json()["type"] == "connected"
            websocket.send_json({"type": "chat", "message": "答案是多少？"})
            assert websocket.receive_json()["type"] == "thinking"
            payload = websocket.receive_json()
            assert payload["type"] == "answer"
            assert payload["practice_mode"] is True
            assert "不直接" in payload["answer"]
            assert "42" not in payload["answer"]

        main.SESSIONS.pop(session["id"], None)


def test_learning_page_has_websocket_voice_input_and_tts_controls():
    template = Path("app/templates/index.html").read_text()
    script = Path("app/static/learning_chat.js").read_text()

    assert "/ws/learn/chat" in script
    assert "new WebSocket" in script
    assert "type: 'chat'" in script
    assert "fetch('/learn/chat'" not in script
    assert "SpeechRecognition" in script
    assert "webkitSpeechRecognition" in script
    assert "speechSynthesis" in script
    assert "SpeechSynthesisUtterance" in script
    assert "自动朗读老师讲解" in template
    assert "data-mic-button" in template
    assert "data-chat-form" in template
    assert "练习中我会给你提示" not in template
    assert "不会直接告诉当前题答案" in template
