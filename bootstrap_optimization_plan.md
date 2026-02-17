# Bootstrap 文件系统优化方案

## 当前问题

Bootstrap 文件的**创建**和**读取**逻辑分散在多处：

```
创建位置：
├── get_default_workspace()          → 调用 _create_workspace_templates()
├── create_finch_agent()             → 调用 _create_workspace_templates() [已修复]
└── (CLI 入口未调用 get_default_workspace)

读取位置：
└── build_system_prompt()            → 通过 ContextBuilder._load_bootstrap_files()
```

## 方案对比

### 方案 A：统一入口（推荐）

**核心思路**：所有地方都调用 `get_default_workspace()` 获取工作区路径

```
修改内容：
1. 修改 CLI 入口：chat_session.py, cli_main.py, sessions.py, selector.py
2. 移除 create_finc_agent() 中的 _create_workspace_templates() 调用
3. 保留 get_default_workspace() 中的创建逻辑

优点：
- 单一职责：get_default_workspace() 负责初始化，create_finch_agent() 负责创建 agent
- 减少重复代码
- 符合"DRY"原则

缺点：
- 需要修改多个 CLI 文件
```

**实现方式**：
```python
# cli_main.py, chat_session.py 等
from finchbot.agent import get_default_workspace

ws_path = get_default_workspace()  # 替换原有的 Path(...) 逻辑
```

---

### 方案 B：保持现状（最小改动）

**核心思路**：不调整架构，只确保现有逻辑正常工作

```
修改内容：
1. 保留 create_finch_agent() 中的 _create_workspace_templates() 调用
2. get_default_workspace() 中的调用保留（但可能不会被 CLI 使用）

优点：
- 最小改动
- 现有代码基本不变

缺点：
- 创建逻辑分散在两处
- get_default_workspace() 可能变成死代码
- 违反"单一职责"原则
```

---

### 方案 C：ContextBuilder 延迟创建

**核心思路**：在 ContextBuilder 读取时按需创建

```
修改内容：
1. 修改 ContextBuilder._load_bootstrap_files()
2. 如果文件不存在，自动创建默认内容
3. 移除其他所有创建逻辑

优点：
- 创建和读取在同一位置
- 真正"按需"创建

缺点：
- ContextBuilder 职责过重（既读取又创建）
- 不符合"创建者不应是读者"原则
- 测试难度增加
```

---

## 推荐：方案 A

理由：
1. **单一职责**：初始化归初始化，agent 创建归 agent 创建
2. **符合 DRY**：避免重复调用 `_create_workspace_templates()`
3. **语义清晰**：`get_default_workspace()` 表达的是"获取默认工作区（并初始化）"
4. **易于维护**：未来修改 Bootstrap 创建逻辑只需改一处

## 执行步骤

1. [ ] 修改 `cli_main.py` - 使用 `get_default_workspace()` 替代直接构造路径
2. [ ] 修改 `chat_session.py` - 同上
3. [ ] 修改 `cli/sessions.py` - 同上
4. [ ] 修改 `sessions/selector.py` - 同上
5. [ ] 移除 `create_finch_agent()` 中的 `_create_workspace_templates()` 调用
6. [ ] 运行测试验证
