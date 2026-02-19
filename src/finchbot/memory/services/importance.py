"""重要性评分服务模块.

提供记忆内容的重要性计算功能。
"""

from typing import Optional


class ImportanceScorer:
    """重要性评分器."""

    BASE_IMPORTANCE = 0.5
    MIN_IMPORTANCE = 0.1
    MAX_IMPORTANCE = 1.0
    CONTENT_LENGTH_LONG_THRESHOLD = 100
    CONTENT_LENGTH_SHORT_THRESHOLD = 20
    CONTENT_LENGTH_IMPORTANCE_DELTA = 0.1
    KEYWORD_IMPORTANCE_DELTA = 0.2

    CATEGORY_IMPORTANCE = {
        "personal": 0.8,
        "contact": 0.9,
        "goal": 0.7,
        "work": 0.6,
        "preference": 0.5,
        "schedule": 0.7,
    }

    IMPORTANT_KEYWORDS = ["重要", "关键", "必须", "紧急", "邮箱", "电话", "密码"]

    def calculate_importance(self, content: str, category: str) -> float:
        """计算重要性评分.

        Args:
            content: 记忆内容。
            category: 分类标签。

        Returns:
            重要性评分 (0-1)。
        """
        base_importance = self.BASE_IMPORTANCE

        if category in self.CATEGORY_IMPORTANCE:
            base_importance = self.CATEGORY_IMPORTANCE[category]

        content_length = len(content)
        if content_length > self.CONTENT_LENGTH_LONG_THRESHOLD:
            base_importance = min(
                base_importance + self.CONTENT_LENGTH_IMPORTANCE_DELTA, self.MAX_IMPORTANCE
            )
        elif content_length < self.CONTENT_LENGTH_SHORT_THRESHOLD:
            base_importance = max(
                base_importance - self.CONTENT_LENGTH_IMPORTANCE_DELTA, self.MIN_IMPORTANCE
            )

        for keyword in self.IMPORTANT_KEYWORDS:
            if keyword in content:
                base_importance = min(
                    base_importance + self.KEYWORD_IMPORTANCE_DELTA, self.MAX_IMPORTANCE
                )
                break

        return round(base_importance, 2)
