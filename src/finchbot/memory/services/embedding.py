"""Embedding 服务模块.

提供向量嵌入模型的加载、网络检查和镜像选择功能。
优化版：延迟加载模型，异步网络检查，减少初始化时间。
"""

import os
import socket
import threading
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
    """向量嵌入服务 - 优化版.

    特性：
    1. 延迟加载模型（首次使用时加载）
    2. 异步网络检查（后台线程）
    3. 缓存网络状态避免重复检查
    """

    def __init__(self, cache_dir: Path | None = None, verbose: bool = True):
        self.cache_dir = cache_dir or MODEL_CACHE_DIR
        self.verbose = verbose
        self._embeddings_cache: FastEmbedEmbeddings | None = None
        self._model_loading = False
        self._model_load_error: Exception | None = None

        # 网络状态缓存
        self._network_checked = False
        self._has_internet = False
        self._mirror_url = "https://huggingface.co"
        self._mirror_name = "官方源"

        self._ensure_cache_dir()

        # 后台异步检查网络（非阻塞）
        self._start_network_check()

    def _ensure_cache_dir(self) -> None:
        """确保缓存目录存在."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _start_network_check(self) -> None:
        """启动后台网络检查线程."""
        thread = threading.Thread(target=self._check_network_async, daemon=True)
        thread.start()

    def _check_network_async(self) -> None:
        """异步检查网络连接和镜像.
        
        策略：
        1. 优先检查国内镜像 (hf-mirror.com)
        2. 如果国内镜像可用，直接使用，视为有网络
        3. 如果国内镜像不可用，检查官方源 (huggingface.co)
        """
        try:
            # 1. 优先检测国内镜像
            try:
                socket.create_connection(("hf-mirror.com", 443), timeout=2)
                self._has_internet = True
                self._mirror_url = "https://hf-mirror.com"
                self._mirror_name = "国内镜像"
                self._network_checked = True
                logger.debug(f"Network check completed: {self._mirror_name}, internet=True")
                return
            except OSError:
                pass

            # 2. 检测官方源
            try:
                socket.create_connection(("huggingface.co", 443), timeout=2)
                self._has_internet = True
                self._mirror_url = "https://huggingface.co"
                self._mirror_name = "官方源"
            except OSError:
                self._has_internet = False
                self._mirror_name = "无连接"

            self._network_checked = True
            logger.debug(
                f"Network check completed: {self._mirror_name}, internet={self._has_internet}"
            )
        except Exception as e:
            logger.debug(f"Network check failed: {e}")
            self._network_checked = True

    def _check_model_exists(self) -> bool:
        """检查模型文件是否存在且有效（文件大小 > 1MB）."""
        if not self.cache_dir.exists():
            return False
        return any(
            item.exists() and item.stat().st_size > 1_000_000
            for item in self.cache_dir.rglob("model_optimized.onnx")
        )

    def _print_model_status(self, model_exists: bool) -> None:
        """打印模型状态提示."""
        from rich.console import Console
        from rich.panel import Panel

        console = Console()

        if model_exists:
            logger.info(f"✓ 嵌入模型已就绪: {self.cache_dir}")
            return

        # 等待网络检查完成（最多等3秒）
        import time

        wait_start = time.time()
        while not self._network_checked and time.time() - wait_start < 3.0:
            time.sleep(0.05)

        # 网络检查未完成时，假设有网络（让下载尝试进行）
        if not self._network_checked:
            logger.debug("Network check timeout, assuming online mode")
            self._has_internet = True

        if self._has_internet:
            mirror_display = f"{self._mirror_name} ({self._mirror_url})"
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

    def _load_model(self) -> Optional["FastEmbedEmbeddings"]:
        """实际加载模型（在后台线程中执行）."""
        try:
            from langchain_community.embeddings.fastembed import FastEmbedEmbeddings

            # 确保网络检查完成
            if not self._network_checked:
                import time

                wait_start = time.time()
                while not self._network_checked and time.time() - wait_start < 3.0:
                    time.sleep(0.05)

            # 设置镜像
            if "HF_ENDPOINT" not in os.environ and self._mirror_url:
                os.environ["HF_ENDPOINT"] = self._mirror_url
                logger.debug(f"Using mirror: {self._mirror_name} ({self._mirror_url})")

            logger.debug(f"Loading FastEmbed model (cache: {self.cache_dir})...")

            embeddings = FastEmbedEmbeddings(
                model_name="BAAI/bge-small-zh-v1.5",
                max_length=512,
                cache_dir=str(self.cache_dir),
            )

            logger.debug("FastEmbed model loaded successfully")
            return embeddings

        except ImportError:
            logger.warning("FastEmbed not available. Install with: uv add fastembed")
            return None
        except Exception as e:
            logger.warning(f"Failed to load FastEmbed model: {e}")
            return None

    def get_embeddings(self) -> Optional["FastEmbedEmbeddings"]:
        """获取 FastEmbed 本地模型（懒加载）."""
        # 如果已缓存，直接返回
        if self._embeddings_cache is not None:
            return self._embeddings_cache

        # 如果正在加载中，等待完成
        if self._model_loading:
            import time

            wait_start = time.time()
            while self._model_loading and time.time() - wait_start < 30.0:
                time.sleep(0.1)
            return self._embeddings_cache

        # 开始加载
        self._model_loading = True
        model_exists = self._check_model_exists()

        try:
            if self.verbose:
                self._print_model_status(model_exists)

            self._embeddings_cache = self._load_model()

            if self.verbose and self._embeddings_cache and not model_exists:
                from rich.console import Console

                console = Console()
                console.print("[green]✓ 嵌入模型加载成功[/green]")

            return self._embeddings_cache

        finally:
            self._model_loading = False

    def preload_model(self) -> None:
        """预加载模型（可选，在后台调用）."""
        if self._embeddings_cache is None and not self._model_loading:
            thread = threading.Thread(target=self.get_embeddings, daemon=True)
            thread.start()
