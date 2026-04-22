"""
记忆存储 - 树图混合记忆管理器

核心职责:
1. 管理所有记忆节点（树结构）
2. 管理所有关联边（图结构）
3. 提供CRUD操作（主动读写）
4. 提供遍历与查询接口
"""

import json
import time
from typing import Optional
from .node import MemoryNode, Edge


class MemoryStore:
    """树图混合记忆存储"""

    def __init__(self, root_name="记忆根节点", root_content="这是记忆系统的根节点"):
        self.nodes: dict[str, MemoryNode] = {}
        self.edges: list[Edge] = []

        # 创建根节点
        self.root = MemoryNode(
            name=root_name,
            content=root_content,
            importance=10.0,
            precision="low",
        )
        self.root.depth = 0
        self.nodes[self.root.node_id] = self.root

    # ==================== 树操作 ====================

    def add_node(self, name: str, content: str, parent_id: Optional[str] = None,
                 importance: float = 5.0, precision: str = "high",
                 tags: list = None) -> MemoryNode:
        """添加记忆节点（主动写入）"""
        if parent_id is None:
            parent_id = self.root.node_id

        parent = self.nodes.get(parent_id)
        if parent is None:
            raise ValueError(f"父节点 {parent_id} 不存在")

        node = MemoryNode(
            name=name,
            content=content,
            parent_id=parent_id,
            importance=importance,
            precision=precision,
            tags=tags or [],
        )
        node.depth = parent.depth + 1

        self.nodes[node.node_id] = node
        parent.children_ids.append(node.node_id)
        return node

    def modify_node(self, node_id: str, content: str = None,
                    importance: float = None, name: str = None):
        """修改记忆节点（主动修改）"""
        node = self.nodes.get(node_id)
        if node is None:
            raise ValueError(f"节点 {node_id} 不存在")
        if content is not None:
            node.content = content
        if importance is not None:
            node.importance = importance
        if name is not None:
            node.name = name

    def get_children(self, node_id: str) -> list[MemoryNode]:
        """获取子节点列表"""
        node = self.nodes.get(node_id)
        if node is None:
            return []
        return [self.nodes[cid] for cid in node.children_ids if cid in self.nodes]

    def get_parent(self, node_id: str) -> Optional[MemoryNode]:
        """获取父节点"""
        node = self.nodes.get(node_id)
        if node is None or node.parent_id is None:
            return None
        return self.nodes.get(node.parent_id)

    def get_path_to_root(self, node_id: str) -> list[MemoryNode]:
        """获取从节点到根的路径"""
        path = []
        current = self.nodes.get(node_id)
        while current is not None:
            path.append(current)
            if current.parent_id is None:
                break
            current = self.nodes.get(current.parent_id)
        return path

    # ==================== 图操作 ====================

    def add_edge(self, source_id: str, target_id: str, relation: str,
                 weight: float = 1.0) -> Edge:
        """添加关联边（记忆关联）"""
        if source_id not in self.nodes or target_id not in self.nodes:
            raise ValueError("源节点或目标节点不存在")
        edge = Edge(source_id=source_id, target_id=target_id,
                    relation=relation, weight=weight)
        self.edges.append(edge)
        return edge

    def get_edges_from(self, node_id: str) -> list[Edge]:
        """获取从某节点出发的所有关联边"""
        return [e for e in self.edges if e.source_id == node_id]

    def get_edges_to(self, node_id: str) -> list[Edge]:
        """获取指向某节点的所有关联边"""
        return [e for e in self.edges if e.target_id == node_id]

    def get_related_nodes(self, node_id: str) -> list[tuple[MemoryNode, Edge]]:
        """获取与某节点关联的所有节点及其边"""
        related = []
        for edge in self.edges:
            if edge.source_id == node_id and edge.target_id in self.nodes:
                related.append((self.nodes[edge.target_id], edge))
            elif edge.target_id == node_id and edge.source_id in self.nodes:
                related.append((self.nodes[edge.source_id], edge))
        return related

    # ==================== 统计与可视化 ====================

    def stats(self) -> dict:
        """记忆库统计"""
        depths = {}
        for node in self.nodes.values():
            d = node.depth
            depths[d] = depths.get(d, 0) + 1

        return {
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "depth_distribution": depths,
            "high_precision": sum(1 for n in self.nodes.values() if n.precision == "high"),
            "low_precision": sum(1 for n in self.nodes.values() if n.precision == "low"),
        }

    def print_tree(self, node_id: str = None, indent: int = 0, max_depth: int = 10):
        """打印记忆树结构"""
        if node_id is None:
            node_id = self.root.node_id
        if indent > max_depth * 2:
            return

        node = self.nodes.get(node_id)
        if node is None:
            return

        prefix = "  " * indent + ("├─ " if indent > 0 else "")
        precision_marker = "📄" if node.precision == "high" else "📁"
        weight_bar = "█" * int(node.weight * 5)
        print(f"{prefix}{precision_marker} {node.name} (w={node.weight:.2f}, imp={node.importance}) [{weight_bar}]")

        # 打印关联边
        edges = self.get_edges_from(node_id)
        for edge in edges:
            target = self.nodes.get(edge.target_id)
            if target:
                edge_prefix = "  " * (indent + 1) + "  ↗ "
                print(f"{edge_prefix}关联→{target.name} ({edge.relation})")

        for child_id in node.children_ids:
            self.print_tree(child_id, indent + 1, max_depth)

    def find_node_by_name(self, name: str) -> Optional[MemoryNode]:
        """按名称查找节点"""
        for node in self.nodes.values():
            if node.name == name:
                return node
        return None

    def to_dict(self) -> dict:
        """序列化为字典"""
        return {
            "nodes": {
                nid: {
                    "name": n.name, "content": n.content, "node_id": n.node_id,
                    "parent_id": n.parent_id, "children_ids": n.children_ids,
                    "importance": n.importance, "weight": n.weight,
                    "precision": n.precision, "created_at": n.created_at,
                    "last_accessed": n.last_accessed, "access_count": n.access_count,
                    "tags": n.tags,
                }
                for nid, n in self.nodes.items()
            },
            "edges": [
                {"source_id": e.source_id, "target_id": e.target_id,
                 "relation": e.relation, "weight": e.weight, "created_at": e.created_at}
                for e in self.edges
            ],
            "root_id": self.root.node_id,
        }

    def save(self, filepath: str):
        """保存记忆库到JSON文件"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, filepath: str) -> 'MemoryStore':
        """从JSON文件加载记忆库"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        store = cls.__new__(cls)
        store.nodes = {}
        store.edges = []

        for nid, ndata in data["nodes"].items():
            node = MemoryNode(
                name=ndata["name"], content=ndata["content"], node_id=ndata["node_id"],
                parent_id=ndata["parent_id"], children_ids=ndata["children_ids"],
                importance=ndata["importance"], weight=ndata["weight"],
                precision=ndata["precision"], tags=ndata.get("tags", []),
            )
            node.created_at = ndata["created_at"]
            node.last_accessed = ndata["last_accessed"]
            node.access_count = ndata["access_count"]
            store.nodes[nid] = node

        for edata in data["edges"]:
            store.edges.append(Edge(
                source_id=edata["source_id"], target_id=edata["target_id"],
                relation=edata["relation"], weight=edata["weight"],
                created_at=edata["created_at"],
            ))

        store.root = store.nodes[data["root_id"]]

        # 重新计算深度
        store._compute_depths()
        return store

    def _compute_depths(self):
        """重新计算所有节点的深度"""
        def _set_depth(node_id, depth):
            node = self.nodes.get(node_id)
            if node:
                node.depth = depth
                for cid in node.children_ids:
                    _set_depth(cid, depth + 1)
        _set_depth(self.root.node_id, 0)
