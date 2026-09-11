# AI Teacher MVP

面向纸笔学习场景的 AI Teacher 原型。

当前已实现：

- 多学生管理：学生列表、新增学生、学生详情
- 入学诊断：按知识点初始化学习起点
- Personalized Roadmap：每个学生独立推进
- Spaced Review + Forgetting Model：自动安排到期复习
- Learning Session：每次学习都有独立 session_id、开始/结束时间和统计
- 三年级数学练习、规则批改、错误诊断、Teacher 状态机
- A4 PDF 试卷 + worksheet_id + QR Code
- 答卷照片二维码识别、透视矫正
- 可选 Vision：读取最终答案和书写步骤
- 人工确认后再更新 Student Model

## 一键 Docker 部署

服务器只需要提前安装 Docker，并确保 Docker daemon 正常运行。

```bash
git clone https://github.com/senwong/ai-teacher.git
cd ai-teacher
sh deploy.sh
```

`deploy.sh` 会自动：

1. 检查 Docker / Docker Compose
2. 首次部署时从 `.env.example` 创建 `.env`
3. 创建持久化数据目录
4. 构建 Docker 镜像
5. 启动 `ai-teacher` 容器
6. 等待容器健康检查通过
7. 输出访问地址、日志命令和停止命令

默认访问：

```text
http://127.0.0.1:8000
```

如果服务器需要对外提供服务，请在防火墙 / 安全组中开放对应端口，或者后续使用 Nginx/Caddy 反向代理。

### 修改端口

编辑 `.env`：

```bash
AI_TEACHER_PORT=8080
```

然后重新执行：

```bash
sh deploy.sh
```

### 配置 OpenAI（可选）

编辑 `.env`：

```bash
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-5.6-luna
OPENAI_VISION_MODEL=gpt-5.6-luna
```

没有配置 API Key 时，规则批改、二维码、透视矫正、学生管理、Roadmap、复习调度仍可运行。

### 更新部署

```bash
git pull
sh deploy.sh
```

SQLite、上传照片、生成试卷都保存在宿主机 `./data`，重新构建容器不会丢失。

### 常用 Docker 命令

```bash
# 看状态
docker compose ps

# 看实时日志
docker compose logs -f ai-teacher

# 停止服务
docker compose down

# 再次部署 / 更新
sh deploy.sh
```

如果机器仍使用旧版 Compose，也可以使用 `docker-compose`；`deploy.sh` 会自动兼容。

## 数据链路

```text
Student
  ↓
Diagnostic / Review Scheduler
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

## 本地 Python 运行

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

打开 http://127.0.0.1:8000 ，首页会进入学生管理。

## 测试

```bash
PYTHONPATH=. pytest -q
```
