from fastapi import WebSocket, WebSocketDisconnect
from starlette.concurrency import run_in_threadpool

from app.agent.teacher import teacher_snapshot
from app.chat.service import list_messages, save_message, teacher_chat_answer
from app.review.service import learning_plan_for_student
from app.session.service import get_session
from app.student.access import student_from_session


def register_websocket_chat(app, sessions: dict[str, list[dict]], student_cookie_name: str) -> None:
    @app.websocket("/ws/learn/chat")
    async def learning_chat_socket(websocket: WebSocket):
        token = websocket.cookies.get(student_cookie_name)
        student = student_from_session(token)
        if not student:
            await websocket.close(code=4401, reason="Student authentication required")
            return

        session_id = (websocket.query_params.get("session_id") or "").strip()
        session = get_session(session_id) if session_id else None
        if not session or session["student_id"] != student["id"]:
            await websocket.close(code=4404, reason="Learning session not found")
            return

        await websocket.accept()
        await websocket.send_json({"type": "connected", "session_id": session_id})

        try:
            while True:
                payload = await websocket.receive_json()
                event_type = payload.get("type", "chat")

                if event_type == "ping":
                    await websocket.send_json({"type": "pong"})
                    continue
                if event_type != "chat":
                    await websocket.send_json({"type": "error", "detail": "Unsupported event type"})
                    continue

                question = str(payload.get("message", "")).strip()
                if not question:
                    await websocket.send_json({"type": "error", "detail": "请输入问题"})
                    continue
                if len(question) > 500:
                    await websocket.send_json({"type": "error", "detail": "问题太长了，请简短一些"})
                    continue

                await websocket.send_json({"type": "thinking"})

                plan = learning_plan_for_student(student["id"])
                snapshot = teacher_snapshot(plan["skill_id"], plan["progress"])
                active_questions = sessions.get(session_id, [])
                history = list_messages(session_id, limit=12)
                student_message = save_message(session_id, student["id"], "student", question)

                answer = await run_in_threadpool(
                    teacher_chat_answer,
                    question=question,
                    student=student,
                    skill=plan["skill"],
                    progress=plan["progress"],
                    lesson=snapshot.get("lesson"),
                    teaching_mode=snapshot.get("teaching_mode", "practice_only"),
                    strategy=snapshot.get("strategy", {}),
                    history=history + [student_message],
                    practice_mode=bool(active_questions),
                    active_questions=active_questions,
                )
                teacher_message = save_message(session_id, student["id"], "teacher", answer)
                await websocket.send_json(
                    {
                        "type": "answer",
                        "answer": answer,
                        "message": teacher_message,
                        "practice_mode": bool(active_questions),
                    }
                )
        except WebSocketDisconnect:
            return
