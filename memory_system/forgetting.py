"""
软遗忘机制 - Soft Forgetting

核心思路：
- 不物理删除记忆，而是通过降低权重使其"沉入水面下"
- 权重受以下因素影响：
  1. 时间衰减（艾宾浩斯遗忘曲线）
  2. 访问频率（越常被回忆的越不易遗忘）
  3. 重要性（重要记忆衰减更慢）
- 支持 Top-K 和 Top-P 查询过滤
"""

import math
import time
from .node import MemoryNode
from .memory_store import MemoryStore


class SoftForgetting:
    """软遗忘管理器"""

    def __init__(self, store: MemoryStore,
                 base_decay_rate: float = 0.0001,
                 importance_shield: float = 0.5,
                 access_boost: float = 0.1,
                 min_weight: float = 0.01):
        """
        Args:
            base_decay_rate: 基础衰减率 (λ)
            importance_shield: 重要性对衰减的屏蔽系数（越高=重要记忆衰减越慢）
            access_boost: 每次访问对权重的提升
            min_weight: 最低权重（不会完全遗忘）
        """
        self.store = store
        self.base_decay_rate = base_decay_rate
        self.importance_shield = importance_shield
        self.access_boost = access_boost
        self.min_weight = min_weight

    def compute_weight(self, node: MemoryNode) -> float:
        """
        计算节点的当前权重

        公式: w = max(min_weight, e^(-λ_eff · Δt) + boost)

        其中:
            λ_eff = base_decay_rate / (1 + importance_shield * importance_norm)
            Δt = 当前时间 - 创建时间
            boost = access_boost * log(1 + access_count)
        """
        now = time.time()
        delta_t = now - node.created_at

        # 重要性屏蔽：越重要，有效衰减率越低
        importance_norm = node.importance / 10.0
        effective_decay = self.base_decay_rate / (1.0 + self.importance_shield * importance_norm)

        # 时间衰减
        time_factor = math.exp(-effective_decay * delta_t)

        # 访问加成：越常被回忆，权重越稳定
        access_factor = self.access_boost * math.log(1.0 + node.access_count)

        weight = time_factor + access_factor
        return max(self.min_weight, min(1.0, weight))

    def apply_decay(self, verbose: bool = False):
        """
        对所有节点应用衰减（"睡眠"阶段的记忆整理）

        这模拟了大脑在睡眠时进行记忆巩固的过程：
        - 重要/高频的记忆被增强
        - 琐碎/少用的记忆被削弱
        """
        if verbose:
            print("\n💤 软遗忘: 开始记忆权重衰减...")

        changes = []
        for node in self.store.nodes.values():
            old_weight = node.weight
            new_weight = self.compute_weight(node)
            node.weight = new_weight

            if verbose and abs(old_weight - new_weight) > 0.01:
                direction = "↓" if new_weight < old_weight else "↑"
                changes.append(f"  {direction} {node.name}: {old_weight:.3f} → {new_weight:.3f}")

        if verbose:
            if changes:
                print(f"  权重变化 ({len(changes)} 个节点):")
                for c in changes[:20]:  # 最多显示20个
                    print(c)
            else:
                print("  无显著变化")
            print("💤 软遗忘完成\n")

    def get_forgotten_nodes(self, threshold: float = 0.1) -> list[MemoryNode]:
        """获取已经"被遗忘"的节点（权重低于阈值）"""
        return [n for n in self.store.nodes.values() if n.weight < threshold]

    def get_vivid_nodes(self, threshold: float = 0.7) -> list[MemoryNode]:
        """获取"鲜明"的记忆（权重高于阈值）"""
        return [n for n in self.store.nodes.values() if n.weight >= threshold]

    def compress_forgotten(self, threshold: float = 0.05, verbose: bool = False):
        """
        记忆压缩：将极低权重的叶子节点合并到父节点的摘要中

        这实现了方案中的"记忆压缩"和"分级存储"概念
        """
        compressed = 0
        for node in list(self.store.nodes.values()):
            if (node.weight < threshold and
                not node.children_ids and  # 只压缩叶子
                node.node_id != self.store.root.node_id):

                parent = self.store.get_parent(node.node_id)
                if parent:
                    # 将内容摘要追加到父节点
                    parent.content += f"\n[已压缩] {node.name}: {node.content[:50]}"
                    # 从父节点移除
                    parent.children_ids.remove(node.node_id)
                    # 从存储移除
                    del self.store.nodes[node.node_id]
                    compressed += 1
                    if verbose:
                        print(f"  🗜️ 压缩: {node.name} → 合并到 {parent.name}")

        if verbose:
            print(f"  总计压缩 {compressed} 个节点")
        return compressed
