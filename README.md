# trilium-mcp

将 [Trilium Notes](https://github.com/zadam/trilium) 的 ETAPI 封装为 [MCP](https://modelcontextprotocol.io)（Model Context Protocol）服务，使 AI 客户端（如 Claude Desktop）可直接读写 Trilium 笔记。

## 特性

- 通过 MCP 协议暴露 Trilium 全部 ETAPI 功能
- 支持三种传输模式：`stdio`、`sse`、`streamable-http`
- 内置 Bearer Token 鉴权（默认开启）
- 结构化输出（Pydantic models）利于 AI 消费
- 提供 Docker 镜像一键部署

## 可用工具

| 名称 | 说明 |
|------|------|
| `app_info` | 获取 Trilium 服务器信息 |
| `search_notes` | 搜索笔记（支持全文搜索、正则匹配） |
| `search_by_title` | 按标题精确搜索笔记 |
| `get_note` | 获取笔记元数据 |
| `get_note_content` | 获取笔记 HTML 内容 |
| `create_note` | 创建笔记（text / code / file / image 等） |
| `create_image_note` | 从本地图片文件创建图片笔记 |
| `update_note_content` | 更新笔记内容 |
| `patch_note` | 修改笔记标题 |
| `delete_note` | 删除笔记（不可恢复，谨慎使用） |
| `create_branch` | 克隆笔记到另一父节点（创建分支/克隆） |
| `create_attribute` | 为笔记创建标签（label）或关系（relation） |
| `export_note` | 导出笔记为文件 |
| `import_note` | 从 zip 文件导入笔记 |
| `get_day_note` | 获取指定日期日记内容 |
| `set_day_note` | 设置/更新日记内容 |
| `add_todo` | 在日记中添加 TODO 项 |
| `todo_check` | 勾选/取消勾选 TODO 项 |
| `update_todo` | 更新 TODO 项描述 |
| `delete_todo` | 删除 TODO 项 |
| `move_yesterday_unfinished_todo` | 将昨天未完成的 TODO 迁移到今天 |
| `traverse_note_tree` | 遍历笔记树（支持 DFS/BFS、深度/数量限制） |
| `beautify_note` | 美化笔记排版 |
| `save_revision` | 手动保存笔记版本快照 |
| `get_backup` | 创建数据库备份 |
| `get_attachments` | 获取笔记附件列表 |

## 快速开始

### 前置条件

- Python 3.11+
- 一个可访问的 Trilium 实例
- ETAPI Token（在 Trilium 菜单 Options → ETAPI 中获取）

### 本地运行

```bash
# 安装
pip install trilium-mcp

# 运行（stdio 模式，适用于 Claude Desktop）
TRILIUM_URL=http://localhost:8080 TRILIUM_TOKEN=your_token trilium-mcp

# 或使用 streamable-http 模式
TRILIUM_URL=http://localhost:8080 TRILIUM_TOKEN=your_token \
  TRILIUM_MCP_TRANSPORT=streamable-http trilium-mcp
```

### Docker

```bash
# 1. 准备配置
cp .env.example .env
# 编辑 .env 填入 TRILIUM_URL 和 TRILIUM_TOKEN

# 2. 启动
docker compose up -d

# 3. 查看日志
docker compose logs -f
```

默认使用 `streamable-http` 传输模式，监听 `0.0.0.0:8000`。
对于 macOS/Windows 上的本地 Trilium 实例，`TRILIUM_URL` 设为 `http://host.docker.internal:8080`。

## 配置

### 环境变量

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `TRILIUM_URL` | 是 | `http://localhost:8080` | Trilium 服务地址 |
| `TRILIUM_TOKEN` | 是 | - | ETAPI Token |
| `TRILIUM_MCP_TOKEN` | 否 | 同 `TRILIUM_TOKEN` | 单独为 MCP 鉴权配置 token |
| `TRILIUM_MCP_TRANSPORT` | 否 | `stdio` | 传输模式：`stdio` / `sse` / `streamable-http` |
| `TRILIUM_MCP_AUTH_DISABLED` | 否 | `false` | 关闭 MCP Bearer Token 鉴权（设为 `true`/`1`/`yes`） |

### MCP 鉴权说明

- 默认使用 `TRILIUM_TOKEN` 作为 MCP Bearer Token 进行鉴权
- 可通过 `TRILIUM_MCP_TOKEN` 为 MCP 单独配置 token（优先级高于 `TRILIUM_TOKEN`）
- 所有 HTTP 请求需要在 `Authorization` 头中携带 `Bearer <token>`
- 设置 `TRILIUM_MCP_AUTH_DISABLED=true` 可关闭鉴权（适用于本地调试或已有反向代理鉴权的场景）

```bash
# 带鉴权的请求示例
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_token" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"client","version":"1"}}}'
```

## 传输模式

### stdio（默认）
适用于 Claude Desktop 等 MCP 客户端，通过标准输入/输出通信。

```bash
TRILIUM_URL=... TRILIUM_TOKEN=... trilium-mcp
```

### SSE
基于 Server-Sent Events 的 HTTP 传输，适用于 MCP Inspector 调试。

```bash
TRILIUM_URL=... TRILIUM_TOKEN=... TRILIUM_MCP_TRANSPORT=sse trilium-mcp
```

然后使用 Inspector 连接：
```bash
npx @modelcontextprotocol/inspector
```

### Streamable HTTP
支持 CORS 和 ASGI 挂载的生产环境推荐方案，也是 Docker 部署的默认模式。

```bash
TRILIUM_URL=... TRILIUM_TOKEN=... TRILIUM_MCP_TRANSPORT=streamable-http trilium-mcp
```

## 开发

```bash
# 使用 pyenv 管理 Python 版本
pyenv local 3.11.14

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate

# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest tests/ -v

# 列出所有注册的 tool
python -c "
from trilium_mcp.main import mcp
for t in mcp._tool_manager._tools.values():
    print(f'{t.name}: {t.description}')
"
```

## 架构

```
┌──────────────┐     MCP Protocol     ┌───────────────┐
│  AI Client   │ ◄──────────────────► │  trilium-mcp  │
│ (Claude etc) │    stdio/SSE/HTTP    │   FastMCP     │
└──────────────┘                      └───────┬───────┘
                                              │ ETAPI (HTTP)
                                              ▼
                                       ┌──────────────┐
                                       │   Trilium    │
                                       │    Notes     │
                                       └──────────────┘
```

- `FastMCP` 作为 MCP server 框架
- `trilium-py` 的 `ETAPI` 类封装 Trilium ETAPI 调用
- 所有 MCP tool 内部调用 `ETAPI` 方法，不直接发 HTTP 请求
- 返回 Pydantic 模型以利用 MCP structured output

## 项目结构

```
trilium-mcp/
  src/trilium_mcp/
    __init__.py     # 包标记
    main.py         # FastMCP server 入口 + tool 定义
    models.py       # Pydantic 结构化输出模型
  tests/
  Dockerfile
  docker-compose.yml
  pyproject.toml
```

## 参考

- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [Trilium ETAPI 文档](https://docs.triliumnotes.org/user-guide/advanced-usage/etapi)
- [trilium-py](https://github.com/Nriver/trilium-py)
- [Model Context Protocol](https://modelcontextprotocol.io)
