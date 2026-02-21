"""模型下载工具.

提供嵌入模型的预下载功能，支持安装时自动下载和手动下载。
自动检测网络环境，国内用户使用 hf-mirror.com 镜像，国外用户使用官方源。
"""

import os
import socket
from pathlib import Path

from loguru import logger


def get_model_cache_dir() -> Path:
    """获取模型缓存目录.

    Returns:
        模型缓存目录路径
    """
    # 项目根目录
    project_root = Path(__file__).parent.parent.parent.parent
    return project_root / ".models" / "fastembed"


def _detect_best_mirror() -> tuple[str, str]:
    """检测最佳下载镜像.

    通过 TCP 连接测试（HTTP HEAD 可能被防火墙拦截），
    优先检测国内镜像（hf-mirror.com），如果可访问且延迟低则使用国内镜像。
    否则回退到官方源（huggingface.co）。

    超时机制：
    每个镜像源的连接测试超时时间为 2 秒。这确保了在网络不佳的情况下，检测过程不会阻塞太久。

    Returns:
        (镜像URL, 镜像名称) 元组
    """
    # 检测国内镜像
    try:
        # 尝试连接 hf-mirror.com 的 HTTPS 端口 (443)
        socket.create_connection(("hf-mirror.com", 443), timeout=2)
        return ("https://hf-mirror.com", "国内镜像")
    except OSError:
        pass

    # 检测官方源
    try:
        socket.create_connection(("huggingface.co", 443), timeout=2)
        return ("https://huggingface.co", "官方源")
    except OSError:
        pass

    # 默认使用官方源（可能离线，但会给出正确提示）
    return ("https://huggingface.co", "官方源")


def download_embedding_model(
    model_name: str = "BAAI/bge-small-zh-v1.5",
    cache_dir: Path | None = None,
    verbose: bool = True,
) -> bool:
    """下载嵌入模型.

    自动检测网络环境，选择最佳镜像源。

    Args:
        model_name: 模型名称，默认为 BAAI/bge-small-zh-v1.5
        cache_dir: 缓存目录，默认为项目内 .models/fastembed
        verbose: 是否显示详细输出

    Returns:
        是否成功下载
    """
    try:
        from fastembed import TextEmbedding

        # 检测最佳镜像（如果用户未手动设置）
        mirror_url, mirror_name = _detect_best_mirror()
        if "HF_ENDPOINT" not in os.environ:
            os.environ["HF_ENDPOINT"] = mirror_url

        # 确定缓存目录
        model_cache = cache_dir or get_model_cache_dir()
        model_cache.mkdir(parents=True, exist_ok=True)

        if verbose:
            logger.info(f"正在下载嵌入模型: {model_name}")
            logger.info(f"源: {mirror_name} ({mirror_url})")
            logger.info(f"缓存目录: {model_cache}")

        # 使用 FastEmbed 下载模型
        # 这会触发模型下载并缓存到指定目录
        embedding = TextEmbedding(
            model_name=model_name,
            cache_dir=str(model_cache),
        )

        # 执行一次简单的嵌入来确保模型完全下载
        list(embedding.embed(["test"]))

        if verbose:
            logger.info(f"✓ 模型下载完成: {model_name}")

        return True

    except ImportError:
        logger.error("fastembed 未安装，无法下载模型")
        logger.error("请运行: uv pip install fastembed>=0.4.0")
        return False
    except Exception as e:
        logger.error(f"模型下载失败: {e}")
        return False


def check_model_exists(
    model_name: str = "BAAI/bge-small-zh-v1.5",
    cache_dir: Path | None = None,
) -> bool:
    """检查模型是否已存在.

    Args:
        model_name: 模型名称
        cache_dir: 缓存目录

    Returns:
        模型是否存在
    """
    model_cache = cache_dir or get_model_cache_dir()

    # 在缓存目录中查找模型子目录
    if not model_cache.exists():
        return False

    # 检查是否有任何包含有效模型文件的子目录（文件大小 > 1MB）
    return any(
        item.exists() and item.stat().st_size > 1_000_000
        for item in model_cache.rglob("model_optimized.onnx")
    )


def ensure_models(
    model_name: str = "BAAI/bge-small-zh-v1.5",
    cache_dir: Path | None = None,
    verbose: bool = True,
) -> bool:
    """确保模型已下载，如不存在则自动下载.

    Args:
        model_name: 模型名称
        cache_dir: 缓存目录
        verbose: 是否显示详细输出

    Returns:
        模型是否可用
    """
    if check_model_exists(model_name, cache_dir):
        if verbose:
            logger.info(f"模型已存在: {model_name}")
        return True

    return download_embedding_model(model_name, cache_dir, verbose)


if __name__ == "__main__":
    # 命令行入口
    import sys

    verbose = "-q" not in sys.argv and "--quiet" not in sys.argv

    logger.info("开始下载 FinchBot 嵌入模型...")
    success = ensure_models(verbose=verbose)

    if success:
        logger.info("✓ 模型准备就绪")
        sys.exit(0)
    else:
        logger.error("✗ 模型下载失败")
        sys.exit(1)
