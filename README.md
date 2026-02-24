# MCP 客户端（LangChain + Python）

使用 **LangChain** 与 **langchain-mcp-adapters** 连接外部 MCP（Model Context Protocol）服务，将远程工具暴露给 LangChain Agent 使用。

## 环境准备

```bash
# 创建虚拟环境（推荐）
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

可选：复制 `.env.example` 为 `.env`，填入 `OPENAI_API_KEY` 或 `ANTHROPIC_API_KEY`，用于对话时的 LLM。

## 怎么把服务器跑起来

有两种用法，任选其一即可。

### 方式一：不单独起服务器（推荐先试）

MCP 使用 **stdio** 时，**不需要你先启动服务器**。直接运行客户端，客户端会自动在背后启动 `math_server.py` 子进程并与之通信：

```bash
# 列出工具
python client.py --list-tools

# 对话（会自动拉起数学 MCP 服务）
python client.py
```

也就是说：**跑客户端 = 服务器已被自动跑起来**。

### 方式二：先单独起一个 HTTP 服务器

若你想在“一个终端跑服务、另一个终端跑客户端”，可以用 HTTP 版数学服务：

**终端 1 - 启动 MCP 服务器：**

```bash
python servers/math_server_http.py
```

默认监听 `http://127.0.0.1:8000/mcp`，看到类似 “Uvicorn running on ...” 即表示已跑起来。

**终端 2 - 启动客户端并连接该服务：**

```bash
python client.py --server math:http:http://127.0.0.1:8000/mcp
```

---

## 运行方式

### 1. 使用内置示例 MCP 服务（数学计算）

项目自带用 FastMCP 写的数学服务：

- `servers/math_server.py`：stdio 模式，由客户端自动启动。
- `servers/math_server_http.py`：HTTP 模式，可单独运行（见上方「方式二」）。

提供工具：`add`、`multiply`、`power`。

```bash
# 仅列出远程工具（不需要 API Key）
python client.py --list-tools

# 启动对话（需要设置 OPENAI_API_KEY 或 ANTHROPIC_API_KEY）
python client.py
```

在对话中可输入例如：“(3+5) 再乘以 12 等于多少？” 助手会通过 MCP 调用数学工具并回答。

### 2. 指定外部 MCP 服务

**stdio（本地子进程）：**

```bash
python client.py --server math:stdio:python:servers/math_server.py
```

**HTTP 远程服务：**

```bash
python client.py --server weather:http:http://localhost:8000/mcp
```

可多次使用 `--server` 连接多个 MCP 服务。

## 项目结构

```
mcp/
├── client.py           # LangChain MCP 客户端入口
├── requirements.txt
├── .env.example
├── servers/
│   ├── __init__.py
│   └── math_server.py  # 示例 MCP 服务（FastMCP）
└── README.md
```

## 技术说明

- **MCP 客户端**：`langchain-mcp_adapters.MultiServerMCPClient` 连接一个或多个 MCP 服务，`get_tools()` 得到 LangChain 可用的工具列表。
- **传输方式**：支持 `stdio`（本地命令）和 `http`（远程 URL）。
- **对话流程**：使用 LangChain 的 ChatOpenAI/ChatAnthropic + `bind_tools`，根据模型返回的 `tool_calls` 调用对应 MCP 工具，将结果写回对话并继续生成回复。
