# 对话系统后端 API 设计

## API 总览

### 会话管理

| 方法       | 路径                       | 说明     |
| -------- | ------------------------ | ------ |
| `POST`   | `/api/conversations`     | 创建会话   |
| `GET`    | `/api/conversations`     | 获取会话列表 |
| `GET`    | `/api/conversations/:id` | 获取会话详情 |
| `PATCH`  | `/api/conversations/:id` | 更新会话   |
| `DELETE` | `/api/conversations/:id` | 删除会话   |

### 消息管理

| 方法       | 路径                                            | 说明                        |
| -------- | --------------------------------------------- | ------------------------- |
| `GET`    | `/api/conversations/:id/messages`             | 获取消息列表                    |
| `POST`   | `/api/conversations/:id/messages`             | 发送消息（对话补全，支持 `stream` 流式） |
| `DELETE` | `/api/conversations/:id/messages/:message_id` | 删除消息                      |

### 模型与工具

| 方法     | 路径            | 说明       |
| ------ | ------------- | -------- |
| `GET`  | `/api/models`  | 获取模型列表   |
| `GET`  | `/api/tools`   | 获取工具列表   |

### 统计信息

| 方法     | 路径                   | 说明               |
| ------ | -------------------- | ---------------- |
| `GET`  | `/api/stats/tokens`   | 获取 Token 使用统计    |

---

## API 接口

### 1. 会话管理

#### 创建会话

```
POST /api/conversations
```

**请求体：**

```json
{
  "title": "新对话",
  "model": "glm-5",
  "system_prompt": "你是一个有帮助的助手",
  "temperature": 1.0,
  "max_tokens": 65536,
  "thinking_enabled": false
}
```

**响应：**

```json
{
  "code": 0,
  "data": {
    "id": "conv_abc123",
    "title": "新对话",
    "model": "glm-5",
    "system_prompt": "你是一个有帮助的助手",
    "temperature": 1.0,
    "max_tokens": 65536,
    "thinking_enabled": false,
    "created_at": "2026-03-24T10:00:00Z",
    "updated_at": "2026-03-24T10:00:00Z"
  }
}
```

#### 获取会话列表

```
GET /api/conversations?cursor=conv_abc123&limit=20
```

| 参数       | 类型      | 说明                |
| -------- | ------- | ----------------- |
| `cursor` | string  | 分页游标，为空取首页        |
| `limit`  | integer | 每页数量，默认 20，最大 100 |

**响应：**

```json
{
  "code": 0,
  "data": {
    "items": [
      {
        "id": "conv_abc123",
        "title": "新对话",
        "model": "glm-5",
        "created_at": "2026-03-24T10:00:00Z",
        "updated_at": "2026-03-24T10:05:00Z",
        "message_count": 6
      }
    ],
    "next_cursor": "conv_def456",
    "has_more": true
  }
}
```

#### 获取会话详情

```
GET /api/conversations/:id
```

**响应：**

```json
{
  "code": 0,
  "data": {
    "id": "conv_abc123",
    "title": "新对话",
    "model": "glm-5",
    "system_prompt": "你是一个有帮助的助手",
    "temperature": 1.0,
    "max_tokens": 65536,
    "thinking_enabled": false,
    "created_at": "2026-03-24T10:00:00Z",
    "updated_at": "2026-03-24T10:05:00Z"
  }
}
```

#### 更新会话

```
PATCH /api/conversations/:id
```

**请求体（仅传需更新的字段）：**

```json
{
  "title": "修改后的标题",
  "system_prompt": "新的系统提示词",
  "temperature": 0.8
}
```

**响应：** 同获取会话详情

#### 删除会话

```
DELETE /api/conversations/:id
```

**响应：**

```json
{
  "code": 0,
  "message": "deleted"
}
```

---

### 2. 消息管理

#### 获取消息列表

```
GET /api/conversations/:id/messages?cursor=msg_001&limit=50
```

| 参数       | 类型      | 说明                |
| -------- | ------- | ----------------- |
| `cursor` | string  | 分页游标              |
| `limit`  | integer | 每页数量，默认 50，最大 100 |

**响应：**

```json
{
  "code": 0,
  "data": {
    "items": [
      {
        "id": "msg_001",
        "conversation_id": "conv_abc123",
        "role": "user",
        "content": "你好",
        "token_count": 2,
        "thinking_content": null,
        "tool_calls": null,
        "created_at": "2026-03-24T10:00:00Z"
      },
      {
        "id": "msg_002",
        "conversation_id": "conv_abc123",
        "role": "assistant",
        "content": "你好！有什么可以帮你的？",
        "token_count": 15,
        "thinking_content": null,
        "tool_calls": null,
        "created_at": "2026-03-24T10:00:01Z"
      }
    ],
    "next_cursor": "msg_003",
    "has_more": false
  }
}
```

#### 发送消息（对话补全）

```
POST /api/conversations/:id/messages
```

**请求体：**

