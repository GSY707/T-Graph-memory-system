---
applyTo: "**"
---

# 记忆系统使用指南

你拥有一套基于树图混合结构的长期记忆系统（通过 MCP 工具访问）。以下是使用规范。

## 工具清单

| 工具 | 用途 |
|------|------|
| `recall(query, top_k)` | 用自然语言搜索相关记忆，返回匹配节点及评分 |
| `recall_detail(node_name)` | 查看某节点的完整信息、子节点、关联边 |
| `browse_tree(max_depth)` | 查看记忆树层级结构全貌 |
| `memory_write(name, content, parent_name, importance, tags)` | 写入新记忆节点 |
| `memory_link(source_name, target_name, relation)` | 在两个节点间建立关联边 |
| `memory_modify(name, content, importance)` | 修改已有记忆 |
| `apply_forgetting()` | 对全部记忆执行软遗忘衰减 |
| `memory_stats()` | 查看记忆库统计 |

## 核心原则

1. **先回忆，再行动**：收到任何问题时，先 `recall` 搜索已有记忆，避免重复写入或给出过时答案。
2. **树形组织，图式关联**：知识通过父子关系形成层级树，通过关联边形成跨域网络。
3. **先粗后细**：先建低精度骨架节点，再填充高精度叶子节点。
4. **写入即分类**：每条记忆必须挂在合适的父节点下，不要全挂在根节点。

## 面对新工程：从零构建记忆树

### 第一步：建立骨架（5-10 个顶层节点）

先通读项目入口文件、README、目录结构，然后建立一级分类。**不要**在这一步写入细节。

```
记忆根节点
├── 项目概览          ← 项目名、目标、技术栈、版本
├── 架构              ← 整体架构模式、分层、数据流
├── 模块              ← 按功能划分的核心模块（每个子节点是一个模块）
├── 数据模型          ← 数据库表/数据结构/核心类型
├── API与接口         ← 对外暴露的接口、路由、协议
├── 配置与部署        ← 环境变量、构建命令、部署方式
├── 依赖与工具链      ← 关键依赖、版本约束、构建工具
├── 约定与风格        ← 编码规范、命名约定、项目惯例
└── 待解决问题        ← 已知bug、技术债、TODO
```

调用示例：
```
memory_write(name="项目概览", content="MyApp - 基于 FastAPI + React 的任务管理系统，Python 3.11，PostgreSQL", parent_name="", importance=9, tags="项目,概览,FastAPI,React")
memory_write(name="架构", content="前后端分离，后端 FastAPI 提供 REST API，前端 React SPA，数据库 PostgreSQL", parent_name="", importance=8, tags="架构,分层")
memory_write(name="模块", content="核心功能模块索引", parent_name="", importance=8, tags="模块,索引")
```

### 第二步：填充模块（每个模块 3-8 个子节点）

逐个模块深入阅读代码，为每个模块创建子节点。每个子节点描述模块内的一个关键概念。

```
模块
├── 用户认证模块
│   ├── JWT令牌生成与验证
│   ├── 密码哈希策略
│   └── OAuth2第三方登录
├── 任务管理模块
│   ├── 任务CRUD逻辑
│   ├── 任务状态机
│   └── 任务分配规则
└── 通知模块
    ├── 邮件通知
    └── WebSocket实时推送
```

**importance 参考值：**
- 9-10：项目核心逻辑、不看就无法理解代码的关键信息
- 7-8：重要模块、主要接口、核心数据模型
- 5-6：辅助功能、工具函数、常规配置
- 3-4：边缘细节、临时记录
- 1-2：几乎不需要再看的琐碎信息

### 第三步：建立关联边（发现跨模块联系时）

当发现两个节点存在以下关系时，用 `memory_link` 创建关联边：
- **依赖关系**：A 模块调用了 B 模块（relation="调用"）
- **数据流向**：数据从 A 流向 B（relation="数据流入"）
- **概念相似**：A 和 B 解决类似问题（relation="类似实现"）
- **因果关系**：修改 A 必须同步修改 B（relation="需同步修改"）

```
memory_link(source_name="任务状态机", target_name="WebSocket实时推送", relation="状态变更时触发推送")
memory_link(source_name="JWT令牌生成与验证", target_name="API与接口", relation="所有接口依赖认证")
```

### 第四步：持续维护

- **发现新信息**时：写入到合适的父节点下
- **发现错误**时：用 `memory_modify` 修正
- **发现关联**时：用 `memory_link` 连接
- **定期衰减**：对长时间不访问的记忆执行 `apply_forgetting`

## 节点命名规范

| 规则 | 示例 | 反例 |
|------|------|------|
| 使用名词或名词短语 | `JWT令牌验证` | `如何验证JWT` |
| 不超过15个字 | `任务状态机` | `任务从创建到完成的状态流转逻辑` |
| 避免与已有节点重名 | 先 `recall` 确认不存在再写 | 直接写入 |
| 层级体现在树结构中，不要体现在名称中 | `状态机`（挂在`任务管理`下） | `任务管理-状态机` |

## tags 规范

- 用逗号分隔，每个 tag 2-4 个字
- 包含：功能关键词、技术名词、文件名缩写
- 示例：`tags="认证,JWT,中间件,auth.py"`
- tags 是召回的重要依据，宁多勿少

## content 规范

- 第一句话概括"这是什么"
- 后续写关键细节：函数名、文件路径、参数、返回值、约束条件
- 长度控制在 50-300 字，不要贴整段代码
- 如果内容过长，拆成多个子节点

好的写法：
```
用户认证中间件。位于 app/middleware/auth.py。从请求头提取 Bearer token，
用 jose.jwt.decode 验证签名，注入 request.state.user。未认证时返回 401。
白名单路径（/docs, /health）跳过验证。
```

差的写法：
```
这个文件处理认证相关的事情。
```

## 召回技巧

1. **用多个关键词召回**：`recall(query="JWT 认证 中间件")` 比 `recall(query="认证")` 更精确
2. **换角度再搜**：第一次搜不到时，换同义词或上位概念再搜
3. **先粗后细**：先 `recall` 找到相关节点名，再 `recall_detail` 看详情
4. **用 `browse_tree` 定位**：不确定信息在哪时，先浏览树结构找到目标分支

## 一次完整的工作流示例

用户问："这个项目的数据库迁移怎么做？"

```
1. recall("数据库 迁移 migration")         → 找到相关记忆或发现没有
2. recall("数据库 schema 配置 部署")        → 换关键词补充搜索
3. recall_detail("数据模型")               → 深入查看数据模型子节点
4. [阅读代码找到答案]
5. memory_write(                           → 将新发现写入记忆
     name="数据库迁移",
     content="使用 Alembic 管理迁移。配置在 alembic.ini，迁移脚本在 migrations/versions/。运行: alembic upgrade head",
     parent_name="配置与部署",
     importance=7,
     tags="数据库,迁移,Alembic,alembic.ini"
   )
6. memory_link(                            → 关联到数据模型
     source_name="数据库迁移",
     target_name="数据模型",
     relation="迁移脚本对应模型变更"
   )
7. 回复用户
```
