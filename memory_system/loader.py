"""
记忆加载器

提供两种初始化方式：
1. 演示/测试用的固定概念树。
2. MCP 服务用的工作区文档初始化。
"""

import os

from .memory_store import MemoryStore


WORKSPACE_DOC_EXTENSIONS = {".md", ".txt", ".rst"}
WORKSPACE_DOC_KEYWORDS = ("概念", "方案", "设计", "架构", "readme")
WORKSPACE_DOC_PRIORITY = {
    "readme.md": 100,
    "readme.txt": 95,
    "项目概念.txt": 90,
    "项目概念.md": 90,
    "概念文档.txt": 90,
    "概念文档.md": 90,
}
MAX_BOOTSTRAP_FILES = 8
MAX_BOOTSTRAP_CHARS = 4000


def _score_workspace_doc(filename: str) -> int:
    lower_name = filename.lower()
    extension = os.path.splitext(lower_name)[1]
    if extension not in WORKSPACE_DOC_EXTENSIONS:
        return 0

    if lower_name in WORKSPACE_DOC_PRIORITY:
        return WORKSPACE_DOC_PRIORITY[lower_name]

    score = 0
    if lower_name.startswith("readme"):
        score += 80
    if any(keyword in lower_name for keyword in WORKSPACE_DOC_KEYWORDS):
        score += 60
    return score


def _read_workspace_doc(file_path: str, max_chars: int = MAX_BOOTSTRAP_CHARS) -> str:
    for encoding in ("utf-8", "utf-8-sig", "gbk"):
        try:
            with open(file_path, "r", encoding=encoding) as f:
                text = f.read().strip()
            break
        except UnicodeDecodeError:
            text = ""
    else:
        text = ""

    if len(text) > max_chars:
        return text[:max_chars].rstrip() + "\n\n[内容已截断]"
    return text


def _unique_node_name(name: str, existing_names: set[str]) -> str:
    if name not in existing_names:
        return name

    index = 2
    while f"{name} {index}" in existing_names:
        index += 1
    return f"{name} {index}"


def discover_workspace_documents(workspace_root: str) -> list[str]:
    """收集适合作为工作区初始化种子的文档。"""
    workspace_root = os.path.abspath(workspace_root)
    if not os.path.isdir(workspace_root):
        return []

    candidates = []
    for entry in os.scandir(workspace_root):
        if not entry.is_file():
            continue

        score = _score_workspace_doc(entry.name)
        if score <= 0:
            continue

        candidates.append((score, entry.name.lower(), entry.path))

    candidates.sort(key=lambda item: (-item[0], item[1]))
    return [path for _, _, path in candidates[:MAX_BOOTSTRAP_FILES]]


def load_workspace_concept(store: MemoryStore, workspace_root: str) -> dict[str, str]:
    """
    从当前工作区的项目文档初始化记忆树。

    优先读取工作区根目录下的 README/概念/方案类文档。
    找不到文档时返回空映射，让 MCP 以空库启动。
    """
    workspace_root = os.path.abspath(workspace_root)
    workspace_name = os.path.basename(workspace_root.rstrip(os.sep)) or workspace_root
    document_paths = discover_workspace_documents(workspace_root)
    name_to_id = {}

    if not document_paths:
        return name_to_id

    overview = store.add_node(
        name="工作区概览",
        content=(
            f"工作区 {workspace_name} 的初始化记忆。"
            f"已从 {len(document_paths)} 份项目文档导入基础信息。"
        ),
        parent_id=store.root.node_id,
        importance=8.0,
        precision="low",
        tags=["工作区", "初始化", workspace_name],
    )
    name_to_id[overview.name] = overview.node_id

    existing_names = {overview.name}
    for file_path in document_paths:
        content = _read_workspace_doc(file_path)
        if not content:
            continue

        rel_path = os.path.relpath(file_path, workspace_root).replace("\\", "/")
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        node_name = _unique_node_name(base_name, existing_names)
        existing_names.add(node_name)

        node = store.add_node(
            name=node_name,
            content=f"来源: {rel_path}\n\n{content}",
            parent_id=overview.node_id,
            importance=7.0,
            precision="low" if len(content) > 1200 else "high",
            tags=["文档", "初始化", rel_path],
        )
        name_to_id[node.name] = node.node_id

    return name_to_id


