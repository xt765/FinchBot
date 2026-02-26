"""缓存工具模块.

提供基于文件修改时间的通用缓存实现.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Generic, TypeVar

T = TypeVar("T")


@dataclass
class CacheEntry(Generic[T]):
    """缓存条目."""

    value: T
    mtime: float
    expires: float | None = None


class FileBasedCache(Generic[T]):
    """基于文件修改时间的缓存.

    自动检测文件修改并刷新缓存.
    """

    def __init__(
        self,
        loader: Callable[[str], T | None],
        ttl: float | None = None,
    ) -> None:
        """初始化缓存.

        Args:
            loader: 数据加载函数
            ttl: 缓存过期时间（秒），None表示不过期
        """
        self._loader = loader
        self._ttl = ttl
        self._cache: dict[str, CacheEntry[T]] = {}

    def get(self, key: str, file_path: Path | None = None) -> T | None:
        """获取缓存值.

        Args:
            key: 缓存键
            file_path: 关联的文件路径（用于检测修改）

        Returns:
            缓存值，未找到或已过期返回None
        """
        now = time.time()

        # 检查缓存
        if key in self._cache:
            entry = self._cache[key]

            # 检查TTL
            if self._ttl and entry.expires and now > entry.expires:
                del self._cache[key]
            # 检查文件修改
            elif file_path and file_path.exists():
                if file_path.stat().st_mtime <= entry.mtime:
                    return entry.value
                # 文件已修改，继续加载新值
            else:
                return entry.value

        # 加载新值
        value = self._loader(key)
        if value is not None:
            mtime = file_path.stat().st_mtime if file_path and file_path.exists() else now
            expires = now + self._ttl if self._ttl else None
            self._cache[key] = CacheEntry(value, mtime, expires)

        return value

    def set(self, key: str, value: T, file_path: Path | None = None) -> None:
        """手动设置缓存值.

        Args:
            key: 缓存键
            value: 缓存值
            file_path: 关联的文件路径
        """
        now = time.time()
        mtime = file_path.stat().st_mtime if file_path and file_path.exists() else now
        expires = now + self._ttl if self._ttl else None
        self._cache[key] = CacheEntry(value, mtime, expires)

    def invalidate(self, key: str | None = None) -> None:
        """使缓存失效.

        Args:
            key: 要失效的键，None表示清除所有缓存
        """
        if key is None:
            self._cache.clear()
        else:
            self._cache.pop(key, None)

    def clear(self) -> None:
        """清除所有缓存."""
        self._cache.clear()

    def get_info(self) -> dict:
        """获取缓存信息.

        Returns:
            缓存统计信息
        """
        return {
            "size": len(self._cache),
            "keys": list(self._cache.keys()),
        }
