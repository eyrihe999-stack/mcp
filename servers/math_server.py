"""
示例 MCP 服务：提供数学计算工具，供 LangChain 客户端连接调用。
运行: python -m servers.math_server 或 uv run python servers/math_server.py
"""
from fastmcp import FastMCP

# 某些版本的 fastmcp 不支持 description 关键字参数，这里只传名称即可
mcp = FastMCP("Math")


@mcp.tool()
def add(a: float, b: float) -> float:
    """两数相加。"""
    return a + b


@mcp.tool()
def multiply(a: float, b: float) -> float:
    """两数相乘。"""
    return a * b


@mcp.tool()
def power(base: float, exponent: float) -> float:
    """计算 base 的 exponent 次方。"""
    return base**exponent


if __name__ == "__main__":
    mcp.run(transport="stdio")
