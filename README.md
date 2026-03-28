# NanoClaw

基于 LLM 大语言模型的 AI 对话应用，支持工具调用、思维链、流式回复和工作目录隔离。

## 功能特性

- 多轮对话 - 支持上下文管理的多轮对话
- 工具调用 - 网页搜索、代码执行、文件操作等 13 个内置工具
- 思维链 - 支持链式思考推理（DeepSeek R1 / GLM thinking）
- 工作目录 - 项目级文件隔离，安全操作
- Token 统计 - 按日/周/月统计使用量
- 流式响应 - 实时 SSE 流式输出，穿插显示思考/文本/工具调用
- 代码编辑器 - 基于 CodeMirror 6，支持 15+ 语言语法高亮和暗色主题
- 多数据库 - 支持 MySQL、SQLite、PostgreSQL
- 多用户/单用户 - 支持单用户免登录和多用户 JWT 认证两种模式

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

# Max agentic loop iterations (tool call rounds)
max_iterations: 15

# Sub-agent settings (multi_agent tool)
sub_agent:
  max_iterations: 3      # Max tool-call rounds per sub-agent
  max_tokens: 4096        # Max tokens per LLM call inside a sub-agent
  max_agents: 5           # Max number of concurrent sub-agents per request
  max_concurrency: 3      # ThreadPoolExecutor max workers

# Available models
# Each model must have its own id, name, api_url, api_key
models:
  - id: deepseek-chat
    name: DeepSeek V3
    api_url: https://api.deepseek.com/chat/completions
    api_key: sk-xxx
  - id: glm-5
    name: GLM-5
    api_url: https://open.bigmodel.cn/api/paas/v4/chat/completions
    api_key: xxx

default_model: deepseek-chat

# Database Configuration
# Supported types: mysql, sqlite, postgresql
db_type: sqlite

# MySQL/PostgreSQL Settings (ignored for sqlite)
# db_host: localhost
# db_port: 3306
# db_user: root
# db_password: "123456"
# db_name: nano_claw

# SQLite Settings (ignored for mysql/postgresql)
db_sqlite_file: nano_claw.db

# Workspace Configuration
workspace_root: ./workspaces

# Authentication (optional, defaults to single-user mode)
# auth_mode: single  # "single" (default) or "multi"
# jwt_secret: nano-claw-default-secret-change-in-production
```

> **说明**：`api_key` 支持环境变量替换，例如 `api_key: ${DEEPSEEK_API_KEY}`。

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
├── __init__.py          # 应用工厂，数据库初始化，load_config()
├── config.py            # 配置加载与验证
├── models.py            # SQLAlchemy 数据模型
├── run.py               # 入口文件
├── routes/              # API 路由
│   ├── auth.py          # 认证（登录/注册/JWT/profile）
│   ├── conversations.py # 会话 CRUD
│   ├── messages.py      # 消息 CRUD + 聊天（SSE 流式）
│   ├── models.py        # 模型列表
│   ├── projects.py      # 项目管理 + 文件操作
│   ├── stats.py         # Token 使用统计
│   └── tools.py         # 工具列表
├── services/            # 业务逻辑
│   ├── chat.py          # 聊天补全服务（SSE 流式 + 多轮工具调用）
│   └── llm_client.py    # OpenAI 兼容 LLM API 客户端
├── tools/               # 工具系统
│   ├── core.py          # 核心类（ToolDefinition/ToolRegistry）
│   ├── factory.py       # @tool 装饰器 + register_tool()
│   ├── executor.py      # 工具执行器（缓存、去重、上下文注入）
│   ├── services.py      # 辅助服务（搜索/抓取/计算）
│   └── builtin/         # 内置工具
│       ├── crawler.py   # 网页搜索、抓取
│       ├── data.py      # 计算器、文本、JSON 处理
│       ├── weather.py   # 天气查询（模拟）
│       ├── file_ops.py  # 文件操作（6 个工具，project_id 自动注入）
│       ├── agent.py     # 多智能体（子 Agent 并发执行，工具权限隔离）
│       └── code.py      # Python 代码执行（沙箱）
└── utils/               # 辅助函数
    ├── helpers.py       # 通用函数（ok/err/build_messages 等）
    └── workspace.py     # 工作目录工具（路径验证、项目目录管理）

frontend/
└── src/
    ├── api/             # API 请求层（request + SSE 流解析）
    ├── components/      # Vue 组件（12 个）
    ├── composables/     # 组合式函数（主题/模态框/Toast）
    └── utils/           # 工具模块（Markdown 渲染/代码高亮/图标）
```