```json
{
  "content": "介绍一下你的能力",
  "stream": true,
  "tools_enabled": true
}
```

| 参数              | 类型       | 说明                     |
| --------------- | -------- | ---------------------- |
| `content`       | string   | 用户消息内容                 |
| `stream`        | boolean  | 是否流式响应，默认 `true`       |
| `tools_enabled` | boolean  | 是否启用工具调用，默认 `true`（可选） |

**流式响应 (stream=true)：**

**普通回复示例：**

```
HTTP/1.1 200 OK
Content-Type: text/event-stream

event: thinking
data: {"content": "用户想了解我的能力..."}

event: message
data: {"content": "我是"}

event: message
data: {"content": "智谱AI"}

event: message
data: {"content": "开发的大语言模型"}

event: done
data: {"message_id": "msg_003", "token_count": 200}
```

**工具调用示例：**

```
HTTP/1.1 200 OK
Content-Type: text/event-stream

event: thinking
data: {"content": "用户想知道北京天气..."}

event: tool_calls
data: {"calls": [{"id": "call_001", "type": "function", "function": {"name": "get_weather", "arguments": "{\"city\": \"北京\"}"}}]}

event: tool_result
data: {"name": "get_weather", "content": "{\"temperature\": 25, \"humidity\": 60, \"description\": \"晴天\"}"}

event: message
data: {"content": "北京"}

event: message
data: {"content": "今天天气晴朗，"}

event: message
data: {"content": "温度25°C，"}

event: message
data: {"content": "湿度60%"}

event: done
data: {"message_id": "msg_003", "token_count": 150}
```

**非流式响应 (stream=false)：**

```json
{
  "code": 0,
  "data": {
    "message": {
      "id": "msg_003",
      "conversation_id": "conv_abc123",
      "role": "assistant",
      "content": "我是智谱AI开发的大语言模型...",
      "token_count": 200,
      "thinking_content": "用户想了解我的能力...",
      "tool_calls": null,
      "created_at": "2026-03-24T10:01:00Z"
    },
    "usage": {
      "prompt_tokens": 50,
      "completion_tokens": 200,
      "total_tokens": 250
    }
  }
}
```

#### 删除消息

```
DELETE /api/conversations/:id/messages/:message_id
```

**响应：**

```json
{
  "code": 0,
  "message": "deleted"
}
```

---

### 3. 模型与工具

#### 获取模型列表

```
GET /api/models
```

**响应：**

```json
{
  "code": 0,
  "data": [
    {"id": "glm-5", "name": "GLM-5"},
    {"id": "glm-5-turbo", "name": "GLM-5 Turbo"},
    {"id": "glm-4.5", "name": "GLM-4.5"},
    {"id": "glm-4.6", "name": "GLM-4.6"},
    {"id": "glm-4.7", "name": "GLM-4.7"}
  ]
}
```

#### 获取工具列表

```
GET /api/tools
```

**响应：**

```json
{
  "code": 0,
  "data": {
    "tools": [
      {
        "name": "get_weather",
        "description": "获取指定城市的天气信息",
        "parameters": {
          "type": "object",
          "properties": {
            "city": {
              "type": "string",
              "description": "城市名称"
            }
          },
          "required": ["city"]
        }
      }
    ],
    "total": 1
  }
}
```

---

### 4. 统计信息

#### 获取 Token 使用统计

```
GET /api/stats/tokens?period=daily
```

**参数：**

| 参数       | 类型     | 说明                                    |
| -------- | ------ | ------------------------------------- |
| `period` | string | 统计周期：`daily`（今日）、`weekly`（近7天）、`monthly`（近30天） |

**响应（daily）：**

```json
{
  "code": 0,
  "data": {
    "period": "daily",
    "date": "2026-03-24",
    "prompt_tokens": 1000,
    "completion_tokens": 2000,
    "total_tokens": 3000,
    "by_model": {
      "glm-5": {
        "prompt": 500,
        "completion": 1000,
        "total": 1500
      },
      "glm-4": {
        "prompt": 500,
        "completion": 1000,
        "total": 1500
      }
    }
  }
}
```

**响应（weekly/monthly）：**

```json
{
  "code": 0,
  "data": {
    "period": "weekly",
    "start_date": "2026-03-18",
    "end_date": "2026-03-24",
    "prompt_tokens": 7000,
    "completion_tokens": 14000,
    "total_tokens": 21000,
    "daily": {
      "2026-03-18": {"prompt": 1000, "completion": 2000, "total": 3000},
      "2026-03-19": {"prompt": 1000, "completion": 2000, "total": 3000},
      ...
    }
  }
}
```

---

### 5. SSE 事件说明

| 事件            | 说明                                       |
| ------------- | ---------------------------------------- |
| `thinking`    | 思维链增量内容（启用时）                             |
| `message`     | 回复内容的增量片段                                |
| `tool_calls`  | 工具调用信息，包含工具名称和参数                         |
| `tool_result` | 工具执行结果，包含工具名称和返回内容                       |
| `error`       | 错误信息                                     |
| `done`        | 回复结束，携带完整 message_id 和 token 统计          |

