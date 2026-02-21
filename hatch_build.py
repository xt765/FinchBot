"""Hatch 构建钩子 - 安装时自动下载 Embedding 模型.

该钩子在 wheel 安装后自动下载 FastEmbed 模型，确保用户无需手动配置即可使用。
"""

from __future__ import annotations

import os
import shutil
import socket
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


def _detect_best_mirror() -> tuple[str, str]:
    """检测最佳下载镜像.

    通过 TCP 连接测试，优先检测国内镜像（hf-mirror.com）。
    如果可访问则使用国内镜像，否则回退到官方源（huggingface.co）。

    Returns:
        (镜像URL, 镜像名称) 元组
    """
    # 检测国内镜像
    try:
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

    # 默认使用国内镜像（国内用户更常见）
    return ("https://hf-mirror.com", "国内镜像")


def _check_model_exists(cache_dir: Path) -> bool:
    """检查模型文件是否存在且有效（文件大小 > 1MB）."""
    if not cache_dir.exists():
        return False
    return any(
        item.exists() and item.stat().st_size > 1_000_000
        for item in cache_dir.rglob("model_optimized.onnx")
    )


def _clean_incomplete_cache(cache_dir: Path) -> None:
    """清理不完整的缓存目录."""
    if cache_dir.exists():
        # 检查是否有 .incomplete 文件
        if any(cache_dir.rglob("*.incomplete")):
            print("[构建钩子] 检测到不完整的缓存，正在清理...")
            shutil.rmtree(cache_dir)
        # 检查模型文件是否有效
        elif not _check_model_exists(cache_dir):
            # 有缓存目录但没有有效的模型文件
            onnx_files = list(cache_dir.rglob("*.onnx"))
            if onnx_files:
                # 有 onnx 文件但太小，说明下载不完整
                print("[构建钩子] 检测到不完整的模型文件，正在清理...")
                shutil.rmtree(cache_dir)


def _download_model(cache_dir: Path) -> bool:
    """下载嵌入模型."""
    try:
        # 清理不完整的缓存
        _clean_incomplete_cache(cache_dir)

        # 检测最佳镜像（如果用户未手动设置）
        mirror_url, mirror_name = _detect_best_mirror()
        if "HF_ENDPOINT" not in os.environ:
            os.environ["HF_ENDPOINT"] = mirror_url

        cache_dir.mkdir(parents=True, exist_ok=True)

        print(f"[构建钩子] 正在下载嵌入模型: BAAI/bge-small-zh-v1.5")
        print(f"[构建钩子] 源: {mirror_name} ({mirror_url})")
        print(f"[构建钩子] 缓存目录: {cache_dir}")

        from fastembed import TextEmbedding

        embedding = TextEmbedding(
            model_name="BAAI/bge-small-zh-v1.5",
            cache_dir=str(cache_dir),
        )

        # 执行一次简单的嵌入来确保模型完全下载
        print("[构建钩子] 执行测试嵌入...")
        result = list(embedding.embed(["test"]))
        print(f"[构建钩子] 测试嵌入完成，维度: {len(result[0]) if result else 0}")

        print("[构建钩子] 模型下载完成")
        return True

    except ImportError as e:
        print(f"[构建钩子] fastembed 未安装，跳过模型下载: {e}")
        return False
    except Exception as e:
        print(f"[构建钩子] 模型下载失败: {e}")
        import traceback
        traceback.print_exc()
        return False


class ModelDownloadHook(BuildHookInterface):
    """模型下载构建钩子.

    在 wheel 安装后自动下载 FastEmbed 模型到项目缓存目录。
    """

    def initialize(self, version: str, build_data: dict) -> None:
        """构建初始化."""
        pass

    def finalize(self, version: str, build_data: dict, artifact_path: str) -> None:
        """构建完成后下载模型."""
        try:
            project_root = Path(self.root)
            model_cache = project_root / ".models" / "fastembed"

            if _check_model_exists(model_cache):
                print("[构建钩子] 嵌入模型已存在且有效，跳过下载")
                return

            print("[构建钩子] 首次安装，正在下载嵌入模型...")

            success = _download_model(model_cache)

            if not success:
                print("[构建钩子] 模型下载失败，可稍后手动运行: finchbot models download")

        except Exception as e:
            print(f"[构建钩子] 模型下载跳过: {e}")
            import traceback
            traceback.print_exc()
