# 可用工具

## 文件操作

### read_file

读取指定路径的文本文件内容。仅支持 UTF-8 编码，二进制文件可能显示乱码。

**参数:**

- `file_path` (必填): tools.read_file.param_file_path

---

### write_file

将内容写入文件，自动创建父目录。警告：如果文件已存在，将直接覆盖！

**参数:**

- `file_path` (必填): tools.write_file.param_file_path
- `content` (必填): 要写入的文件内容

---

### edit_file

通过替换文本编辑文件。old_text 必须精确匹配（包括空格和换行）。如果 old_text 出现多次，会返回警告要求提供更多上下文。

**参数:**

- `file_path` (必填): tools.read_file.param_file_path
- `old_str` (必填): The exact string to be replaced.
- `new_str` (必填): The new string to replace with.

---

### list_dir

列出目录内容，按名称字母顺序排序。📁 表示目录，📄 表示文件。

**参数:**

- `dir_path` (必填): tools.list_dir.param_dir_path

---

### exec

执行 shell 命令并返回输出。默认超时 60 秒，输出超过 10000 字符会被截断。包含安全检查，禁止危险命令。 优先使用文件系统工具（read_file/write_file/edit_file）处理文件，仅在需要批量操作、复杂文本处理或系统命令时使用 exec。适用于：批量文件操作、复杂文本处理、系统信息查询、需要管道或重定向的场景。

**参数:**

- `command` (必填): 要执行的 shell 命令
- `working_dir`: 可选的工作目录

---

## 网络工具

### web_extract

从网页 URL 提取内容。支持批量提取（建议一次不超过 5 个 URL）。返回内容超过 5000 字符会被截断。

**参数:**

- `urls` (必填): URLs to extract

---

### web_search

搜索互联网获取最新信息。默认返回 5 条结果，支持 Tavily、Brave Search 和 DuckDuckGo 自动降级。

**参数:**

- `query` (必填): Search query
- `max_results`: Max results

---

## 记忆管理

### remember

保存重要信息到记忆库，以便后续检索。 当用户告诉你重要信息（如名字、偏好、联系方式、日程等）时，必须调用此工具。

**参数:**

- `content` (必填): 要记住的信息内容
- `category`: 分类: personal(个人信息), preference(偏好), work(工作), contact(联系方式), goal(目标), schedule(日程), general(通用)
- `importance`: 重要性评分 (0-1)，越高越重要

---

### recall

从记忆库中搜索和检索信息。支持基于查询类型的混合检索策略（加权 RRF）。 当用户询问关于他自己的信息时，必须先调用此工具检索记忆。根据查询类型选择合适的 query_type：factual 用于事实性查询（如'我的邮箱是多少'），conceptual 用于概念性查询（如'我喜欢的食物'），complex 用于复杂查询，ambiguous 用于歧义查询，keyword_only 用于特定ID或名称查询，semantic_only 用于语义探索。

**参数:**

- `query` (必填): 搜索查询内容
- `category`: 按分类过滤（可选）
- `top_k`: 最大返回数量
- `query_type`: 查询类型: keyword_only (1.0/0.0), semantic_only (0.0/1.0), factual (0.8/0.2), conceptual (0.2/0.8), complex (0.5/0.5), ambiguous (0.3/0.7)
- `similarity_threshold`: 相似度阈值 (0.0-1.0)，用于过滤语义不相关的结果，默认 0.5。当返回不相关结果时可提高阈值（如 0.7），当返回结果过少时可降低阈值（如 0.3）

---

### forget

从记忆库中删除指定的信息。删除是永久性的，无法恢复。支持部分匹配，例如输入'邮箱'会删除所有包含'邮箱'的记忆。 当用户明确要求忘记、删除或清除某些信息时调用此工具。删除后无法恢复，请谨慎使用。

**参数:**

- `pattern` (必填): 要删除的内容匹配模式

---

## 会话管理

### session_title

获取或设置当前会话的标题。 当对话进行 2-3 轮后，如果标题为空或需要修改时使用。

**参数:**

- `action` (必填): 操作类型: get(获取标题) 或 set(设置标题)
- `title`: 新标题（仅 set 时需要），5-15 个字符，无标点

---
