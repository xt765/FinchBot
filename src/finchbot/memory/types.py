"""记忆模块类型定义.

包含检索策略枚举等共享类型，避免循环导入。
"""

from enum import StrEnum


class QueryType(StrEnum):
    """查询类型枚举.

    定义记忆检索的六种查询类型，对应不同的混合检索权重策略：
    - KEYWORD_ONLY: 纯关键词检索
    - SEMANTIC_ONLY: 纯语义检索
    - FACTUAL: 事实型（混合检索，强调用词精确匹配）
    - CONCEPTUAL: 概念型（混合检索，强调语义相关性）
    - COMPLEX: 复杂型（混合检索，均衡权重）
    - AMBIGUOUS: 歧义型（混合检索，偏向语义理解）
    """

    KEYWORD_ONLY = "keyword_only"
    SEMANTIC_ONLY = "semantic_only"
    FACTUAL = "factual"
    CONCEPTUAL = "conceptual"
    COMPLEX = "complex"
    AMBIGUOUS = "ambiguous"
