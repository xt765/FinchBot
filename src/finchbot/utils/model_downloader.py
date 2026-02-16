"""模型下载工具.

提供嵌入模型的预下载功能，支持安装时自动下载和手动下载。
"""

import os
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


def download_embedding_model(
    model_name: str = "BAAI/bge-small-zh-v1.5",
    cache_dir: Path | None = None,
    verbose: bool = True,
) -> bool:
    """下载嵌入模型.

    Args:
        model_name: 模型名称，默认为 BAAI/bge-small-zh-v1.5
        cache_dir: 缓存目录，默认为项目内 .models/fastembed
        verbose: 是否显示详细输出

    Returns:
        是否成功下载
    """
    try:
        from fastembed import TextEmbedding

        # 设置 HuggingFace 镜像（国内加速）
        if "HF_ENDPOINT" not in os.environ:
            os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

        # 确定缓存目录
        model_cache = cache_dir or get_model_cache_dir()
        model_cache.mkdir(parents=True, exist_ok=True)

        if verbose:
            logger.info(f"正在下载嵌入模型: {model_name}")
            logger.info(f"缓存目录: {model_cache}")

        # 使用 FastEmbed 下载模型
        # 这会触发模型下载并缓存到指定目录
        embedding = TextEmbedding(
            model_name=model_name,
            cache_dir=str(model_cache),
        )

        # 执行一次简单的嵌入来确保模型完全下载
        list(embedding.embed(["测试"]))

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

    # 检查是否有任何包含模型文件的子目录
    return any(item.exists() for item in model_cache.rglob("model_optimized.onnx"))


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
