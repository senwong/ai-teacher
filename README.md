# AI Teacher MVP

面向纸笔学习场景的 AI Teacher 原型。

当前已实现：

- 多学生管理：学生列表、新增学生、学生详情
- 每个学生独立的掌握度、答题记录和试卷
- Learning Session：每次学习都有独立 session_id、开始/结束时间和统计
- 三年级数学练习、规则批改、错误诊断、Teacher 状态机
- A4 PDF 试卷 + worksheet_id + QR Code
- 答卷照片二维码识别、透视矫正
- 可选 Vision：读取最终答案和书写步骤
- 人工确认后再更新 Student Model

## 数据链路

```text
Student
  ↓
Learning Session
  ↓
Teacher Agent
  ↓
Worksheet / Screen Practice
  ↓
Attempt
  ↓
Student Model / Mastery
```

Worksheet 同时保存 `student_id` 和 `session_id`，因此摄像头只要识别二维码，就能自动关联到对应学生和学习过程。

## 运行

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

打开 http://127.0.0.1:8000 ，首页会进入学生管理。

## Vision（可选）

```bash
export OPENAI_API_KEY="..."
export OPENAI_VISION_MODEL="gpt-5.6-luna"
```

二维码识别和页面透视矫正不依赖 API Key。

## 测试

```bash
PYTHONPATH=. pytest -q
```

## Next

V1.3：打印机 + 固定摄像头 + 自动拍照，将 Paper Loop 进一步变成实体 AI Teacher Machine。
