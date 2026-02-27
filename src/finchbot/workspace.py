"""FinchBot 工作区结构定义.

定义工作区目录结构和初始化逻辑。
支持新的目录架构。
"""

from pathlib import Path

# ========================================
# 目录结构常量
# ========================================

CONFIG_DIR = "config"
BOOTSTRAP_DIR = "bootstrap"
GENERATED_DIR = "generated"
SKILLS_DIR = "skills"
MEMORY_DIR = "memory"
SESSIONS_DIR = "sessions"

# ========================================
# 文件路径常量
# ========================================

MCP_CONFIG_FILE = "mcp.json"
TOOLS_FILE = "TOOLS.md"
CAPABILITIES_FILE = "CAPABILITIES.md"
GITIGNORE_FILE = ".gitignore"

# ========================================
# Bootstrap 文件列表
# ========================================

BOOTSTRAP_FILES = [
    "SYSTEM.md",
    "MEMORY_GUIDE.md",
    "AGENT_CONFIG.md",
    "SOUL.md",
]

# ========================================
# 默认 .gitignore 内容
# ========================================

DEFAULT_GITIGNORE = """# FinchBot 工作区 .gitignore

# 自动生成的文件，不应提交
generated/
sessions/
memory/

# 配置文件，可能包含敏感信息
config/mcp.json

# 用户编辑的文件，应该提交
!bootstrap/
!skills/
"""


def get_mcp_config_path(workspace: Path) -> Path:
    """获取 MCP 配置文件路径.

    Args:
        workspace: 工作区路径.

    Returns:
        MCP 配置文件路径.
    """
    return workspace / CONFIG_DIR / MCP_CONFIG_FILE


def get_bootstrap_path(workspace: Path, filename: str) -> Path:
    """获取 Bootstrap 文件路径.

    Args:
        workspace: 工作区路径.
        filename: Bootstrap 文件名.

    Returns:
        Bootstrap 文件路径.
    """
    return workspace / BOOTSTRAP_DIR / filename


def get_generated_path(workspace: Path, filename: str) -> Path:
    """获取自动生成文件路径.

    Args:
        workspace: 工作区路径.
        filename: 文件名.

    Returns:
        生成文件路径.
    """
    return workspace / GENERATED_DIR / filename


def get_tools_path(workspace: Path) -> Path:
    """获取 TOOLS.md 文件路径.

    Args:
        workspace: 工作区路径.

    Returns:
        TOOLS.md 文件路径.
    """
    return get_generated_path(workspace, TOOLS_FILE)


def get_capabilities_path(workspace: Path) -> Path:
    """获取 CAPABILITIES.md 文件路径.

    Args:
        workspace: 工作区路径.

    Returns:
        CAPABILITIES.md 文件路径.
    """
    return get_generated_path(workspace, CAPABILITIES_FILE)


def init_workspace(workspace: Path, create_gitignore: bool = True) -> None:
    """初始化工作区目录结构.

    创建必要的目录结构，并生成默认文件。

    Args:
        workspace: 工作区路径.
        create_gitignore: 是否创建 .gitignore 文件.
    """
    workspace = Path(workspace).expanduser().resolve()
    
    # 创建目录结构
    (workspace / CONFIG_DIR).mkdir(parents=True, exist_ok=True)
    (workspace / BOOTSTRAP_DIR).mkdir(parents=True, exist_ok=True)
    (workspace / GENERATED_DIR).mkdir(parents=True, exist_ok=True)
    (workspace / SKILLS_DIR).mkdir(parents=True, exist_ok=True)
    (workspace / MEMORY_DIR).mkdir(parents=True, exist_ok=True)
    (workspace / SESSIONS_DIR).mkdir(parents=True, exist_ok=True)
    
    # 创建默认 MCP 配置
    mcp_path = get_mcp_config_path(workspace)
    if not mcp_path.exists():
        mcp_path.write_text('{"servers": {}}', encoding="utf-8")
    
    # 创建 .gitignore
    if create_gitignore:
        gitignore_path = workspace / GITIGNORE_FILE
        if not gitignore_path.exists():
            gitignore_path.write_text(DEFAULT_GITIGNORE, encoding="utf-8")


def is_workspace_initialized(workspace: Path) -> bool:
    """检查工作区是否已初始化.

    Args:
        workspace: 工作区路径.

    Returns:
        是否已初始化。
    """
    workspace = Path(workspace).expanduser().resolve()
    
    # 检查必要的目录是否存在
    required_dirs = [CONFIG_DIR, BOOTSTRAP_DIR, GENERATED_DIR, SKILLS_DIR]
    for dir_name in required_dirs:
        if not (workspace / dir_name).is_dir():
            return False
    
    # 检查 MCP 配置文件是否存在
    if not get_mcp_config_path(workspace).exists():
        return False
    
    return True
