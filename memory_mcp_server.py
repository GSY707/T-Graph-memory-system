"""
记忆系统 MCP 服务器

将树图混合记忆系统暴露为 MCP 工具，供 VS Code Copilot 等客户端调用。
支持：主动回忆、深入查看、浏览树、写入、关联、修改、遗忘衰减、统计。
"""

import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from mcp.server.fastmcp import FastMCP

from memory_system.memory_store import MemoryStore
from memory_system.recall_engine import RecallEngine
from memory_system.forgetting import SoftForgetting
from memory_system.loader import load_workspace_concept

# ==================== 初始化 ====================

WORKSPACE_ROOT = os.path.abspath(os.environ.get("MEMORY_WORKSPACE_ROOT") or os.getcwd())
WORKSPACE_NAME = os.path.basename(WORKSPACE_ROOT.rstrip(os.sep)) or WORKSPACE_ROOT
STATE_DIR = os.path.join(WORKSPACE_ROOT, ".memory-system")
SNAPSHOT_PATH = os.path.join(STATE_DIR, "memory_mcp_snapshot.json")
LEGACY_SNAPSHOT_PATH = os.path.join(SCRIPT_DIR, "memory_mcp_snapshot.json")

mcp = FastMCP("memory-system", log_level="WARNING")

store = MemoryStore(
    root_name=f"{WORKSPACE_NAME} 记忆根节点",
    root_content=f"这是工作区 {WORKSPACE_NAME} 的独立记忆根节点",
)
engine = RecallEngine(store)
forgetter = SoftForgetting(store)


def _should_migrate_legacy_snapshot() -> bool:
    """仅在工具运行于原工作区时，迁移旧版根目录快照。"""
    return (
        os.path.abspath(WORKSPACE_ROOT) == SCRIPT_DIR
        and os.path.exists(LEGACY_SNAPSHOT_PATH)
        and not os.path.exists(SNAPSHOT_PATH)
    )


