# -*- coding: utf-8 -*-
"""
性能监控模块
提供基本的执行时间统计和性能指标收集
"""

import time
import logging
from typing import Dict, List, Any, Optional
from ..config.constants import PerformanceConfig


class PerformanceMonitor:
    """简单的性能监控器"""

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.execution_times: Dict[str, List[float]] = {}
        self.operation_counts: Dict[str, int] = {}
        self.start_times: Dict[str, float] = {}

        # 🆕 优化4：性能监控智能模式
        self.lightweight_mode = False  # 轻量级模式开关
        self.minor_operations_enabled = True  # 是否监控小操作

    def start_timer(self, operation_name: str):
        """开始计时操作"""
        # 🆕 优化4a：轻量级模式下跳过小操作的监控
        if self.lightweight_mode and not self._should_monitor_operation(operation_name):
            return

        self.start_times[operation_name] = time.time()
        if operation_name not in self.execution_times:
            self.execution_times[operation_name] = []

    def _should_monitor_operation(self, operation_name: str) -> bool:
        """判断是否应该监控某个操作（轻量级模式优化）"""
        # 小于100ms的操作在轻量级模式下跳过
        minor_keywords = [
            "单个查询循环",
            "验证码识别-",
            "API调用-",
            "页面加载-",
            "元素查找-"
        ]

        # 检查是否包含minor keywords
        for keyword in minor_keywords:
            if keyword in operation_name:
                return False

        # 检查是否是初始化操作（通常需要监控）
        major_keywords = [
            "批量查询程序执行",
            "数据加载",
            "WebDriver",
            "AI渠道"
        ]

        for keyword in major_keywords:
            if keyword in operation_name:
                return True

        # 其他操作根据配置决定
        return self.minor_operations_enabled

    def end_timer(self, operation_name: str, log_slow_operations: bool = True) -> float:
        """结束计时操作，返回执行时间"""
        if operation_name not in self.start_times:
            # 🆕 优化4b：轻量级模式下不记录警告（因为某些操作被跳过了）
            if not (self.lightweight_mode and not self._should_monitor_operation(operation_name)):
                self.logger.warning(f"未找到操作 '{operation_name}' 的开始时间")
            return 0.0

        end_time = time.time()
        start_time = self.start_times.pop(operation_name, 0)
        execution_time = end_time - start_time

        # 🆕 优化4c：轻量级模式下跳过小操作的时间记录
        if self.lightweight_mode and not self._should_monitor_operation(operation_name):
            return execution_time

        # 记录执行时间
        self.execution_times[operation_name].append(execution_time)
        self.operation_counts[operation_name] = self.operation_counts.get(operation_name, 0) + 1

        # 记录慢操作
        if log_slow_operations and execution_time > PerformanceConfig.SLOW_OPERATION_THRESHOLD:
            status = "慢操作" if execution_time < PerformanceConfig.VERY_SLOW_THRESHOLD else "极慢操作"
            self.logger.info(
                f"⏱️  {operation_name} {status}: {execution_time:.2f}秒 "
                f"(阈值: {PerformanceConfig.SLOW_OPERATION_THRESHOLD}秒)"
            )

        return execution_time

    # 🆕 优化4d：添加轻量级模式控制方法
    def set_lightweight_mode(self, enabled: bool = True):
        """启用或禁用轻量级模式"""
        self.lightweight_mode = enabled
        if enabled:
            self.logger.info("性能监控已切换到轻量级模式，将跳过小操作的详细监控")

    def enable_minor_operations(self, enabled: bool = True):
        """启用或禁用小操作监控"""
        self.minor_operations_enabled = enabled

    def get_monitoring_status(self) -> Dict[str, Any]:
        """获取监控状态信息"""
        return {
            "lightweight_mode": self.lightweight_mode,
            "minor_operations_enabled": self.minor_operations_enabled,
            "total_operations": len(self.execution_times),
            "total_timers": len(self.start_times)
        }

    def get_average_time(self, operation_name: str) -> float:
        """获取操作的平均执行时间"""
        if operation_name not in self.execution_times or not self.execution_times[operation_name]:
            return 0.0
        return sum(self.execution_times[operation_name]) / len(self.execution_times[operation_name])

    def get_total_time(self, operation_name: str) -> float:
        """获取操作的总执行时间"""
        return sum(self.execution_times.get(operation_name, []))

    def get_operation_count(self, operation_name: str) -> int:
        """获取操作执行次数"""
        return self.operation_counts.get(operation_name, 0)

    def get_stats_summary(self) -> Dict[str, Any]:
        """获取性能统计摘要"""
        summary = {}
        for operation_name in self.execution_times:
            times = self.execution_times[operation_name]
            if times:
                summary[operation_name] = {
                    "count": len(times),
                    "total_time": sum(times),
                    "avg_time": sum(times) / len(times),
                    "min_time": min(times),
                    "max_time": max(times)
                }
        return summary

    def log_performance_report(self):
        """输出性能报告"""
        if not self.execution_times:
            self.logger.info("📊 无性能数据可报告")
            return

        self.logger.info("\n📊 性能报告")
        self.logger.info("=" * 50)

        for operation_name, stats in self.get_stats_summary().items():
            self.logger.info(
                f"🔧 {operation_name}: "
                f"{stats['count']}次, "
                f"平均{stats['avg_time']:.2f}秒, "
                f"总计{stats['total_time']:.2f}秒, "
                f"范围{stats['min_time']:.2f}-{stats['max_time']:.2f}秒"
            )

    def reset(self):
        """重置所有性能数据"""
        self.execution_times.clear()
        self.operation_counts.clear()
        self.start_times.clear()
        self.logger.debug("🔄 性能监控数据已重置")


# 全局性能监控实例
_global_monitor = None


def get_monitor() -> PerformanceMonitor:
    """获取全局性能监控实例"""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = PerformanceMonitor()
    return _global_monitor


def monitor_operation(operation_name: str, log_slow: bool = True):
    """操作计时装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            monitor = get_monitor()
            monitor.start_timer(operation_name)
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                monitor.end_timer(operation_name, log_slow)
        return wrapper
    return decorator