# NanoClaw

基于 GLM 大语言模型的 AI 对话应用，支持工具调用、思维链和流式回复。

## 功能特性

- 💬 **多轮对话** - 支持上下文管理的多轮对话
- 🔧 **工具调用** - 网页搜索、代码执行、文件操作等
- 🧠 **思维链** - 支持链式思考推理
- 📊 **Token 统计** - 按日/周/月统计使用量
- 🔄 **流式响应** - 实时 SSE 流式输出
- 💾 **多数据库** - 支持 MySQL、SQLite、PostgreSQL

## 快速开始

### 1. 安装依赖

```bash
pip install -e .
```

### 2. 配置

复制并编辑 `config.yml`：

```yaml
# Port
backend_port: 3000
frontend_port: 4000

# AI API
api_key: {{your-api-key}}
api_url: https://open.bigmodel.cn/api/paas/v4/chat/completions

# Available models
models:
  - id: glm-5
    name: GLM-5
  - id: glm-5-turbo
    name: GLM-5 Turbo
  - id: glm-4.5
    name: GLM-4.5
  - id: glm-4.6
    name: GLM-4.6
  - id: glm-4.7
    name: GLM-4.7

default_model: glm-5

# Database Configuration
# Supported types: mysql, sqlite, postgresql
db_type: sqlite

# MySQL/PostgreSQL Settings (ignored for sqlite)
db_host: localhost
db_port: 3306
db_user: root
db_password: "123456"
db_name: nano_claw

# SQLite Settings (ignored for mysql/postgresql)
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
├── services/        # 业务逻辑
│   ├── chat.py      # 聊天补全服务
│   └── glm_client.py
├── tools/           # 工具系统
│   ├── core.py      # 核心类
│   ├── executor.py  # 工具执行器
│   └── builtin/     # 内置工具
└── utils/           # 辅助函数

frontend/
└── src/
    ├── api/         # API 请求层
    ├── components/  # Vue 组件
    └── views/       # 页面
```

## API 概览

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/conversations` | 创建会话 |
| `GET` | `/api/conversations` | 会话列表 |
| `GET` | `/api/conversations/:id/messages` | 消息列表 |
| `POST` | `/api/conversations/:id/messages` | 发送消息（SSE） |
| `GET` | `/api/tools` | 工具列表 |
| `GET` | `/api/stats/tokens` | Token 统计 |

## 内置工具

| 分类 | 工具 |
|------|------|
| **爬虫** | web_search, fetch_page, crawl_batch |
| **数据处理** | calculator, text_process, json_process |
| **代码执行** | execute_python（沙箱环境） |
| **文件操作** | file_read, file_write, file_list 等 |
| **天气** | get_weather |

## 文档

- [后端设计](docs/Design.md) - 架构设计、类图、API 文档
- [工具系统](docs/ToolSystemDesign.md) - 工具开发指南

## 技术栈

- **后端**: Python 3.11+, Flask
- **前端**: Vue 3
- **大模型**: GLM API（智谱AI）
