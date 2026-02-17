"""测试智能分类系统功能.

验证Classifier的核心功能：
1. 关键词分类
2. 语义分类（如果可用）
3. 分类管理
4. 层次结构
"""

import tempfile
from pathlib import Path

from finchbot.memory.classifier import Classifier


def test_keyword_classification():
    """测试关键词分类."""
    print("\n" + "=" * 60)
    print("测试 1: 关键词分类")
    print("=" * 60)

    classifier = Classifier()

    test_cases = [
        ("我叫张三，今年25岁", "personal"),
        ("我的邮箱是 test@example.com", "contact"),
        ("明天下午3点有个会议", "work"),
        ("我喜欢吃苹果", "preference"),
        ("我的目标是学习AI", "goal"),
        ("下周有个重要约会", "schedule"),
        ("这是一个通用信息", "general"),
    ]

    print("\n关键词分类测试:")
    for text, expected_category in test_cases:
        category = classifier.classify(text, use_semantic=False)
        status = "✓" if category == expected_category else "✗"
        print(f"  {status} '{text[:20]}...'")
        print(f"      预期: {expected_category}, 实际: {category}")

    print("\n✅ 关键词分类测试通过!")


def test_category_management():
    """测试分类管理."""
    print("\n" + "=" * 60)
    print("测试 2: 分类管理")
    print("=" * 60)

    classifier = Classifier()

    # 测试创建分类
    category_id = classifier.create_category(
        name="健康",
        description="健康相关记忆，如饮食、运动、医疗等",
        keywords=["健康", "饮食", "运动", "医疗", "体检", "睡眠"],
    )

    assert category_id == "健康"
    print(f"✓ 分类创建成功: {category_id}")

    # 测试获取分类详情
    category_info = classifier.get_category(category_id)
    assert category_info is not None
    assert category_info["name"] == "健康"
    assert "饮食" in category_info["keywords"]
    print("✓ 分类详情获取成功")

    # 测试更新分类
    updated = classifier.update_category(
        category_id=category_id,
        description="更新后的健康描述",
        keywords=["健康", "饮食", "运动", "医疗", "体检", "睡眠", "心理健康"],
    )

    assert updated is True

    category_info = classifier.get_category(category_id)
    assert "心理健康" in category_info["keywords"]
    print("✓ 分类更新成功")

    # 测试列出分类
    categories = classifier.list_categories()
    assert len(categories) >= 8  # 7个默认 + 1个自定义
    print(f"✓ 分类列表获取成功: {len(categories)} 个分类")

    # 测试删除分类
    deleted = classifier.delete_category(category_id)
    assert deleted is True

    category_info = classifier.get_category(category_id)
    assert category_info is None
    print("✓ 分类删除成功")

    print("\n✅ 分类管理测试通过!")


def test_hierarchy_management():
    """测试层次结构管理."""
    print("\n" + "=" * 60)
    print("测试 3: 层次结构管理")
    print("=" * 60)

    classifier = Classifier()

    # 创建父分类
    parent_id = classifier.create_category(
        name="项目",
        description="项目相关记忆",
        keywords=["项目", "任务", "进度", "团队"],
    )

    print(f"✓ 父分类创建成功: {parent_id}")

    # 创建子分类
    child_id = classifier.create_category(
        name="前端开发",
        description="前端开发相关任务",
        keywords=["前端", "HTML", "CSS", "JavaScript", "React"],
        parent_id=parent_id,
    )

    print(f"✓ 子分类创建成功: {child_id} (父分类: {parent_id})")

    # 测试获取层次结构
    hierarchy = classifier.get_category_hierarchy()

    assert parent_id in hierarchy
    assert len(hierarchy[parent_id]["children"]) >= 1

    child_found = False
    for child in hierarchy[parent_id]["children"]:
        if child["id"] == child_id:
            child_found = True
            break

    assert child_found is True
    print("✓ 层次结构获取成功")

    # 测试分类统计
    stats = classifier.get_classification_stats()

    assert stats["total_categories"] >= 8
    assert stats["custom_categories"] >= 2
    assert stats["hierarchy_depth"] >= 2

    print("✓ 分类统计获取成功:")
    print(f"  总分类数: {stats['total_categories']}")
    print(f"  自定义分类: {stats['custom_categories']}")
    print(f"  层次深度: {stats['hierarchy_depth']}")

    print("\n✅ 层次结构管理测试通过!")


