# Chatbot API

把命令行聊天机器人改造成 FastAPI 服务：多会话连续对话、流式输出，外加一个学习功能（英语单词讲解）。

## 功能

- 多会话连续对话：`session_id` 由调用方提供，同一 ID 带历史，不同 ID 互不串话
- 流式输出：`/chat/stream` 边生成边返回纯文本
- 会话管理：列出会话、查看消息记录、清空会话
- 学习功能：`/study/word` 讲解英语单词（词性、释义、搭配、例句）
- 配置集中在 `config.py`，用 `.env` 覆盖；API Key 用 `SecretStr` 保存，不会出现在日志和响应里
- 27 个离线单元测试，不联网、不需要真实 API Key

## 目录结构

    .
    ├── app/
    │   ├── main.py      # FastAPI 应用与路由
    │   ├── schemas.py   # 请求 / 响应模型（含校验）
    │   ├── store.py     # 内存会话存储：所有会话读写都在这里，换数据库只需改这个文件
    │   ├── study.py     # 学习功能：单词讲解
    │   └── deps.py      # 依赖注入：配置、存储、模型客户端
    ├── config.py        # 全部可变配置
    ├── llm.py           # 大模型调用封装（流式 / 非流式）
    ├── cli.py           # 命令行版（上一版作业，仍可运行）
    ├── tests/           # 27 个离线测试
    ├── requirements.txt
    └── requirements-dev.txt

## 快速开始

    python -m venv .venv
    source .venv/bin/activate          # Windows: .venv\Scripts\activate
    pip install -r requirements-dev.txt
    cp .env.example .env               # Windows: copy .env.example .env
    # 编辑 .env，填入 CHATBOT_API_KEY

启动服务：

    uvicorn app.main:app --reload

- 服务地址：http://127.0.0.1:8000
- 交互式文档（可直接点着测）：http://127.0.0.1:8000/docs

命令行版仍在：`python cli.py`

## 配置

所有可变参数都在 `config.py`，可用 `.env` 或环境变量覆盖（前缀 `CHATBOT_`）。`.env` 已写入 `.gitignore`。

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `CHATBOT_API_KEY` | 空 | 接口密钥，`SecretStr` 保存，打印只显示 `**********` |
| `CHATBOT_BASE_URL` | `https://api.openai.com/v1` | OpenAI 兼容接口地址 |
| `CHATBOT_MODEL` | `gpt-4o-mini` | 模型名 |
| `CHATBOT_TEMPERATURE` | `0.7` | 0~2，越界抛 `ValidationError` |
| `CHATBOT_MAX_TOKENS` | `1024` | 单次回复上限 |
| `CHATBOT_SYSTEM_PROMPT` | 中文助手提示词 | 对话用的 system prompt |
| `CHATBOT_STUDY_SYSTEM_PROMPT` | 英语老师提示词 | 单词讲解用的 system prompt |
| `CHATBOT_HISTORY_LIMIT` | `20` | 每次请求最多携带多少条历史 |

## 接口

### POST /chat — 一问一答（非流式）

    curl -X POST http://127.0.0.1:8000/chat \
      -H "Content-Type: application/json" \
      -d '{"session_id": "u1", "message": "我叫小明，请记住"}'

    {"session_id": "u1", "reply": "好的，小明，我记住了。"}

同一 `session_id` 再来一次，会带上之前的对话：

    curl -X POST http://127.0.0.1:8000/chat \
      -H "Content-Type: application/json" \
      -d '{"session_id": "u1", "message": "我叫什么名字？"}'

    {"session_id": "u1", "reply": "你叫小明。"}

换个 `session_id`（比如 `u2`）问同样的问题，它答不出——会话之间互不影响。

### POST /chat/stream — 流式问答

请求体与 `/chat` 相同，响应是逐块返回的纯文本（`text/plain`）。`curl` 要加 `-N` 关闭缓冲，才能看到一段段输出：

    curl -N -X POST http://127.0.0.1:8000/chat/stream \
      -H "Content-Type: application/json" \
      -d '{"session_id": "u1", "message": "用三句话介绍杭州"}'

流结束后，完整回复同样会写入该会话的历史记录，可以用下面的接口查到。

### GET /sessions — 会话列表

    curl http://127.0.0.1:8000/sessions

    {"sessions": ["u1", "u2"]}

### GET /sessions/{session_id}/messages — 消息记录

    curl http://127.0.0.1:8000/sessions/u1/messages

    {"session_id": "u1",
     "messages": [
       {"role": "user", "content": "我叫小明，请记住"},
       {"role": "assistant", "content": "好的，小明，我记住了。"}
     ]}

按对话顺序返回，每条只有 `role`（`user` / `assistant`）和 `content` 两个字段，前端可以直接渲染成气泡。

### DELETE /sessions/{session_id} — 清空会话

    curl -X DELETE http://127.0.0.1:8000/sessions/u1

返回 `204 No Content`。清空后会话仍然存在，消息记录为空数组，可以继续用同一个 `session_id` 对话。

### POST /study/word — 学习功能：单词讲解

    curl -X POST http://127.0.0.1:8000/study/word \
      -H "Content-Type: application/json" \
      -d '{"word": "serendipity"}'

    {"word": "serendipity",
     "explanation": "名词：意外发现美好事物的运气……"}

讲解包含词性与释义、常见搭配、一个例句及翻译。这个接口**不接入对话会话**，不读写历史，也不会影响 `/chat` 的上下文。

### GET /health — 探活

    curl http://127.0.0.1:8000/health

    {"status": "ok"}

## 错误码

| 状态码 | 场景 |
| --- | --- |
| `404` | 查询或清空不存在的会话 |
| `422` | 消息为空 / 只有空白字符，或 `session_id` 为空 |
| `502` | 上游模型调用失败（网络、鉴权、限流等），响应里只给出异常类型，不含密钥 |

## 测试

    pytest

27 个用例，全部离线：用 `TestClient` 发请求，用 `tests/fake_model.py` 替换模型客户端，不会真的调用接口。

- `tests/test_api_chat.py`：同会话连续对话、跨会话隔离、空消息被拒、模型异常回滚、单词讲解接口
- `tests/test_api_sessions.py`：会话列表、消息顺序、清空、404
- `tests/test_api_stream.py`：模型收到 `stream=True`、流式内容正确、完整回复写入历史
- `tests/test_config.py`、`tests/test_llm.py`：配置校验与模型调用参数（上一版作业）

## 设计说明

- **会话存储集中在一个模块**：`app/store.py` 是唯一读写会话的地方，路由只调用它的方法。以后换成 Redis/PostgreSQL，只需要重写这个类，路由代码不用动。
- **依赖注入便于测试**：`app/deps.py` 提供 `get_store` / `get_client`，测试里用 `app.dependency_overrides` 整包替换成假实现，所以测试完全不联网。
- **流式结束才写历史**：`/chat/stream` 在生成器里边发边累加，正常结束才把完整回复写入会话；中途失败会撤销那条提问，保证 user / assistant 成对。

## 在 Windows PowerShell 里调用

`curl` 的引号在 PowerShell 里容易被吃掉，建议用原生命令：

    $body = @{ session_id = "u1"; message = "你好" } | ConvertTo-Json
    Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/chat `
      -ContentType "application/json; charset=utf-8" -Body $body