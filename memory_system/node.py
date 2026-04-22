"""
记忆节点 - 树图混合记忆的基本单元

每个节点是树的一部分（有父子关系），同时通过边参与图结构（跨层级关联）。
支持：权重、精度层级、访问计数、时间衰减等软遗忘所需的全部元数据。
"""

import time
import uuid
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Edge:
    """记忆关联边 - 连接两个记忆节点的显式关系"""
    source_id: str
    target_id: str
    relation: str          # 关系描述，如 "依赖于", "类似于", "触发"
    weight: float = 1.0    # 边的权重/强度
    created_at: float = field(default_factory=time.time)

    def __repr__(self):
        return f"Edge({self.relation}: {self.source_id[:8]}→{self.target_id[:8]}, w={self.weight:.2f})"


@dataclass
class MemoryNode:
    """
    记忆节点 - 树图混合记忆的基本单元

    树结构: parent_id + children_ids 构成层级
    图结构: edges 构成跨层级关联
    软遗忘: weight + access_count + created_at + last_accessed 构成衰减参数
    """
    name: str                                          # 节点名称/标题
    content: str                                       # 节点内容（记忆正文）
    node_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parent_id: Optional[str] = None                    # 父节点ID（根节点为None）
    children_ids: list = field(default_factory=list)   # 子节点ID列表（有序，支持top-k/top-p）
    importance: float = 5.0                            # 重要性 1-10
    weight: float = 1.0                                # 当前权重（受衰减影响）
    precision: str = "high"                            # 精度: "high"=高精度叶子, "low"=低精度摘要
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 0                              # 被回忆次数
    tags: list = field(default_factory=list)            # 关键词标签，辅助检索

    def touch(self):
        """被访问时更新元数据"""
        self.last_accessed = time.time()
        self.access_count += 1

    @property
    def depth(self):
        """节点深度（由外部MemoryStore计算后设置）"""
        return getattr(self, '_depth', 0)

    @depth.setter
    def depth(self, val):
        self._depth = val

    def summary(self, max_len=80):
        """生成节点简短摘要"""
        content_preview = self.content[:max_len] + "..." if len(self.content) > max_len else self.content
        return f"[{self.name}] (w={self.weight:.2f}, imp={self.importance}, p={self.precision}) {content_preview}"

    def __repr__(self):
        return f"MemoryNode('{self.name}', children={len(self.children_ids)}, w={self.weight:.2f})"
