# Chatbot 项目（后端 API + Vue 前端）

一个聊天机器人项目：后端是基于 FastAPI 的对话服务（多会话、流式输出、SQLite 持久化、关键词搜索），
前端目前只是 `npm create vue@latest` 生成的**空脚手架**，尚未接入 API。

## 目录结构

    .
    ├── backend/            # FastAPI 服务（Python）
    │   ├── src/chatbot/    # 源码：app/（路由、存储、ORM 模型）、config.py、llm.py、cli.py
    │   ├── tests/          # 44 个离线单元测试
    │   ├── pyproject.toml
    │   ├── requirements.txt / requirements-dev.txt
    │   ├── .env.example    # 配置模板（真实 .env 不入库）
    │   └── README.md       # 后端详细文档：接口、配置、数据库设计、ORM 说明
    └── frontend/           # Vue 3 + Vite 空工程（本次仅脚手架）

## 后端

**所有后端命令都在 `backend/` 目录下执行。**

    cd backend
    python -m venv .venv
    .venv\Scripts\Activate.ps1          # macOS/Linux: source .venv/bin/activate
    pip install -r requirements-dev.txt
    copy .env.example .env              # 编辑 .env，填入 CHATBOT_API_KEY
    uvicorn chatbot.app.main:app --reload

- 服务地址：http://127.0.0.1:8000
- 接口文档：http://127.0.0.1:8000/docs
- 运行测试：`pytest`（44 个用例，全部离线，不需要真实 API Key）

> **必须在 `backend/` 目录下执行。** `.env` 与 SQLite 数据库 `chat.db` 都按"当前工作目录"查找，
> 在仓库根目录启动会读不到配置（报缺少 API Key），并另外新建一个空库。

数据库文件 `chat.db` 与 `.env` 都在 `.gitignore` 中，不会提交；`.env.example` 提供配置模板。

## 前端

**本次只搭脚手架，不写业务代码，也不调用后端接口。**

    cd frontend
    npm install
    npm run dev

- 开发地址：http://localhost:5173 （Vue 默认欢迎页）
- 技术栈：Vue 3 + Vite；创建时选项全选 No，因此**没有 TypeScript / Router / Pinia / 测试 / ESLint**
- 当前页面与后端无任何交互，后续课程才会把界面接到 `/chat`、`/chat/stream` 等接口

## Git 约定

- 提交信息遵循 Conventional Commits（`feat:` / `fix:` / `docs:` / `test:` / `chore:` / `refactor:`）
- 不直接向 `main` push，所有改动走功能分支 + PR
