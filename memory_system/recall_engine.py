"""
主动回忆引擎 - Active Recall Engine

核心逻辑:
1. 从根节点开始遍历记忆树
2. 在每一层根据查询相关性 × 节点权重 进行评分
3. Top-P / Top-K 截断选择进入下一层的节点
4. 同时沿图的关联边"联想"相关记忆
5. 返回最终召回的记忆集合，按综合评分排序
"""

import math
import re
import time
from typing import Optional
from .node import MemoryNode
from .memory_store import MemoryStore


def _tokenize(text: str) -> set[str]:
    """简单分词：按空格和标点分割，支持中文逐字"""
    # 英文按词，中文按字+词
    words = set()
    # 提取英文单词
    for w in re.findall(r'[a-zA-Z]+', text.lower()):
        words.add(w)
    # 提取中文字符（逐字 + 连续中文作为词组）
    chinese_chars = re.findall(r'[\u4e00-\u9fff]', text)
    words.update(chinese_chars)
    # 连续中文2-4字组合
    chinese_runs = re.findall(r'[\u4e00-\u9fff]{2,}', text)
    for run in chinese_runs:
        words.add(run)
        for i in range(len(run)):
            for j in range(i + 2, min(i + 5, len(run) + 1)):
                words.add(run[i:j])
    return words


def keyword_relevance(query: str, node: MemoryNode) -> float:
    """基于关键词重叠计算查询与节点的相关性 (0-1)"""
    query_tokens = _tokenize(query)
    node_tokens = _tokenize(node.name + " " + node.content + " " + " ".join(node.tags))

    if not query_tokens or not node_tokens:
        return 0.0

    overlap = query_tokens & node_tokens
    # Jaccard相似度的变体：以查询词为基准
    relevance = len(overlap) / len(query_tokens) if query_tokens else 0.0
    return min(relevance, 1.0)


def compute_recall_score(query: str, node: MemoryNode,
                         alpha: float = 1.0, beta: float = 1.0,
                         gamma: float = 0.5, decay_rate: float = 0.001) -> float:
    """
    综合回忆评分 = alpha * Relevance + beta * Importance_norm + gamma * Recency

    参考 Generative Agents 的评分公式:
    Score = α·Relevance + β·Importance + γ·Recency

    Recency 使用指数衰减: e^(-λ·Δt)
    """
    # 相关性
    relevance = keyword_relevance(query, node)

    # 重要性（归一化到0-1）
    importance_norm = node.importance / 10.0

    # 新近度（指数衰减）
    time_delta = time.time() - node.last_accessed
    recency = math.exp(-decay_rate * time_delta)

    # 权重调节
    weight_factor = node.weight

    score = (alpha * relevance + beta * importance_norm + gamma * recency) * weight_factor
    return score


