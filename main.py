"""命令行聊天机器人入口：多轮对话 + 配置校验。"""

from __future__ import annotations

import argparse
import sys

from pydantic import ValidationError

from config import Settings, get_settings
from llm import ChatClient

BANNER = "CLI Chatbot —— 输入 /help 查看命令，/exit 退出"

HELP = """可用命令：
  /help   显示本帮助
  /clear  清空上下文，开始新话题
  /exit   退出程序（Ctrl+C、Ctrl+D 同样有效）"""


def load_settings() -> Settings:
    """读取配置，并把校验错误翻译成可读的中文提示。"""
    try:
        return get_settings()
    except ValidationError as exc:
        print("配置有误，请检查 .env 中的取值：", file=sys.stderr)
        for err in exc.errors():
            field = ".".join(str(part) for part in err["loc"]) or "配置"
            print(f"  - CHATBOT_{field.upper()}: {err['msg']}", file=sys.stderr)
        raise SystemExit(2) from exc


def chat_loop(client: ChatClient) -> None:
    history: list[dict[str, str]] = []
    while True:
        try:
            raw = input("\n你> ")
        except (EOFError, KeyboardInterrupt):
            print("\n再见！")
            return

        text = raw.strip()
        if not text:
            continue
        if text in {"/exit", "/quit"}:
            print("再见！")
            return
        if text == "/help":
            print(HELP)
            continue
        if text == "/clear":
            history.clear()
            print("上下文已清空。")
            continue

        history.append({"role": "user", "content": text})
        try:
            reply = client.reply(history)
        except Exception as exc:  # 网络 / 鉴权 / 限流等
            print(f"\n[请求失败] {type(exc).__name__}: {exc}", file=sys.stderr)
            history.pop()  # 丢掉这条没有回复的提问，保证 user / assistant 成对
            continue

        print(f"助手> {reply}")
        history.append({"role": "assistant", "content": reply})


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="命令行对话机器人")
    parser.add_argument("--show-config", action="store_true", help="打印当前配置后退出")
    args = parser.parse_args(argv)

    settings = load_settings()

    if args.show_config:
        print(settings)
        return 0

    if not settings.api_key.get_secret_value().strip():
        print("未配置 API Key。", file=sys.stderr)
        print("请把 .env.example 复制为 .env，并填写 CHATBOT_API_KEY=sk-xxxx", file=sys.stderr)
        print("  Windows: copy .env.example .env", file=sys.stderr)
        print("  macOS/Linux: cp .env.example .env", file=sys.stderr)
        return 1

    print(BANNER)
    print(f"模型: {settings.model} | 地址: {settings.base_url} | 温度: {settings.temperature}")
    chat_loop(ChatClient(settings))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())