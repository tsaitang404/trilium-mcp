# trilium-mcp

将 Trilium Notes ETAPI 封装为 MCP 服务。

## 环境准备

```bash
# 使用 pyenv 管理 Python 版本
pyenv local 3.11.14

# 创建虚拟环境（首次）
python -m venv .venv
source .venv/bin/activate

# 安装依赖
uv pip install -e ".[dev]"
```

## 架构

- `FastMCP` 作为 MCP server 框架（`mcp.server.fastmcp`）
- `trilium-py`（`ETAPI` 类）作为 Trilium ETAPI 的 Python 封装
- 所有 MCP tool 内部调用 `ETAPI` 方法，不直接发 HTTP 请求
- `ETAPI` 客户端通过 `lifespan` 在 server 启动时初始化一次，注入到 tool context
- 返回结构化 Pydantic 模型以利用 MCP structured output

## 快速命令

```bash
# 运行测试
.venv/bin/python -m pytest tests/ -v

# 测试覆盖率
.venv/bin/python -m coverage run -m pytest tests/ && .venv/bin/python -m coverage report -m

# stdio 模式（MCP 客户端默认方式）
TRILIUM_URL=http://localhost:8080 TRILIUM_TOKEN=xxx .venv/bin/trilium-mcp

# SSE 模式（开发调试用，可通过 Inspector 连接）
TRILIUM_URL=... TRILIUM_TOKEN=... TRILIUM_MCP_TRANSPORT=sse .venv/bin/trilium-mcp
npx @modelcontextprotocol/inspector

# Streamable HTTP 模式
TRILIUM_URL=... TRILIUM_TOKEN=... TRILIUM_MCP_TRANSPORT=streamable-http .venv/bin/trilium-mcp
```

## 环境变量

| 变量 | 必填 | 说明 |
|------|------|------|
| `TRILIUM_URL` | 是 | Trilium 服务地址，如 `http://localhost:8080` |
| `TRILIUM_TOKEN` | 是 | ETAPI Token（在 Trilium Options -> ETAPI 中获取） |
| `TRILIUM_MCP_TRANSPORT` | 否 | 传输模式：`stdio`（默认）、`sse`、`streamable-http` |

`.env.example` 已提供，首次使用复制为 `.env` 并填入实际值。

## Docker

```bash
# 构建并启动
cp .env.example .env   # 编辑 .env 填入实际 TRILIUM_URL 和 TRILIUM_TOKEN
docker compose up -d

# 查看日志
docker compose logs -f

# 停止
docker compose down
```

默认使用 `streamable-http` 传输模式，监听 `0.0.0.0:8000`。
对于 macOS/Windows 上的本地 Trilium 实例，`TRILIUM_URL` 设为 `http://host.docker.internal:8080`。

## 项目结构

```
trilium-mcp/
  src/trilium_mcp/
    __init__.py     # 包标记
    main.py         # FastMCP server 入口 + 全部 tool 定义
    models.py       # Pydantic 结构化输出模型
  tests/
  pyproject.toml
  AGENTS.md
```

## 关键约定

- 每个 tool 使用 `@mcp.tool(name=...)` 注册为 MCP tool，对外名称用 snake_case
- Tool 通过 `ctx: Context[ServerSession, AppContext]` 参数获取 `ETAPI` 客户端：
  `ctx.request_context.lifespan_context.ea`
- 返回值尽可能使用 Pydantic model（`models.py` 中定义），以获得结构化输出
- 安全处理：鉴权信息仅从环境变量读取，绝不硬编码
- 新增 tool 时先在 `models.py` 定义返回模型，再到 `main.py` 添加 tool 函数

## 传输模式

- **stdio**（默认）：适用于 Claude Desktop 等 MCP 客户端，通过 stdin/stdout 通信
- **sse**：基于 SSE 的 HTTP 传输，适用于 MCP Inspector 调试，监听 `http://127.0.0.1:8000`
- **streamable-http**：支持 CORS 和 ASGI 挂载，适用于生产环境

通过 `TRILIUM_MCP_TRANSPORT` 环境变量切换模式。

## MCP 调试

```bash
# 列出所有注册的 tool（不需要 Trilium 服务）
.venv/bin/python -c "
from trilium_mcp.main import mcp
for t in mcp._tool_manager._tools.values():
    print(f'{t.name}: {t.description}')
"

# MCP Inspector 交互调试
TRILIUM_URL=... TRILIUM_TOKEN=... TRILIUM_MCP_TRANSPORT=sse .venv/bin/trilium-mcp
npx @modelcontextprotocol/inspector
# 在 Inspector UI 中连接 http://127.0.0.1:8000
```

## 参考

- MCP Python SDK: https://github.com/modelcontextprotocol/python-sdk
- Trilium ETAPI 文档: https://docs.triliumnotes.org/user-guide/advanced-usage/etapi
- trilium-py: https://github.com/Nriver/trilium-py