## 工作目录系统

### 概述

工作目录系统为文件操作提供安全隔离，确保 AI 只能访问指定项目目录内的文件。

### 使用流程

1. **创建项目** - 在侧边栏点击"新建项目"或上传文件夹
2. **选择项目** - 在对话中选择当前工作目录
3. **文件操作** - AI 自动在项目目录内执行文件操作（`project_id` 由后端自动注入，对 AI 透明）

### 安全机制

- 所有文件工具的 `project_id` 由后端自动注入，AI 不可见也不可伪造
- 后端强制验证路径在项目目录内
- 阻止目录遍历攻击（如 `../../../etc/passwd`）

## API 概览

### 认证

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/auth/mode` | 获取当前认证模式 |
| `POST` | `/api/auth/login` | 用户登录 |
| `POST` | `/api/auth/register` | 用户注册 |
| `GET` | `/api/auth/profile` | 获取当前用户信息 |
| `PATCH` | `/api/auth/profile` | 更新当前用户信息 |

### 会话管理

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET/POST` | `/api/conversations` | 会话列表 / 创建会话 |
| `GET` | `/api/conversations/:id` | 会话详情 |
| `PATCH` | `/api/conversations/:id` | 更新会话 |
| `DELETE` | `/api/conversations/:id` | 删除会话 |

### 消息管理

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/conversations/:id/messages` | 消息列表 |
| `POST` | `/api/conversations/:id/messages` | 发送消息（SSE 流式） |
| `DELETE` | `/api/conversations/:id/messages/:mid` | 删除消息 |
| `POST` | `/api/conversations/:id/regenerate/:mid` | 重新生成消息 |

### 项目管理

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET/POST` | `/api/projects` | 项目列表 / 创建项目 |
| `GET/PUT/DELETE` | `/api/projects/:id` | 项目详情 / 更新 / 删除 |
| `POST` | `/api/projects/upload` | 上传文件夹作为项目 |
| `GET` | `/api/projects/:id/files` | 列出项目文件 |
| `GET/PUT/PATCH/DELETE` | `/api/projects/:id/files/:path` | 文件 CRUD |
| `POST` | `/api/projects/:id/directories` | 创建目录 |
| `POST` | `/api/projects/:id/search` | 搜索文件内容 |

### 其他

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/models` | 获取可用模型列表 |
| `GET` | `/api/tools` | 获取工具列表 |
| `GET` | `/api/stats/tokens` | Token 使用统计 |

## 内置工具

| 分类 | 工具 | 说明 |
|------|------|------|
| **爬虫** | web_search, fetch_page, crawl_batch | 网页搜索和抓取 |
| **数据处理** | calculator, text_process, json_process | 数学计算和文本处理 |
| **代码执行** | execute_python | 沙箱环境执行 Python |
| **文件操作** | file_read, file_write, file_delete, file_list, file_exists, file_mkdir | project_id 自动注入 |
| **天气** | get_weather | 天气查询（模拟） |
| **智能体** | multi_agent | 派生子 Agent 并发执行（禁止递归，工具权限与主 Agent 一致） |

## 文档

- [后端设计](docs/Design.md) - 架构设计、数据模型、API 文档、SSE 事件
- [工具系统](docs/ToolSystemDesign.md) - 工具开发指南、安全设计

## 技术栈

- **后端**: Python 3.10+, Flask, SQLAlchemy, requests
- **前端**: Vue 3, Vite 6, CodeMirror 6, marked, highlight.js, KaTeX
- **LLM**: 支持任何 OpenAI 兼容 API（DeepSeek、GLM、OpenAI、Moonshot、Qwen 等）