**tool_calls 事件数据格式：**

```json
{
  "calls": [
    {
      "id": "call_001",
      "type": "function",
      "function": {
        "name": "get_weather",
        "arguments": "{\"city\": \"北京\"}"
      }
    }
  ]
}
```

**tool_result 事件数据格式：**

```json
{
  "name": "get_weather",
  "content": "{\"temperature\": 25, \"humidity\": 60}"
}
```

---

### 6. 错误码

| code  | 说明       |
| ----- | -------- |
| `0`   | 成功       |
| `400` | 请求参数错误   |
| `401` | 未认证      |
| `403` | 无权限访问该资源 |
| `404` | 资源不存在    |
| `429` | 请求过于频繁   |
| `500` | 上游模型服务错误 |
| `503` | 服务暂时不可用  |

**错误响应格式：**

```json
{
  "code": 404,
  "message": "conversation not found"
}
```

---

## 数据模型

### ER 关系

```
User  1 ── * Conversation  1 ── * Message
```

### Conversation（会话）

| 字段                 | 类型            | 说明                    |
| ------------------ | ------------- | --------------------- |
| `id`               | string (UUID) | 会话 ID                 |
| `user_id`          | string        | 所属用户 ID               |
| `title`            | string        | 会话标题                  |
| `model`            | string        | 使用的模型，默认 `glm-5`      |
| `system_prompt`    | string        | 系统提示词                 |
| `temperature`      | float         | 采样温度，默认 `1.0`         |
| `max_tokens`       | integer       | 最大输出 token，默认 `65536` |
| `thinking_enabled` | boolean       | 是否启用思维链，默认 `false`    |
| `created_at`       | datetime      | 创建时间                  |
| `updated_at`       | datetime      | 更新时间                  |

### Message（消息）

| 字段                 | 类型            | 说明                              |
| ------------------ | ------------- | ------------------------------- |
| `id`               | string (UUID) | 消息 ID                           |
| `conversation_id`  | string        | 所属会话 ID                         |
| `role`             | enum          | `user` / `assistant` / `system`  |
| `content`          | string        | 消息内容                            |
| `token_count`      | integer       | token 消耗数                       |
| `thinking_content` | string        | 思维链内容（启用时）                      |
| `tool_calls`       | array (JSON)  | 工具调用信息（含结果），仅 assistant 消息      |
| `created_at`       | datetime      | 创建时间                            |

#### 消息类型说明

**1. 用户消息 (role=user)**
```json
{
  "id": "msg_001",
  "role": "user",
  "content": "北京今天天气怎么样？",
  "created_at": "2026-03-24T10:00:00Z"
}
```

**2. 助手消息 - 普通回复 (role=assistant)**
```json
{
  "id": "msg_002",
  "role": "assistant",
  "content": "北京今天天气晴朗...",
  "token_count": 50,
  "thinking_content": "用户想了解天气...",
  "tool_calls": null,
  "created_at": "2026-03-24T10:00:01Z"
}
```

**3. 助手消息 - 含工具调用 (role=assistant, with tool_calls)**

工具调用结果直接合并到 `tool_calls` 数组中，每个调用包含 `result` 字段：

```json
{
  "id": "msg_003",
  "role": "assistant",
  "content": "北京今天天气晴朗，温度25°C，湿度60%",
  "token_count": 80,
  "thinking_content": "用户想知道北京天气，需要调用工具获取...",
  "tool_calls": [
    {
      "id": "call_abc123",
      "type": "function",
      "function": {
        "name": "get_weather",
        "arguments": "{\"city\": \"北京\"}"
      },
      "result": "{\"temperature\": 25, \"humidity\": 60, \"description\": \"晴天\"}"
    }
  ],
  "created_at": "2026-03-24T10:00:02Z"
}
```

#### 工具调用流程示例

```
用户: "北京今天天气怎么样？"
    ↓
[msg_001] role=user, content="北京今天天气怎么样？"
    ↓
[AI 调用工具 get_weather]
    ↓
[msg_002] role=assistant, tool_calls=[{get_weather, args:{"city":"北京"}, result="{...}"}]
          content="北京今天天气晴朗，温度25°C..."
```

**说明：**
- 工具调用结果直接存储在 `tool_calls[].result` 字段中
- 不再创建独立的 `role=tool` 消息
- 前端可通过 `tool_calls` 数组展示完整的工具调用过程

---

## 前端特性

### 工具调用控制

- 工具调用开关位于输入框右侧（扳手图标）
- 状态存储在浏览器 localStorage（`tools_enabled`）
- 默认开启，可通过请求参数 `tools_enabled` 控制每次请求

### 消息渲染

- 助手消息的 `tool_calls` 通过可折叠面板展示
- 面板显示：思考过程 → 工具调用 → 工具结果
- 每个子项可独立展开/折叠
