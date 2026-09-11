# AI Teacher MVP

一个最小可运行的「AI 老师」教学闭环：**讲解 → 出题 → 纸笔作答 → 拍照 → 确认识别 → 批改 → 错误诊断 → 更新掌握度 → 决定下一教学动作**。

当前聚焦小学三年级数学「两位数乘一位数」。V1 已加入真实纸笔练习链路。

## V1 已完成

- FastAPI + SQLite + 零构建 Web UI
- 生成 5 道数学题
- 为每份试卷生成唯一 `worksheet_id`
- ReportLab 生成 A4 PDF
- PDF 内含二维码，可用于后续相机自动关联试卷
- 上传 JPG / PNG / WEBP 答卷照片
- 配置 `OPENAI_API_KEY` 后调用 Vision 模型提取每题最终答案
- Vision 结果先让学生/家长确认，再进入批改，避免识别错误污染学习数据
- 未配置 Vision 时自动降级为人工录入答案
- 复用原有 grader、错误分类、Student Model、Teacher State Machine
- `attempts` 记录可关联 `worksheet_id`

## 快速开始

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

打开 http://127.0.0.1:8000

如需 Vision：

```bash
export OPENAI_API_KEY=your_key
export OPENAI_VISION_MODEL=gpt-5.6-luna
uvicorn app.main:app --reload
```

## V1 Paper Loop

```text
Teacher Agent
   ↓
生成 questions JSON
   ↓
创建 worksheet_id
   ↓
PDF + QR Code
   ↓
打印 / 纸笔作答
   ↓
拍照上传
   ↓
Vision 提取答案
   ↓
人工确认识别结果
   ↓
规则批改 + 错误分类
   ↓
Student Model
   ↓
RETEACH / PRACTICE / NEXT_SKILL
```

这里刻意把 **Vision Recognition** 和 **Grading** 拆开：Vision 只负责看清学生写了什么，正确性仍由确定性程序判断。

## 测试

```bash
pytest -q
```

## 接下来：V1.1 / V2

1. 二维码拍照后自动定位 worksheet_id
2. OpenCV 做透视矫正 / 页面裁切
3. Vision 提取竖式步骤并升级错误诊断
4. macOS `lp` / CUPS 一键自动打印
5. 固定摄像头自动拍照
6. 长期知识图谱与跨天 Teacher Agent