class RecallEngine:
    """
    主动回忆引擎

    模拟人类回忆过程：
    1. 接收到查询（等价于"刺激"）
    2. 从根节点开始，逐层评估哪些记忆被"激活"
    3. 沿着被激活的路径继续深入（高精度回忆）
    4. 同时沿关联边"联想"到相关记忆
    5. 所有被激活的记忆按评分排序返回
    """

    def __init__(self, store: MemoryStore):
        self.store = store

    def recall(self, query: str, top_k: int = 10, top_p: float = 0.8,
               max_depth: int = 20, use_associations: bool = True,
               verbose: bool = False) -> list[tuple[MemoryNode, float]]:
        """
        主动回忆：给定查询，返回最相关的记忆节点列表

        Args:
            query: 用户查询/当前消息
            top_k: 每层最多激活的节点数
            top_p: 累积概率截断（在每层中，按评分排序，取累积占比达到top_p的节点）
            max_depth: 最大搜索深度
            use_associations: 是否沿关联边联想
            verbose: 是否打印回忆过程

        Returns:
            [(MemoryNode, score), ...] 按评分降序排列
        """
        recalled = {}  # node_id -> (node, score)
        visited = set()
        frontier = [self.store.root.node_id]

        if verbose:
            print(f"\n🧠 主动回忆开始 | 查询: \"{query}\"")
            print("=" * 60)

        depth = 0
        while frontier and depth < max_depth:
            if verbose:
                print(f"\n  📍 深度 {depth} | 待探索节点: {len(frontier)}")

            # 对当前层所有节点评分
            scored = []
            for nid in frontier:
                if nid in visited:
                    continue
                visited.add(nid)
                node = self.store.nodes.get(nid)
                if node is None:
                    continue

                score = compute_recall_score(query, node)
                scored.append((node, score))
                node.touch()  # 更新访问时间

            if not scored:
                break

            # 按评分排序
            scored.sort(key=lambda x: x[1], reverse=True)

            # Top-P截断
            activated = self._top_p_filter(scored, top_p, top_k)

            if verbose:
                for node, score in activated:
                    marker = "✅" if score > 0.3 else "⬜"
                    print(f"    {marker} {node.name}: score={score:.3f} "
                          f"(w={node.weight:.2f}, imp={node.importance})")

            # 记录被激活的节点
            for node, score in activated:
                if node.node_id not in recalled or recalled[node.node_id][1] < score:
                    recalled[node.node_id] = (node, score)

            # 下一层：被激活节点的子节点 + 关联节点
            next_frontier = []
            for node, score in activated:
                # 子节点（沿树下钻）
                next_frontier.extend(node.children_ids)

                # 关联节点（沿图联想）
                if use_associations:
                    related = self.store.get_related_nodes(node.node_id)
                    for related_node, edge in related:
                        if related_node.node_id not in visited:
                            next_frontier.append(related_node.node_id)
                            if verbose:
                                print(f"    ↗ 联想: {node.name} --({edge.relation})--> {related_node.name}")

            frontier = list(set(next_frontier))
            depth += 1

        # 按评分排序返回
        results = sorted(recalled.values(), key=lambda x: x[1], reverse=True)[:top_k]

        if verbose:
            print(f"\n{'='*60}")
            print(f"🧠 回忆完成 | 召回 {len(results)} 条记忆")
            for i, (node, score) in enumerate(results):
                print(f"  {i+1}. [{score:.3f}] {node.name}: {node.content[:60]}...")

        return results

    def _top_p_filter(self, scored: list[tuple[MemoryNode, float]],
                      top_p: float, top_k: int) -> list[tuple[MemoryNode, float]]:
        """Top-P截断：选择累积评分占比达到top_p的节点子集"""
        if not scored:
            return []

        total_score = sum(s for _, s in scored)
        if total_score == 0:
            return scored[:top_k]

        activated = []
        cumulative = 0.0
        for node, score in scored:
            cumulative += score / total_score
            activated.append((node, score))
            if cumulative >= top_p or len(activated) >= top_k:
                break

        return activated

    def recall_context(self, query: str, **kwargs) -> str:
        """
        回忆并生成上下文字符串（可直接注入LLM提示词）

        这是"主动回忆"的最终输出：一段结构化的记忆上下文。
        """
        results = self.recall(query, **kwargs)

        if not results:
            return "[无相关记忆]"

        lines = ["# 回忆到的相关记忆\n"]
        for i, (node, score) in enumerate(results):
            lines.append(f"## 记忆 {i+1} (相关度: {score:.2f}, 精度: {node.precision})")
            lines.append(f"**{node.name}**")
            lines.append(node.content)

            # 显示路径上下文
            path = self.store.get_path_to_root(node.node_id)
            if len(path) > 1:
                path_names = " → ".join(n.name for n in reversed(path))
                lines.append(f"_路径: {path_names}_")

            # 显示关联
            related = self.store.get_related_nodes(node.node_id)
            if related:
                assoc_strs = [f"{rn.name}({e.relation})" for rn, e in related]
                lines.append(f"_关联: {', '.join(assoc_strs)}_")

            lines.append("")

        return "\n".join(lines)
