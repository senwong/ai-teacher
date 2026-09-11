# AI Teacher MVP

一个最小可运行的「AI 老师」教学闭环：**讲解 → 出题 → 学生作答 → 批改 → 错误诊断 → 更新掌握度 → 决定下一教学动作**。

当前 V0 聚焦小学三年级数学「两位数乘一位数」。先验证教学闭环，不接打印机和摄像头；V1 再加入 PDF/打印和拍照识别。

## 架构

- FastAPI：Web 与 API
- SQLite：学生与学习进度
- Rule Engine：批改、错误分类、掌握度、状态机
- Optional LLM：配置 `OPENAI_API_KEY` 后，用模型生成更自然的教师讲解；没有 Key 也能完整运行
- Vanilla HTML/CSS：零前端构建依赖

## 快速开始

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

打开 http://127.0.0.1:8000

> 如果要启用模型讲解，请把 `.env` 中 `OPENAI_API_KEY` 导入当前 shell，例如 `export OPENAI_API_KEY=...`。当前代码不会主动读取 `.env` 文件，避免额外依赖；也可以自行加入 `python-dotenv`。

## 测试

```bash
pytest -q
```

## 当前教学状态机

```text
TEACHING
  ↓
PRACTICE
  ↓
GRADING
  ↓
DIAGNOSIS
  ├── RETEACH
  └── NEXT_SKILL
```

当前掌握度采用最简单的 `correct / attempts`，目的是先验证系统结构。后续可以替换为滚动窗口、IRT/BKT 或带遗忘曲线的 mastery model。

## V1 Roadmap

1. Worksheet JSON → PDF 渲染
2. CUPS / macOS `lp` 自动打印
3. 试卷 QR Code / worksheet_id
4. 相机拍照上传
5. Vision 模型识别答案和步骤
6. 程序校验客观题，模型诊断解题过程
7. 学生知识图谱与跨天复习计划
8. 家长 / 真人导师 Dashboard

## 为什么先规则、后 Agent

Teacher Agent 不应该完全自由运行。课程、掌握规则和关键状态转移由程序控制，模型主要负责解释、反馈和教学策略语言化，这样更容易测试、追踪和迭代。
