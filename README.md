# NanoClaw

基于 LLM 大语言模型的 AI 对话应用，支持工具调用、思维链、流式回复和工作目录隔离。

## 功能特性

- 💬 **多轮对话** - 支持上下文管理的多轮对话
- 🔧 **工具调用** - 网页搜索、代码执行、文件操作等
- 🧠 **思维链** - 支持链式思考推理
- 📁 **工作目录** - 项目级文件隔离，安全操作
- 📊 **Token 统计** - 按日/周/月统计使用量
- 🔄 **流式响应** - 实时 SSE 流式输出
- 📝 **代码编辑器** - 基于 CodeMirror 6，支持 15+ 语言语法高亮和暗色主题
- 💾 **多数据库** - 支持 MySQL、SQLite、PostgreSQL

## 快速开始

### 1. 安装依赖

```bash
conda create -n claw python=3.12
conda activate claw
pip install -e .
```

### 2. 配置

复制并编辑 `config.yml`：

```yaml
# Port
backend_port: 3000
frontend_port: 4000

# LLM API (global defaults, can be overridden per model)
default_api_key: {{your-api-key}}
default_api_url: https://open.bigmodel.cn/api/paas/v4/chat/completions

# Available models (each model can optionally specify its own api_key and api_url)
models:
  - id: glm-5
    name: GLM-5
    # api_key: xxx       # Optional, falls back to default_api_key
    # api_url: xxx       # Optional, falls back to default_api_url
  - id: glm-4-plus
    name: GLM-4 Plus

default_model: glm-5

# Workspace root directory
workspace_root: ./workspaces

# Authentication
# "single": Single-user mode - no login required, auto-creates default user
# "multi": Multi-user mode - requires JWT, users must register/login
auth_mode: single

# JWT secret (only used in multi-user mode, change for production!)
jwt_secret: nano-claw-default-secret-change-in-production

# Database Configuration
db_type: sqlite
db_sqlite_file: nano_claw.db
```

### 3. 启动后端

```bash
python -m backend.run
```

### 4. 启动前端

```bash
cd frontend
npm install
npm run dev
```

## 项目结构

```
backend/
├── models.py        # SQLAlchemy 数据模型
├── routes/          # API 路由
│   ├── auth.py      # 认证（登录/注册/JWT）
│   ├── conversations.py
│   ├── messages.py
│   ├── projects.py  # 项目管理
│   └── ...
├── services/        # 业务逻辑
│   ├── chat.py      # 聊天补全服务
│   └── glm_client.py
├── tools/           # 工具系统
│   ├── core.py      # 核心类
│   ├── executor.py  # 工具执行器
│   └── builtin/     # 内置工具
├── utils/           # 辅助函数
│   ├── helpers.py
│   └── workspace.py # 工作目录工具
└── migrations/      # 数据库迁移

frontend/
└── src/
    ├── api/         # API 请求层
    ├── components/  # Vue 组件
    └── views/       # 页面
```

## 工作目录系统

### 概述

工作目录系统为文件操作提供安全隔离，确保 AI 只能访问指定项目目录内的文件。

### 使用流程

1. **创建项目** - 在侧边栏点击"新建项目"或上传文件夹
2. **选择项目** - 在对话中选择当前工作目录
3. **文件操作** - AI 自动在项目目录内执行文件操作

### 安全机制

- 所有文件操作需要 `project_id` 参数
- 后端强制验证路径在项目目录内
- 阻止目录遍历攻击（如 `../../../etc/passwd`）

## API 概览

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/auth/login` | 用户登录 |
| `POST` | `/api/auth/register` | 用户注册 |
| `GET` | `/api/conversations` | 会话列表 |
| `GET` | `/api/conversations/:id/messages` | 消息列表 |
| `POST` | `/api/conversations/:id/messages` | 发送消息（SSE 流式） |
| `GET` | `/api/projects` | 项目列表 |
| `POST` | `/api/projects` | 创建项目 |
| `POST` | `/api/projects/upload` | 上传文件夹 |
| `GET` | `/api/tools` | 工具列表 |
| `GET` | `/api/stats/tokens` | Token 统计 |

## 内置工具

| 分类 | 工具 | 说明 |
|------|------|------|
| **爬虫** | web_search, fetch_page, crawl_batch | 网页搜索和抓取 |
| **数据处理** | calculator, text_process, json_process | 数学计算和文本处理 |
| **代码执行** | execute_python | 沙箱环境执行 Python |
| **文件操作** | file_read, file_write, file_list 等 | **需要 project_id** |
| **天气** | get_weather | 天气查询（模拟） |

## 文档

- [后端设计](docs/Design.md) - 架构设计、数据模型、API 文档
- [工具系统](docs/ToolSystemDesign.md) - 工具开发指南、安全设计

## 技术栈

- **后端**: Python 3.11+, Flask, SQLAlchemy
- **前端**: Vue 3, Vite, CodeMirror 6
- **LLM**: 支持 GLM 等大语言模型
