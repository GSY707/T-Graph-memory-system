# Memory System MCP

一个面向 MCP 客户端的长期记忆服务器与记忆引擎原型。

这是一个树图混合架构的记忆方案，树用于LOD（level of details）记忆加载，图用于关联推理。这个记忆方案适合保存长的，关联性强的，经常更新的记忆内容。

这个仓库提供两部分内容：

- Python MCP 服务器：把树 + 图混合记忆结构暴露为可调用工具。
- 可选的 VS Code 扩展子项目：帮助把打包后的 MCP 可执行文件注入到常见客户端配置中。

当前实现重点在于工作区级独立记忆、主动回忆、记忆关联和软遗忘机制，适合作为本地 AI 助手长期记忆的实验基础。

## 特性

- 工作区隔离记忆：每个工作区使用自己的 .memory-system/memory_mcp_snapshot.json。
- 树图混合结构：父子层级表达主题结构，关联边表达跨主题联想。
- 主动回忆：基于关键词相关性、重要性、新近度和权重综合排序。
- 软遗忘：通过衰减权重而不是物理删除来模拟遗忘。
- 文档冷启动：首次启动时可从工作区根目录的 README、概念、方案类文档生成初始记忆。
- MCP 工具接口：支持 recall、recall_detail、browse_tree、memory_write、memory_link、memory_modify、apply_forgetting、memory_stats。

## 仓库结构

```text
.
├─ memory_mcp_server.py          # MCP 服务器入口
├─ memory_mcp_server.spec        # PyInstaller 打包配置
├─ memory_system/                # 核心记忆引擎
│  ├─ node.py                    # 记忆节点与关联边
│  ├─ memory_store.py            # 树图混合存储
│  ├─ recall_engine.py           # 主动回忆算法
│  ├─ forgetting.py              # 软遗忘机制
│  ├─ loader.py                  # 工作区文档初始化逻辑
│  └─ __init__.py
├─ .vscode/
│  ├─ mcp.json                   # VS Code 工作区示例配置
│  └─ memory-system.instructions.md
└─ memory-system-dev/            # 可选 VS Code 扩展项目
```

## 运行要求

- Python 3.11+
- Node.js 18+（仅当你需要构建 memory-system-dev 扩展时）

## 安装

### 运行 Python MCP 服务器

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python memory_mcp_server.py
```

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python memory_mcp_server.py
```

### VS Code 工作区配置

仓库内已经附带一个最小示例配置 [.vscode/mcp.json](.vscode/mcp.json)。核心思路是让 MCP 进程在当前工作区启动，这样服务器会把状态写入当前工作区自己的 .memory-system 目录。

示例：

```json
{
  "servers": {
    "memory-system": {
      "type": "stdio",
      "command": "python",
      "args": ["memory_mcp_server.py"],
      "cwd": "${workspaceFolder}"
    }
  }
}
```

如果你运行的是打包后的可执行文件，也可以显式传入环境变量 MEMORY_WORKSPACE_ROOT，让服务器把记忆绑定到指定工作区。

## 工作方式

### 1. 首次启动

服务器会按下面的顺序初始化：

1. 读取当前工作区的 .memory-system/memory_mcp_snapshot.json。
2. 如果当前工作区就是服务器源码所在目录，则兼容迁移旧版根目录快照。
3. 尝试读取工作区根目录下的 README、概念、方案、设计、架构类文档。
4. 如果都不存在，则以空记忆库启动。

### 2. 记忆存储

- 根目录下不会再共享一份全局快照。
- 每个工作区的记忆状态只写入它自己的 .memory-system/。
- 这个目录已经被 [.gitignore](.gitignore) 忽略，适合本地长期积累，不应提交到仓库。

### 3. MCP 工具

| 工具 | 说明 |
| --- | --- |
| recall(query, top_k) | 主动回忆相关记忆 |
| recall_detail(node_name) | 查看单个节点详情 |
| browse_tree(max_depth) | 浏览树形结构 |
| memory_write(name, content, parent_name, importance, tags) | 写入新记忆 |
| memory_link(source_name, target_name, relation) | 创建关联边 |
| memory_modify(name, content, importance) | 修改已有记忆 |
| apply_forgetting() | 执行软遗忘衰减 |
| memory_stats() | 查看记忆库统计 |

## memory-system-dev 扩展

[memory-system-dev](memory-system-dev) 是一个可选的 VS Code 扩展子项目，用来把打包后的 MCP 可执行文件注入到常见 AI 客户端配置中。

构建方式：

```bash
cd memory-system-dev
npm install
npm run compile
```

如果你要打包扩展：

```bash
cd memory-system-dev
npm install
npm run package
```

## 打包服务器

仓库包含 [memory_mcp_server.spec](memory_mcp_server.spec)，可用于 PyInstaller 打包：

```bash
python -m pip install pyinstaller
pyinstaller memory_mcp_server.spec
```

## 开发说明

- 运行时快照和测试记忆不应提交。
- API key、.env、keys.yaml 等敏感配置应保留在本地。
- 如果你修改并公开部署了这个服务器，AGPL-3.0 要求你向通过网络与之交互的用户提供对应源码。

## 许可证

本项目使用 GNU Affero General Public License v3.0 or later 发布。详见 [LICENSE](LICENSE)。
