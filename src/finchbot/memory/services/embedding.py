"""Embedding 服务模块.

提供向量嵌入模型的加载、网络检查和镜像选择功能。
"""

import os
import socket
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from loguru import logger

if TYPE_CHECKING:
    from langchain_community.embeddings.fastembed import FastEmbedEmbeddings

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
# 模型缓存目录（项目内）
MODEL_CACHE_DIR = PROJECT_ROOT / ".models" / "fastembed"


class EmbeddingService:
    """向量嵌入服务."""

    def __init__(self, cache_dir: Optional[Path] = None, verbose: bool = True):
        self.cache_dir = cache_dir or MODEL_CACHE_DIR
        self.verbose = verbose
        self._embeddings_cache: Optional["FastEmbedEmbeddings"] = None
        self._ensure_cache_dir()

    def _ensure_cache_dir(self) -> None:
        """确保缓存目录存在."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _check_internet_connection(
        self, host: str = "huggingface.co", port: int = 443, timeout: int = 3
    ) -> bool:
        """检查网络连接."""
        try:
            socket.create_connection((host, port), timeout=timeout)
            return True
        except OSError:
            return False

    def _detect_best_mirror(self) -> tuple[str, str]:
        """检测最佳下载镜像."""
        try:
            socket.create_connection(("hf-mirror.com", 443), timeout=2)
            return ("https://hf-mirror.com", "国内镜像")
        except OSError:
            pass

        try:
            socket.create_connection(("huggingface.co", 443), timeout=2)
            return ("https://huggingface.co", "官方源")
        except OSError:
            pass

        return ("https://huggingface.co", "官方源")

    def _check_model_exists(self) -> bool:
        """检查模型文件是否存在."""
        if not self.cache_dir.exists():
            return False
        return any(self.cache_dir.rglob("model_optimized.onnx"))

    def _print_model_status(
        self,
        model_exists: bool,
        has_internet: bool,
        mirror_url: Optional[str] = None,
    ) -> None:
        """打印模型状态提示."""
        from rich.console import Console
        from rich.panel import Panel

        console = Console()

        if model_exists:
            logger.info(f"✓ 嵌入模型已就绪: {self.cache_dir}")
            return

        if has_internet:
            mirror_display = mirror_url or "自动检测"
            console.print(
                Panel(
                    f"[yellow]⚠ 嵌入模型未找到[/yellow]\n\n"
                    f"模型将在首次使用时自动下载:\n"
                    f"• 模型: BAAI/bge-small-zh-v1.5\n"
                    f"• 源: {mirror_display}\n"
                    f"• 大小: 约 50MB\n\n"
                    f"或手动下载: [cyan]finchbot download-models[/cyan]",
                    title="模型状态",
                    border_style="yellow",
                )
            )
        else:
            console.print(
                Panel(
                    "[red]✗ 嵌入模型未找到且无法连接网络[/red]\n\n"
                    "当前处于离线模式，无法下载模型。\n\n"
                    "解决方案:\n"
                    "1. 连接网络后运行: [cyan]finchbot download-models[/cyan]\n"
                    "2. 或从其他机器复制模型到:\n"
                    f"   [dim]{self.cache_dir}[/dim]\n\n"
                    "注意: 离线模式下语义记忆功能将不可用",
                    title="离线模式",
                    border_style="red",
                )
            )

    def get_embeddings(self) -> Optional["FastEmbedEmbeddings"]:
        """获取 FastEmbed 本地模型."""
        if self._embeddings_cache is not None:
            return self._embeddings_cache

        model_exists = self._check_model_exists()
        has_internet = self._check_internet_connection()

        mirror_url, mirror_name = self._detect_best_mirror()
        if "HF_ENDPOINT" not in os.environ:
            os.environ["HF_ENDPOINT"] = mirror_url
            logger.debug(f"Auto-selected mirror: {mirror_name} ({mirror_url})")

        if self.verbose:
            self._print_model_status(model_exists, has_internet, mirror_url)

        try:
            from langchain_community.embeddings.fastembed import FastEmbedEmbeddings

            logger.debug(
                f"Using FastEmbed embeddings (cache: {self.cache_dir}, mirror: {mirror_name})"
            )

            embeddings = FastEmbedEmbeddings(
                model_name="BAAI/bge-small-zh-v1.5",
                max_length=512,
                cache_dir=str(self.cache_dir),
            )

            self._embeddings_cache = embeddings

            if self.verbose and not model_exists:
                from rich.console import Console

                console = Console()
                console.print("[green]✓ 嵌入模型加载成功[/green]")

            return embeddings

        except ImportError:
            logger.warning("FastEmbed not available. Install with: pip install fastembed")
            return None
        except Exception as e:
            error_msg = str(e)
            if not model_exists and not has_internet:
                logger.error(
                    "无法加载嵌入模型: 处于离线模式且模型未下载\n"
                    "请连接网络后运行: finchbot download-models"
                )
            elif "download" in error_msg.lower() or "connection" in error_msg.lower():
                logger.error(f"模型下载失败: {e}\n请检查网络连接或手动下载: finchbot download-models")
            else:
                logger.warning(f"FastEmbed embeddings failed: {e}")
            return None
