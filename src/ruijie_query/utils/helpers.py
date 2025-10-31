# -*- coding: utf-8 -*-
"""
辅助工具函数
"""

import logging
from typing import Any, Dict, Optional


def setup_logger(name: str, level: str = "INFO") -> logging.Logger:
    """设置日志记录器"""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))

    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


def validate_config(config: Dict[str, Any], required_keys: list) -> bool:
    """验证配置是否包含必需的键"""
    return all(key in config for key in required_keys)


def format_file_size(size_bytes: int) -> str:
    """格式化文件大小"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


def safe_get(dictionary: dict, key: str, default: Any = None) -> Any:
    """安全获取字典值"""
    try:
        return dictionary.get(key, default)
    except (AttributeError, TypeError):
        return default