"""日志配置工具.

提供统一的日志配置管理，支持：
1. 控制台输出开关与级别控制
2. 文件日志自动分割与归档
3. 统一的日志格式
4. 异常捕获与记录
"""

import sys
from pathlib import Path

from loguru import logger

# 默认日志格式
LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)


def setup_logger(
    log_dir: Path | str = "logs",
    console_level: str = "INFO",
    file_level: str = "DEBUG",
    rotation: str = "00:00",
    retention: str = "30 days",
    console_enabled: bool = True,
) -> None:
    """配置全局日志系统.

    Args:
        log_dir: 日志文件存储目录。
        console_level: 控制台输出级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)。
        file_level: 文件记录级别。
        rotation: 日志轮转规则 (如 "00:00" 表示每天午夜轮转)。
        retention: 日志保留时间 (如 "30 days")。
        console_enabled: 是否启用控制台输出。
    """
    # 移除默认的 handler
    logger.remove()

    # 1. 配置控制台输出
    if console_enabled:
        logger.add(
            sys.stderr,
            level=console_level,
            format=LOG_FORMAT,
            enqueue=True,  # 线程安全
            backtrace=True,
            diagnose=True,
        )

    # 2. 配置文件输出
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # 普通日志 (按日期分割)
    logger.add(
        log_path / "finchbot_{time:YYYY-MM-DD}.log",
        level=file_level,
        format=LOG_FORMAT,
        rotation=rotation,
        retention=retention,
        enqueue=True,
        encoding="utf-8",
        backtrace=True,
        diagnose=True,
    )

    # 错误日志 (单独存储，方便排查)
    logger.add(
        log_path / "error_{time:YYYY-MM-DD}.log",
        level="ERROR",
        format=LOG_FORMAT,
        rotation=rotation,
        retention=retention,
        enqueue=True,
        encoding="utf-8",
        backtrace=True,
        diagnose=True,
    )

    logger.debug(f"Logger initialized. Log directory: {log_path.absolute()}")
