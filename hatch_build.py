"""Hatchling 自定义构建钩子.

在包安装时自动下载嵌入模型。
"""

import os
import subprocess
import sys
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class ModelDownloadHook(BuildHookInterface):
    """安装时自动下载模型的钩子."""

    def initialize(self, version: str, build_data: dict) -> None:
        """初始化钩子，在构建时执行.

        Args:
            version: 版本号
            build_data: 构建数据
        """
        # 设置 HuggingFace 镜像（国内加速）
        if "HF_ENDPOINT" not in os.environ:
            os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

        # 获取项目根目录
        project_root = Path(__file__).parent

        # 检查模型是否已存在
        model_cache = project_root / ".models" / "fastembed"
        model_marker = model_cache / ".download_complete"

        if model_marker.exists():
            print("模型已存在，跳过下载")
            return

        # 检查是否有模型文件
        onnx_files = list(model_cache.rglob("model_optimized.onnx"))
        if onnx_files:
            print(f"检测到已有模型文件: {onnx_files[0]}")
            # 创建标记文件
            model_marker.touch()
            return

        print("=" * 60)
        print("FinchBot: 准备下载嵌入模型...")
        print("模型: BAAI/bge-small-zh-v1.5")
        print("镜像: https://hf-mirror.com (国内加速)")
        print("=" * 60)

        try:
            # 使用 subprocess 运行模型下载脚本
            # 这样可以避免在构建环境中直接导入 fastembed
            download_script = project_root / "src" / "finchbot" / "utils" / "model_downloader.py"

            if download_script.exists():
                result = subprocess.run(
                    [sys.executable, str(download_script), "-q"],
                    cwd=str(project_root),
                    capture_output=True,
                    text=True,
                    timeout=300,  # 5分钟超时
                )

                if result.returncode == 0:
                    print("✓ 模型下载完成")
                    # 创建标记文件
                    model_marker.touch()
                else:
                    print(f"模型下载失败: {result.stderr}")
                    print("提示: 首次运行时将会自动下载模型")
            else:
                print(f"下载脚本不存在: {download_script}")
                print("提示: 首次运行时将会自动下载模型")

        except subprocess.TimeoutExpired:
            print("模型下载超时，将在首次运行时自动下载")
        except Exception as e:
            print(f"模型下载出错: {e}")
            print("提示: 首次运行时将会自动下载模型")

        print("=" * 60)