def load_project_concept(store: MemoryStore) -> dict[str, str]:
    """
    将项目概念.txt的内容手动构建为记忆树，并返回 name->node_id 映射。
    这等价于AI第一次阅读文档后进行的"主动记忆写入"。
    """
    name_to_id = {}

    def add(name, content, parent_name=None, importance=5.0, precision="high", tags=None):
        parent_id = name_to_id.get(parent_name) if parent_name else store.root.node_id
        if parent_id is None:
            parent_id = store.root.node_id
        node = store.add_node(
            name=name, content=content, parent_id=parent_id,
            importance=importance, precision=precision, tags=tags or []
        )
        name_to_id[name] = node.node_id
        return node

    # ===== 第一层：根的直接子节点 =====
    add("记忆解决方案", "这是一个基于分层记忆的主动回忆的AI记忆解决方案",
        importance=9.0, precision="low", tags=["方案", "总览", "AI记忆"])

    # ===== 第二层 =====
    add("特性", "项目核心，本方案有5个重要特性：主动读写，多线程，软遗忘，记忆分层，记忆关联",
        parent_name="记忆解决方案", importance=8.0, precision="low",
        tags=["特性", "核心", "主动", "多线程", "遗忘", "分层", "关联"])

    add("实例搭建与外围特性",
        "外围特性是为了更好的实现而进行的附加优化，主要属于提示词工程范畴。本项目分为模型层，实现层，用户层",
        parent_name="记忆解决方案", importance=6.0, precision="low",
        tags=["搭建", "外围", "模型层", "实现层", "用户层"])

    # ===== 第三层：特性的子节点 =====
    add("主动读写", "本方案允许AI主动读写记忆",
        parent_name="特性", importance=8.0, tags=["主动", "读写", "回忆", "写入", "修改"])

    add("多线程", "允许多个AI同时更新/读取一个记忆库，实现多线程项目加速，比如多线程搜索，多线程研究，多线程生成。",
        parent_name="特性", importance=7.0, tags=["多线程", "并发", "加速", "多AI"])

    add("软遗忘", "根据内容重要程度，回忆频率，创建时间，调整记忆被读取的概率",
        parent_name="特性", importance=7.0, tags=["遗忘", "权重", "概率", "衰减"])

    add("记忆分层", "高精度记忆与低精度记忆分层，适配不同回忆精度需要。在同一层级记忆点过多时，聚类为低精度记忆",
        parent_name="特性", importance=8.0, tags=["分层", "精度", "聚类", "高精度", "低精度"])

    add("记忆关联", "关联相关记忆，加强联想能力",
        parent_name="特性", importance=7.0, tags=["关联", "联想", "图", "边"])

    add("其他机制", "允许AI主动整理任务，创建子任务，防止单次任务过长导致上下文爆炸",
        parent_name="特性", importance=6.0, tags=["机制", "任务", "回调", "自动"])

    # ===== 第四层：主动读写的子节点 =====
    add("主动回忆", "每次发送消息只发送当前用户发送的内容，由LLM读取相关内容",
        parent_name="主动读写", importance=9.0,
        tags=["主动回忆", "LLM", "检索", "消息"])

    add("主动写入", "AI可以主动写入记忆，如果这个内容特别重要，应该进行写入",
        parent_name="主动读写", importance=8.0,
        tags=["写入", "创建", "叶子", "父亲"])

    add("主动修改", "AI可以根据最新状态，修改记忆，或根据重要性，修改记忆权重",
        parent_name="主动读写", importance=7.0,
        tags=["修改", "权重", "状态"])

    # ===== 第四层：软遗忘的子节点 =====
    add("记忆权重", "不同记忆条应该可以标记不同权重，可以根据top p回忆",
        parent_name="软遗忘", importance=7.0,
        tags=["权重", "top p", "top k", "概率"])

    add("记忆压缩", "对于不重要的记忆，实现分级存储",
        parent_name="软遗忘", importance=6.0,
        tags=["压缩", "存储", "分级", "归档"])

    # ===== 第四层：其他机制的子节点 =====
    add("回调机制", "如果AI发现任务过长，或用户输入过长，可以进行一次存档，然后重新继续任务",
        parent_name="其他机制", importance=6.0,
        tags=["回调", "存档", "长任务"])

    add("自动进行任务", "AI可以创建子任务AI，加快整个任务进程",
        parent_name="其他机制", importance=6.0,
        tags=["自动", "子任务", "拆分"])

    add("多模态", "这个项目应该原生支持多模态",
        parent_name="其他机制", importance=5.0,
        tags=["多模态", "图片", "音频"])

    # ===== 第三层：实例搭建的子节点 =====
    add("模型层", "这层管理模型调用，并分析模型的能力，将需求按需发送至机器",
        parent_name="实例搭建与外围特性", importance=7.0, precision="low",
        tags=["模型", "调用", "能力", "路由"])

    add("实现层", "待补充",
        parent_name="实例搭建与外围特性", importance=6.0, precision="low",
        tags=["实现", "存储", "服务器"])

    add("用户层", "待补充",
        parent_name="实例搭建与外围特性", importance=5.0, precision="low",
        tags=["用户", "API", "界面"])

    add("外围特性", "关联聚类器，联想树，能力树，模型能力测评器",
        parent_name="实例搭建与外围特性", importance=6.0, precision="low",
        tags=["外围", "聚类", "联想", "能力树"])

    # ===== 第四层：模型层的子节点 =====
    add("模型能力分析", "通过调用结果，用大数据进行分析，分析不同模型的能力特征",
        parent_name="模型层", importance=6.0,
        tags=["能力", "分析", "大数据", "适配"])

    add("模型管理", "管理API，GPU等资源。如果必须将多模态内容发往不支持的模型，进行一次转译",
        parent_name="模型层", importance=6.0,
        tags=["API", "GPU", "资源", "管理"])

    # ===== 第四层：实现层的子节点 =====
    add("存储层", "根据不同存储需求，将数据分级存储。编码为level1-n，方便快速适配",
        parent_name="实现层", importance=6.0,
        tags=["存储", "分级", "内存", "SSD", "HDD"])

    add("软件服务器", "服务器部署相关知识",
        parent_name="实现层", importance=4.0,
        tags=["服务器", "部署"])

    add("日志层", "记录模型的运行过程，用于分析能力瓶颈，数据/细节丢失情况",
        parent_name="实现层", importance=5.0,
        tags=["日志", "debug", "分析", "瓶颈"])

    add("训练数据准备器", "通过复杂化任务执行和实际项目训练，生成模型训练数据",
        parent_name="实现层", importance=6.0,
        tags=["训练", "数据", "微调"])

    # ===== 第四层：外围特性的子节点 =====
    add("关联聚类器", "允许不同深度的节点产生关联，研究如何连接到最合适的节点",
        parent_name="外围特性", importance=5.0,
        tags=["聚类", "关联", "连接"])

    add("联想树", "AI根据已有知识的共性、特性，总结各领域的关联方法，加强记忆联系写入能力",
        parent_name="外围特性", importance=6.0,
        tags=["联想", "共性", "关联方法"])

    add("能力树", "AI通过超长上文学习，形成能力经验。让AI的各式各样固定下来，只需调用记忆",
        parent_name="外围特性", importance=6.0,
        tags=["能力", "经验", "专业性"])

    add("模型能力测评器", "待补充",
        parent_name="外围特性", importance=4.0,
        tags=["测评", "评估"])

    # ==================== 创建关联边（图结构） ====================

    def link(source_name, target_name, relation, weight=1.0):
        src_id = name_to_id.get(source_name)
        tgt_id = name_to_id.get(target_name)
        if src_id and tgt_id:
            store.add_edge(src_id, tgt_id, relation, weight)

    # 方案中明确标注的关联
    link("主动读写", "软遗忘", "主动遗忘→软遗忘")
    link("主动回忆", "回调机制", "输入过长时先记忆再回调")
    link("主动写入", "记忆分层", "可主动创建叶子或父亲")
    link("主动写入", "记忆关联", "发现相关记忆时应主动写入关联")
    link("主动修改", "记忆权重", "修改记忆权重")
    link("多线程", "自动进行任务", "由AI创建子进程自动加速")
    link("记忆压缩", "存储层", "根据需要设置存储等级")
    link("记忆分层", "主动写入", "AI可主动创建父层或叶子")
    link("记忆关联", "联想树", "增强联想创建能力")
    link("记忆关联", "关联聚类器", "聚类时对关联聚类")
    link("回调机制", "主动回忆", "回调时应先主动回忆内容")
    link("自动进行任务", "多线程", "多线程加速")
    link("模型能力分析", "模型能力测评器", "如何分析模型能力")

    return name_to_id