def _load_snapshot(snapshot_path: str):
    with open(snapshot_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    _restore_from_dict(data)


def _load_or_init():
    """尝试加载当前工作区快照，否则从当前工作区文档初始化。"""
    if os.path.exists(SNAPSHOT_PATH):
        _load_snapshot(SNAPSHOT_PATH)
        return

    if _should_migrate_legacy_snapshot():
        _load_snapshot(LEGACY_SNAPSHOT_PATH)
        _save_snapshot()
        return

    if load_workspace_concept(store, WORKSPACE_ROOT):
        _save_snapshot()


def _save_snapshot():
    """持久化当前记忆状态"""
    data = store.to_dict()
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(SNAPSHOT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _restore_from_dict(data: dict):
    """从序列化数据恢复记忆库"""
    from memory_system.node import MemoryNode, Edge

    store.nodes.clear()
    store.edges.clear()

    for nid, nd in data["nodes"].items():
        node = MemoryNode(
            name=nd["name"],
            content=nd["content"],
            node_id=nd["node_id"],
            parent_id=nd["parent_id"],
            children_ids=nd["children_ids"],
            importance=nd["importance"],
            weight=nd["weight"],
            precision=nd["precision"],
            created_at=nd["created_at"],
            last_accessed=nd["last_accessed"],
            access_count=nd["access_count"],
            tags=nd.get("tags", []),
        )
        store.nodes[nid] = node

    root_id = data.get("root_id")
    if root_id and root_id in store.nodes:
        store.root = store.nodes[root_id]

    # 恢复深度
    def _set_depth(nid, depth):
        if nid in store.nodes:
            store.nodes[nid].depth = depth
            for cid in store.nodes[nid].children_ids:
                _set_depth(cid, depth + 1)

    _set_depth(store.root.node_id, 0)

    for ed in data.get("edges", []):
        edge = Edge(
            source_id=ed["source_id"],
            target_id=ed["target_id"],
            relation=ed["relation"],
            weight=ed.get("weight", 1.0),
            created_at=ed.get("created_at", 0),
        )
        store.edges.append(edge)


# ==================== MCP 工具 ====================

@mcp.tool()
def recall(query: str, top_k: int = 5) -> str:
    """从记忆树中主动回忆与查询相关的记忆。从根节点开始逐层搜索，返回最相关的记忆节点。"""
    results = engine.recall(query, top_k=top_k, verbose=False)
    if not results:
        return "未找到相关记忆。"

    lines = []
    for i, (node, score) in enumerate(results):
        path = store.get_path_to_root(node.node_id)
        path_str = " → ".join(n.name for n in reversed(path))
        lines.append(
            f"{i+1}. [{score:.2f}] **{node.name}** (精度:{node.precision}, 重要性:{node.importance})\n"
            f"   内容: {node.content}\n"
            f"   路径: {path_str}"
        )
        related = store.get_related_nodes(node.node_id)
        if related:
            assocs = [f"{rn.name}({e.relation})" for rn, e in related]
            lines.append(f"   关联: {', '.join(assocs)}")
    return "\n".join(lines)


@mcp.tool()
def recall_detail(node_name: str) -> str:
    """深入查看某个记忆节点的详细信息，包括子节点、父节点路径和关联边。"""
    node = store.find_node_by_name(node_name)
    if not node:
        return f"节点 '{node_name}' 不存在"

    lines = [f"## {node.name}"]
    lines.append(f"内容: {node.content}")
    lines.append(f"精度: {node.precision} | 重要性: {node.importance} | 权重: {node.weight:.2f}")
    lines.append(f"访问次数: {node.access_count}")

    path = store.get_path_to_root(node.node_id)
    lines.append(f"路径: {' → '.join(n.name for n in reversed(path))}")

    children = store.get_children(node.node_id)
    if children:
        lines.append(f"子节点 ({len(children)}):")
        for c in children:
            lines.append(f"  - {c.name}: {c.content[:80]}...")

    related = store.get_related_nodes(node.node_id)
    if related:
        lines.append(f"关联 ({len(related)}):")
        for rn, edge in related:
            lines.append(f"  ↔ {rn.name} ({edge.relation})")

    return "\n".join(lines)


@mcp.tool()
def browse_tree(max_depth: int = 3) -> str:
    """浏览记忆树的结构概览，查看所有节点的层级关系。"""
    import io
    from contextlib import redirect_stdout
    f = io.StringIO()
    with redirect_stdout(f):
        store.print_tree(max_depth=max_depth)
    return f.getvalue()


@mcp.tool()
def memory_write(name: str, content: str, parent_name: str = "", importance: float = 5.0, tags: str = "") -> str:
    """写入一条新记忆。tags 用逗号分隔。parent_name 为空则挂在根节点下。"""
    parent_node = store.find_node_by_name(parent_name) if parent_name else None
    parent_id = parent_node.node_id if parent_node else store.root.node_id
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []

    node = store.add_node(
        name=name,
        content=content,
        parent_id=parent_id,
        importance=importance,
        tags=tag_list,
    )
    _save_snapshot()
    return f"记忆已写入: '{node.name}' (importance={node.importance}, 父节点='{parent_name or '根节点'}')"


@mcp.tool()
def memory_link(source_name: str, target_name: str, relation: str) -> str:
    """在两个记忆节点之间创建关联边。"""
    src = store.find_node_by_name(source_name)
    tgt = store.find_node_by_name(target_name)
    if not src:
        return f"源节点 '{source_name}' 不存在"
    if not tgt:
        return f"目标节点 '{target_name}' 不存在"
    store.add_edge(src.node_id, tgt.node_id, relation)
    _save_snapshot()
    return f"关联已创建: {source_name} --({relation})--> {target_name}"


@mcp.tool()
def memory_modify(name: str, content: str = "", importance: float = -1) -> str:
    """修改一条已有记忆的内容或重要性。importance 传 -1 表示不修改。"""
    node = store.find_node_by_name(name)
    if not node:
        return f"节点 '{name}' 不存在"
    store.modify_node(
        node.node_id,
        content=content if content else None,
        importance=importance if importance >= 0 else None,
    )
    _save_snapshot()
    return f"记忆已修改: '{name}'"


@mcp.tool()
def apply_forgetting() -> str:
    """对所有记忆应用软遗忘衰减（模拟时间流逝的自然遗忘）。"""
    forgetter.apply_decay(verbose=False)
    _save_snapshot()
    forgotten = forgetter.get_forgotten_nodes(threshold=0.1)
    vivid = forgetter.get_vivid_nodes(threshold=0.7)
    return f"软遗忘已应用。鲜明记忆: {len(vivid)} 条, 模糊记忆: {len(forgotten)} 条"


@mcp.tool()
def memory_stats() -> str:
    """查看记忆库统计信息。"""
    s = store.stats()
    lines = [
        f"总节点数: {s['total_nodes']}",
        f"总关联边: {s['total_edges']}",
        f"高精度节点: {s['high_precision']}",
        f"低精度节点: {s['low_precision']}",
        f"层级分布: {json.dumps(s['depth_distribution'], ensure_ascii=False)}",
    ]
    return "\n".join(lines)


# ==================== 启动 ====================

_load_or_init()

if __name__ == "__main__":
    mcp.run()
