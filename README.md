# Nano Claw

基于 GLM 大语言模型的对话应用，支持流式回复和思维链。


## 快速开始

### 1. 克隆并安装后端

```bash
pip install -e .
```

### 2. 配置

创建并编辑 `config.yml`，填入你的信息：

```yaml
# Port
backend_port: 3000
frontend_port: 4000

# GLM API
api_key: your-api-key-here
api_url: https://open.bigmodel.cn/api/paas/v4/chat/completions

# MySQL
db_host: localhost
db_port: 3306
db_user: root
db_password: ""
db_name: nano_claw
```

### 3. 初始化数据库

```bash
mysql -u root -p -e "CREATE DATABASE nano_claw CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

```

### 4. 启动后端

```bash
python -m backend.run
```

### 5. 启动前端

```bash
cd frontend
npm install
npm run dev
```


## 项目结构

```
├── backend/          # Flask 后端
│   ├── __init__.py
│   ├── models.py     # 数据模型
│   └── routes.py     # API 路由
├── frontend/         # Vue 3 前端
│   └── src/
│       ├── api/      # API 请求层
│       └── components/ # UI 组件
├── docs/             # 文档
├── config.yml.example
└── pyproject.toml
```

## API 概览

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/conversations` | 创建会话 |
| GET | `/api/conversations` | 会话列表 |
| PATCH | `/api/conversations/:id` | 更新会话 |
| DELETE | `/api/conversations/:id` | 删除会话 |
| GET | `/api/conversations/:id/messages` | 消息列表 |
| POST | `/api/conversations/:id/messages` | 发送消息（支持 SSE 流式） |
| DELETE | `/api/conversations/:id/messages/:mid` | 删除消息 |

详细 API 文档见 [docs/design.md](docs/design.md)。