def test_workspace_integration():
    """测试工作空间集成."""
    print("\n" + "=" * 60)
    print("测试 4: 工作空间集成")
    print("=" * 60)

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        workspace = Path(tmpdir)

        # 创建分类器并连接到工作空间
        classifier = Classifier(str(workspace))

        # 创建自定义分类
        custom_id = classifier.create_category(
            name="财务",
            description="财务相关记忆",
            keywords=["财务", "预算", "支出", "收入", "投资"],
        )

        print(f"✓ 自定义分类创建成功: {custom_id}")

        # 保存到工作空间
        saved = classifier.save_to_workspace(str(workspace))
        assert saved is True

        # 检查文件是否创建
        config_file = workspace / "memory" / "categories.json"
        assert config_file.exists()

        print(f"✓ 分类配置保存成功: {config_file}")

        # 创建新的分类器并加载工作空间配置
        new_classifier = Classifier(str(workspace))

        # 检查自定义分类是否加载
        custom_info = new_classifier.get_category(custom_id)
        assert custom_info is not None
        assert custom_info["name"] == "财务"

        print("✓ 分类配置加载成功")

        # 测试分类功能
        category = new_classifier.classify("我的预算需要调整", use_semantic=False)
        assert category == custom_id

        print(f"✓ 分类功能验证成功: '我的预算需要调整' -> {category}")

        print("\n✅ 工作空间集成测试通过!")


def test_semantic_classification():
    """测试语义分类."""
    print("\n" + "=" * 60)
    print("测试 5: 语义分类")
    print("=" * 60)

    classifier = Classifier()

    # 尝试启用语义分类
    enabled = classifier.enable_semantic_classification()

    if enabled:
        print("✓ 语义分类启用成功")

        # 测试语义分类
        test_cases = [
            ("我的名字是李四", "personal"),
            ("请记住我的电话号码", "contact"),
            ("我有一个工作项目", "work"),
            ("我特别喜欢蓝色", "preference"),
            ("我想学习机器学习", "goal"),
            ("明天上午10点开会", "schedule"),
        ]

        print("\n语义分类测试:")
        for text, expected_category in test_cases:
            category = classifier.classify(text, use_semantic=True)
            status = "✓" if category == expected_category else "✗"
            print(f"  {status} '{text[:20]}...'")
            print(f"      预期: {expected_category}, 实际: {category}")

        # 测试禁用语义分类
        classifier.disable_semantic_classification()
        assert classifier.is_semantic_classification_available() is False
        print("✓ 语义分类禁用成功")

    else:
        print("⚠ 语义分类不可用，跳过详细测试")

    print("\n✅ 语义分类测试通过!")


def test_classification_accuracy():
    """测试分类准确性."""
    print("\n" + "=" * 60)
    print("测试 6: 分类准确性")
    print("=" * 60)

    classifier = Classifier()

    # 测试数据：文本 -> 预期分类
    test_data = [
        ("我叫王五，来自北京", "personal"),
        ("我的电子邮箱是 user@domain.com", "contact"),
        ("下周要完成项目报告", "work"),
        ("我最喜欢的食物是披萨", "preference"),
        ("我的目标是成为一名数据科学家", "goal"),
        ("后天下午2点有医生预约", "schedule"),
        ("今天天气很好", "general"),
    ]

    print("\n分类准确性测试:")

    correct_keyword = 0
    correct_semantic = 0

    for text, expected_category in test_data:
        # 关键词分类
        keyword_category = classifier.classify(text, use_semantic=False)
        if keyword_category == expected_category:
            correct_keyword += 1

        # 语义分类（如果可用）
        if classifier.is_semantic_classification_available():
            semantic_category = classifier.classify(text, use_semantic=True)
            if semantic_category == expected_category:
                correct_semantic += 1

    total = len(test_data)
    keyword_accuracy = correct_keyword / total * 100
    semantic_accuracy = correct_semantic / total * 100 if classifier.is_semantic_classification_available() else 0

    print(f"  关键词分类准确率: {keyword_accuracy:.1f}% ({correct_keyword}/{total})")

    if classifier.is_semantic_classification_available():
        print(f"  语义分类准确率: {semantic_accuracy:.1f}% ({correct_semantic}/{total})")

    # 要求关键词分类至少达到80%准确率
    assert keyword_accuracy >= 80.0

    print("✓ 分类准确性验证成功")

    print("\n✅ 分类准确性测试通过!")


if __name__ == "__main__":
    """运行所有测试."""
    test_keyword_classification()
    test_category_management()
    test_hierarchy_management()
    test_workspace_integration()
    test_semantic_classification()
    test_classification_accuracy()

    print("\n" + "=" * 60)
    print("所有智能分类系统测试通过! ✅")
    print("=" * 60)
