# 对话系统后端 API 设计

## API 总览

### 会话管理

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/conversations` | 创建会话 |
| `GET` | `/api/conversations` | 获取会话列表 |
| `GET` | `/api/conversations/:id` | 获取会话详情 |
| `PATCH` | `/api/conversations/:id` | 更新会话 |
| `DELETE` | `/api/conversations/:id` | 删除会话 |

### 消息管理

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/conversations/:id/messages` | 获取消息列表 |
| `POST` | `/api/conversations/:id/messages` | 发送消息（对话补全，支持 `stream` 流式） |
| `DELETE` | `/api/conversations/:id/messages/:message_id` | 删除消息 |

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
        "created_at": "2026-03-24T10:00:00Z"
      },
      {
        "id": "msg_002",
        "conversation_id": "conv_abc123",
        "role": "assistant",
        "content": "你好！有什么可以帮你的？",
        "token_count": 15,
        "thinking_content": null,
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
  "stream": true
}
```

**流式响应 (stream=true)：**

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

### 3. SSE 事件说明

| 事件         | 说明                              |
| ---------- | ------------------------------- |
| `thinking` | 思维链增量内容（启用时）                    |
| `message`  | 回复内容的增量片段                       |
| `error`    | 错误信息                            |
| `done`     | 回复结束，携带完整 message_id 和 token 统计 |

---

### 4. 错误码

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
| `role`             | enum          | `user` / `assistant` / `system` |
| `content`          | string        | 消息内容                            |
| `token_count`      | integer       | token 消耗数                       |
| `thinking_content` | string        | 思维链内容（启用时）                      |
| `created_at`       | datetime      | 创建时间                            |
