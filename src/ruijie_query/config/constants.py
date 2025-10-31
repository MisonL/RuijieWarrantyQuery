# -*- coding: utf-8 -*-
"""
配置常量定义
替代硬编码的magic number，提高代码可维护性
"""

# 配置限制值
class ConfigLimits:
    """配置参数的限制值常量"""
    # 查询相关
    QUERY_DELAY_MAX = 300        # 查询延时最大值 (秒)
    SAVE_INTERVAL_MAX = 1000      # 保存间隔最大值 (条)
    MAX_QUERY_ATTEMPTS = 10        # 最大查询尝试次数
    MAX_CAPTCHA_RETRIES = 5       # 最大验证码重试次数

    # AI设置相关
    AI_RETRY_ATTEMPTS_MIN = 1
    AI_RETRY_ATTEMPTS_MAX = 10
    AI_RETRY_DELAY_MIN = 1
    AI_RETRY_DELAY_MAX = 60
    AI_RATE_LIMIT_MIN = 1
    AI_RATE_LIMIT_MAX = 300
    AI_TEST_TIMEOUT_MIN = 10
    AI_TEST_TIMEOUT_MAX = 300

    # 日志相关
    LOG_BACKUP_COUNT_MIN = 0
    LOG_BACKUP_COUNT_MAX = 20

    # 通用限制
    STRING_LENGTH_MAX = 1000
    TIMEOUT_MAX = 300

# 默认配置值
class ConfigDefaults:
    """默认配置值常量"""
    # 通用配置默认值
    DEFAULT_QUERY_DELAY = 10
    DEFAULT_SAVE_INTERVAL = 10
    DEFAULT_MAX_QUERY_ATTEMPTS = 3
    DEFAULT_MAX_CAPTCHA_RETRIES = 2

    # AI设置默认值
    DEFAULT_AI_RETRY_ATTEMPTS = 3
    DEFAULT_AI_RETRY_DELAY = 5
    DEFAULT_AI_RATE_LIMIT_DELAY = 30
    DEFAULT_AI_TEST_TIMEOUT = 120

    # 日志默认值
    DEFAULT_LOG_LEVEL = "INFO"
    DEFAULT_LOG_TO_CONSOLE = True
    DEFAULT_LOG_MAX_BYTES = "1024KB"
    DEFAULT_LOG_BACKUP_COUNT = 5

    # 验证码设置默认值
    DEFAULT_CAPTCHA_PRIMARY_SOLVER = "ddddocr"
    DEFAULT_DDDDOOCR_MAX_ATTEMPTS = 3

# API配置
class APIConfig:
    """API相关配置"""
    # 支持的API类型
    SUPPORTED_API_TYPES = ["gemini", "openai", "grok", "none"]

    # 默认模型名称
    DEFAULT_MODELS = {
        "gemini": "gemini-pro-vision",
        "openai": "gpt-4o",
        "grok": "grok-1.0-vision"
    }

    # 请求限制
    MAX_RETRIES = 3
    REQUEST_TIMEOUT = 30
    RATE_LIMIT_DELAY = 1

# 日志配置
class LogConfig:
    """日志配置常量"""
    LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

    # 日志文件大小限制
    LOG_SIZE_MIN = "10KB"
    LOG_SIZE_MAX = "100MB"

    # 常用日志消息前缀
    PREFIX_SUCCESS = "✅"
    PREFIX_ERROR = "❌"
    PREFIX_WARNING = "⚠️"
    PREFIX_INFO = "💡"
    PREFIX_DEBUG = "🔍"

# 性能监控
class PerformanceConfig:
    """性能监控配置"""
    # 性能阈值 (秒)
    SLOW_OPERATION_THRESHOLD = 2.0    # 慢操作阈值
    VERY_SLOW_THRESHOLD = 5.0          # 很慢操作阈值

    # 内存使用阈值 (MB)
    MEMORY_WARNING_THRESHOLD = 100
    MEMORY_CRITICAL_THRESHOLD = 500

    # 缓存配置
    CACHE_TTL = 3600  # 缓存生存时间 (秒)
    CACHE_MAX_SIZE = 1000  # 缓存最大条目数