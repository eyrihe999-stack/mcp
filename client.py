"""
LangChain + MCP 客户端：连接外部 MCP 服务，将工具交给 LangChain Agent 使用。

用法:
  # 使用内置示例数学服务（需先设置 OPENAI_API_KEY 或 ANTHROPIC_API_KEY）
  python client.py

  # 指定 MCP 服务（stdio：本地命令）
  python client.py --server math:stdio:python:servers/math_server.py

  # 仅列出远程工具（不调用 LLM）
  python client.py --list-tools --server math:stdio:python:servers/math_server.py
"""
import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _parse_server_arg(s: str) -> tuple[str, dict]:
    """解析 --server 参数，格式: name:transport:command:args 或 name:transport:url
    示例: math:stdio:python:servers/math_server.py
          weather:http:http://localhost:8000/mcp
    """
    parts = s.split(":", 3)
    if len(parts) < 3:
        raise ValueError("--server 格式: name:transport:command:args 或 name:transport:url")
    name, transport = parts[0], parts[1]
    rest = ":".join(parts[2:])
    if transport == "stdio":
        idx = rest.find(":")
        command = rest[:idx] if idx >= 0 else rest
        args = [rest[idx + 1 :]] if idx >= 0 else []
        return name, {"transport": "stdio", "command": command, "args": args}
    if transport == "http":
        return name, {"transport": "http", "url": rest}
    raise ValueError(f"不支持的 transport: {transport}")


async def run_agent(server_config: dict, list_tools_only: bool = False) -> None:
    from langchain_mcp_adapters.client import MultiServerMCPClient

    client = MultiServerMCPClient(server_config)
    tools = await client.get_tools()

    if list_tools_only:
        print("已连接 MCP 服务，可用工具：")
        for t in tools:
            print(f"  - {t.name}: {t.description or '(无描述)'}")
        return

    # 选择 LLM：优先 OpenAI，其次 Anthropic
    llm = None
    if os.getenv("OPENAI_API_KEY"):
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    if llm is None and os.getenv("ANTHROPIC_API_KEY"):
        from langchain_anthropic import ChatAnthropic
        llm = ChatAnthropic(model="claude-sonnet-4-20250514", temperature=0)
    if llm is None:
        print("请设置 OPENAI_API_KEY 或 ANTHROPIC_API_KEY（.env 或环境变量）后再运行对话。", file=sys.stderr)
        print("仅列出工具：使用 --list-tools", file=sys.stderr)
        # 仍然列出工具
        print("\n当前 MCP 工具：")
        for t in tools:
            print(f"  - {t.name}: {t.description or '(无描述)'}")
        return

    llm_with_tools = llm.bind_tools(tools)
    from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

    messages = []
    print("LangChain MCP 客户端已就绪。输入问题（可要求使用数学计算），输入 quit 退出。\n")

    while True:
        try:
            user_input = input("你: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            break

        messages.append(HumanMessage(content=user_input))

        while True:
            response = await asyncio.to_thread(llm_with_tools.invoke, messages)
            messages.append(response)

            if not response.tool_calls:
                # 最终文本回复
                if isinstance(response.content, str):
                    text = response.content
                elif response.content and isinstance(response.content, list):
                    text = response.content[0].get("text", str(response.content[0])) if response.content else ""
                else:
                    text = str(response.content)
                print(f"\n助手: {text}\n")
                break

            # 执行工具调用
            for tc in response.tool_calls:
                name = tc["name"]
                args = tc.get("args") or {}
                tid = tc["id"]
                # 从 MCP 适配器得到的 tool 是 LangChain BaseTool，可直接 invoke
                tool = next((t for t in tools if t.name == name), None)
                if not tool:
                    content = f"未知工具: {name}"
                else:
                    try:
                        result = await asyncio.to_thread(tool.invoke, args)
                        content = result if isinstance(result, str) else str(result)
                    except Exception as e:
                        content = f"工具执行错误: {e}"
                messages.append(ToolMessage(content=content, tool_call_id=tid))


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="LangChain MCP 客户端")
    parser.add_argument("--server", "-s", action="append", default=None,
                        help="MCP 服务配置，可多次指定。格式: name:transport:command:args 或 name:transport:url")
    parser.add_argument("--list-tools", action="store_true", help="仅列出远程工具并退出")
    args = parser.parse_args()

    if args.server:
        server_config = {}
        for s in args.server:
            name, config = _parse_server_arg(s)
            server_config[name] = config
    else:
        # 默认：当前目录下的数学示例服务
        root = Path(__file__).resolve().parent
        server_script = root / "servers" / "math_server.py"
        if not server_script.exists():
            print(f"默认 MCP 服务脚本不存在: {server_script}", file=sys.stderr)
            print("请使用 --server 指定服务，例如:", file=sys.stderr)
            print("  --server math:stdio:python:servers/math_server.py", file=sys.stderr)
            sys.exit(1)
        server_config = {
            "math": {
                "transport": "stdio",
                "command": sys.executable,
                "args": [str(server_script)],
            }
        }

    asyncio.run(run_agent(server_config, list_tools_only=args.list_tools))


if __name__ == "__main__":
    main()
