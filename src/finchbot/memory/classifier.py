"""智能分类系统.

提供混合分类功能：关键词快速匹配 + 向量语义确认。
支持动态分类创建和管理。
"""

import json
from typing import Any

from loguru import logger


class Classifier:
    """智能分类器.

    提供混合分类功能：
    1. 关键词快速匹配（高效）
    2. 向量语义分类（精确）
    3. 动态分类管理
    """

    def __init__(self, workspace_path: str | None = None) -> None:
        """初始化分类器.

        Args:
            workspace_path: 工作空间路径，用于加载分类配置。
        """
        self.categories = {}
        self.category_keywords = {}
        self.category_descriptions = {}

        self._embeddings = None
        self._category_embeddings = None

        self._load_default_categories()

        if workspace_path:
            self._load_workspace_categories(workspace_path)

        logger.info(f"Classifier initialized with {len(self.categories)} categories")

    def _load_default_categories(self) -> None:
        """加载默认分类."""
        default_categories = {
            "personal": {
                "description": "个人信息，如姓名、年龄、背景等",
                "keywords": ["名字", "年龄", "出生", "家乡", "家庭", "个人", "自己", "我"],
            },
            "preference": {
                "description": "用户偏好，如喜欢的食物、颜色、活动等",
                "keywords": ["喜欢", "偏好", "爱好", "兴趣", "讨厌", "不喜欢", "最爱"],
            },
            "work": {
                "description": "工作相关，如项目、任务、职业等",
                "keywords": ["工作", "项目", "任务", "职业", "公司", "同事", "会议"],
            },
            "contact": {
                "description": "联系方式，如邮箱、电话、地址等",
                "keywords": ["邮箱", "电话", "手机", "地址", "微信", "QQ", "联系"],
            },
            "goal": {
                "description": "目标和计划，如学习目标、职业规划等",
                "keywords": ["目标", "计划", "梦想", "愿望", "规划", "未来"],
            },
            "schedule": {
                "description": "日程安排，如会议、约会、截止日期等",
                "keywords": ["会议", "约会", "截止", "日程", "安排", "时间", "日期"],
            },
            "general": {
                "description": "通用分类，用于未明确分类的内容",
                "keywords": [],
            },
        }

        for cat_id, cat_info in default_categories.items():
            self.categories[cat_id] = cat_info
            self.category_keywords[cat_id] = cat_info.get("keywords", [])
            self.category_descriptions[cat_id] = cat_info.get("description", "")

    def _load_workspace_categories(self, workspace_path: str) -> None:
        """从工作空间加载分类配置.

        Args:
            workspace_path: 工作空间路径。
        """
        try:
            from pathlib import Path

            workspace = Path(workspace_path)
            config_file = workspace / "memory" / "categories.json"

            if config_file.exists():
                with open(config_file, encoding="utf-8") as f:
                    workspace_categories = json.load(f)

                for cat_id, cat_info in workspace_categories.items():
                    if cat_id not in self.categories:
                        self.categories[cat_id] = cat_info
                        self.category_keywords[cat_id] = cat_info.get("keywords", [])
                        self.category_descriptions[cat_id] = cat_info.get("description", "")

                logger.debug(f"Loaded {len(workspace_categories)} categories from workspace")

        except Exception as e:
            logger.warning(f"Failed to load workspace categories: {e}")

    def classify(self, text: str, use_semantic: bool = True) -> str:
        """分类文本.

        Args:
            text: 待分类的文本。
            use_semantic: 是否使用语义分类（如果可用）。

        Returns:
            分类标签。
        """
        # 1. 关键词快速匹配
        text_lower = text.lower()

        for category_id, keywords in self.category_keywords.items():
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    logger.debug(f"Keyword match: '{keyword}' -> {category_id}")
                    return category_id

        # 2. 向量语义分类（如果启用且可用）
        if use_semantic:
            semantic_category = self._classify_by_embedding(text)
            if semantic_category != "general":
                logger.debug(f"Semantic classification: {semantic_category}")
                return semantic_category

        # 3. 默认分类
        return "general"

    def _classify_by_embedding(self, text: str) -> str:
        """通过向量相似度分类.

        Args:
            text: 待分类的文本。

        Returns:
            分类标签。
        """
        if not self._embeddings or not self.category_descriptions:
            return "general"

        try:
            # 懒加载分类描述嵌入
            if self._category_embeddings is None:
                self._cache_category_embeddings()

            if not self._category_embeddings:
                return "general"

            # 计算文本嵌入
            text_embedding = self._embeddings.embed_query(text)

            # 计算与每个分类描述的相似度
            best_category = "general"
            best_similarity = 0.0

            for category_id, category_embedding in self._category_embeddings.items():
                # 计算余弦相似度
                similarity = self._cosine_similarity(text_embedding, category_embedding)

                if similarity > best_similarity and similarity > 0.5:  # 阈值
                    best_similarity = similarity
                    best_category = category_id

            return best_category

        except Exception as e:
            logger.warning(f"Semantic classification failed: {e}")
            return "general"

    def _cache_category_embeddings(self) -> None:
        """缓存分类描述的嵌入向量."""
        try:
            from finchbot.memory.vector import get_embeddings

            if self._embeddings is None:
                self._embeddings = get_embeddings()

            if not self._embeddings:
                return

            self._category_embeddings = {}

            for category_id, description in self.category_descriptions.items():
                if description:
                    embedding = self._embeddings.embed_query(description)
                    self._category_embeddings[category_id] = embedding

            logger.debug(f"Cached embeddings for {len(self._category_embeddings)} categories")

        except Exception as e:
            logger.warning(f"Failed to cache category embeddings: {e}")

    def _cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """计算余弦相似度.

        Args:
            vec1: 向量1。
            vec2: 向量2。

        Returns:
            余弦相似度 (0-1)。
        """
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2, strict=False))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    def create_category(
        self,
        name: str,
        description: str,
        keywords: list[str],
        parent_id: str | None = None,
    ) -> str:
        """创建新分类.

        Args:
            name: 分类名称。
            description: 分类描述。
            keywords: 关键词列表。
            parent_id: 父分类ID。

        Returns:
            分类ID。
        """
        # 生成分类ID（使用名称的小写版本）
        category_id = name.lower().replace(" ", "_")

        # 检查是否已存在
        if category_id in self.categories:
            logger.warning(f"Category '{category_id}' already exists")
            return category_id

        # 创建分类
        category_info = {
            "name": name,
            "description": description,
            "keywords": keywords,
            "parent_id": parent_id,
        }

        self.categories[category_id] = category_info
        self.category_keywords[category_id] = keywords
        self.category_descriptions[category_id] = description

        # 使嵌入缓存失效
        self._category_embeddings = None

        logger.info(f"Category created: {category_id} ({name})")
        return category_id

    def update_category(
        self,
        category_id: str,
        name: str | None = None,
        description: str | None = None,
        keywords: list[str] | None = None,
        parent_id: str | None = None,
    ) -> bool:
        """更新分类.

        Args:
            category_id: 分类ID。
            name: 新的分类名称。
            description: 新的分类描述。
            keywords: 新的关键词列表。
            parent_id: 新的父分类ID。

        Returns:
            是否成功更新。
        """
        if category_id not in self.categories:
            logger.warning(f"Category '{category_id}' not found")
            return False

        # 更新字段
        category_info = self.categories[category_id]

        if name is not None:
            category_info["name"] = name

        if description is not None:
            category_info["description"] = description
            self.category_descriptions[category_id] = description

        if keywords is not None:
            category_info["keywords"] = keywords
            self.category_keywords[category_id] = keywords

        if parent_id is not None:
            category_info["parent_id"] = parent_id

        # 使嵌入缓存失效
        self._category_embeddings = None

        logger.debug(f"Category updated: {category_id}")
        return True

    def delete_category(self, category_id: str) -> bool:
        """删除分类.

        Args:
            category_id: 分类ID。

        Returns:
            是否成功删除。
        """
        if category_id not in self.categories:
            logger.warning(f"Category '{category_id}' not found")
            return False

        # 不能删除默认分类
        default_categories = [
            "personal",
            "preference",
            "work",
            "contact",
            "goal",
            "schedule",
            "general",
        ]
        if category_id in default_categories:
            logger.warning(f"Cannot delete default category: {category_id}")
            return False

        # 删除分类
        del self.categories[category_id]
        del self.category_keywords[category_id]
        del self.category_descriptions[category_id]

        # 使嵌入缓存失效
        self._category_embeddings = None

        logger.info(f"Category deleted: {category_id}")
        return True

    def get_category(self, category_id: str) -> dict[str, Any] | None:
        """获取分类详情.

        Args:
            category_id: 分类ID。

        Returns:
            分类信息字典，如果不存在返回None。
        """
        return self.categories.get(category_id)

    def list_categories(self, include_parents: bool = True) -> list[dict[str, Any]]:
        """列出所有分类.

        Args:
            include_parents: 是否包含父分类信息。

        Returns:
            分类列表。
        """
        categories = []

        for category_id, category_info in self.categories.items():
            category_data = {
                "id": category_id,
                "name": category_info.get("name", category_id),
                "description": category_info.get("description", ""),
                "keyword_count": len(category_info.get("keywords", [])),
            }

            if include_parents and "parent_id" in category_info:
                category_data["parent_id"] = category_info["parent_id"]

            categories.append(category_data)

        return categories

    def get_category_hierarchy(self) -> dict[str, Any]:
        """获取分类层次结构.

        Returns:
            层次结构字典。
        """
        hierarchy = {}

        # 首先找到所有根分类（没有父分类）
        for category_id, category_info in self.categories.items():
            parent_id = category_info.get("parent_id")

            if (not parent_id or parent_id not in self.categories) and category_id not in hierarchy:
                hierarchy[category_id] = {
                    "name": category_info.get("name", category_id),
                    "children": [],
                }

        # 然后添加子分类
        for category_id, category_info in self.categories.items():
            parent_id = category_info.get("parent_id")

            if parent_id and parent_id in hierarchy:
                hierarchy[parent_id]["children"].append(
                    {
                        "id": category_id,
                        "name": category_info.get("name", category_id),
                    }
                )

        return hierarchy

    def save_to_workspace(self, workspace_path: str) -> bool:
        """保存分类配置到工作空间.

        TODO: 未使用 - 仅在测试中被调用，支持分类配置的持久化。保留作为高级功能。

        Args:
            workspace_path: 工作空间路径。

        Returns:
            是否成功保存。
        """
        try:
            from pathlib import Path

            workspace = Path(workspace_path)
            config_file = workspace / "memory" / "categories.json"

            # 确保目录存在
            config_file.parent.mkdir(parents=True, exist_ok=True)

            # 准备保存的数据
            save_data = {}
            for category_id, category_info in self.categories.items():
                # 只保存非默认分类或修改过的默认分类
                if category_id not in [
                    "personal",
                    "preference",
                    "work",
                    "contact",
                    "goal",
                    "schedule",
                    "general",
                ]:
                    save_data[category_id] = category_info

            # 写入文件
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)

            logger.info(f"Categories saved to {config_file}")
            return True

        except Exception as e:
            logger.error(f"Failed to save categories: {e}")
            return False

    def enable_semantic_classification(self) -> bool:
        """启用语义分类.

        TODO: 未使用 - 仅在测试中被调用，动态启用/禁用语义分类功能。保留作为高级功能。

        Returns:
            是否成功启用。
        """
        try:
            from finchbot.memory.vector import get_embeddings

            self._embeddings = get_embeddings()

            if self._embeddings:
                logger.info("Semantic classification enabled")
                return True
            else:
                logger.warning("Semantic classification not available")
                return False

        except Exception as e:
            logger.warning(f"Failed to enable semantic classification: {e}")
            return False

    def disable_semantic_classification(self) -> None:
        """禁用语义分类.

        TODO: 未使用 - 仅在测试中被调用，动态启用/禁用语义分类功能。保留作为高级功能。
        """
        self._embeddings = None
        self._category_embeddings = None
        logger.info("Semantic classification disabled")

    def is_semantic_classification_available(self) -> bool:
        """检查语义分类是否可用.

        Returns:
            是否可用。
        """
        return self._embeddings is not None

    def get_classification_stats(self) -> dict[str, Any]:
        """获取分类统计信息.

        TODO: 未使用 - 仅在测试中被调用，提供分类系统的监控数据。保留用于调试或监控。

        Returns:
            统计字典。
        """
        stats = {
            "total_categories": len(self.categories),
            "default_categories": 7,
            "custom_categories": len(self.categories) - 7,
            "semantic_enabled": self.is_semantic_classification_available(),
            "keywords_total": sum(len(keywords) for keywords in self.category_keywords.values()),
            "hierarchy_depth": self._calculate_hierarchy_depth(),
        }

        return stats

    def _calculate_hierarchy_depth(self) -> int:
        """计算分类层次结构的深度.

        Returns:
            深度。
        """
        max_depth = 0

        for category_id, _category_info in self.categories.items():
            depth = 1
            current_id = category_id

            while "parent_id" in self.categories.get(current_id, {}):
                parent_id = self.categories[current_id]["parent_id"]
                if parent_id in self.categories:
                    depth += 1
                    current_id = parent_id
                else:
                    break

            max_depth = max(max_depth, depth)

        return max_depth
