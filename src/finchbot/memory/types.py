"""记忆模块类型定义.

包含检索策略枚举等共享类型，避免循环导入。
"""

from enum import StrEnum


class RetrievalStrategy(StrEnum):
    """检索策略枚举.

    定义记忆检索的三种策略：
    - SEMANTIC: 仅使用向量语义检索
    - KEYWORD: 仅使用关键词文本匹配
    - HYBRID: 混合检索（向量 + 关键词，结果融合）
    """

    SEMANTIC = "semantic"
    KEYWORD = "keyword"
    HYBRID = "hybrid"
