"""
数学 MCP 服务 - HTTP 模式：单独起一个进程，在端口上监听，供客户端通过 URL 连接。

运行（在项目根目录）:
  python servers/math_server_http.py

默认地址: http://127.0.0.1:8000/mcp
客户端连接: python client.py --server math:http:http://127.0.0.1:8000/mcp
"""
from fastmcp import FastMCP

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
    # 以 HTTP 方式运行，方便单独“把服务器跑起来”
    mcp.run(transport="streamable-http", host="127.0.0.1", port=8000)
