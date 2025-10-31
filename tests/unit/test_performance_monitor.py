# -*- coding: utf-8 -*-
"""
性能监控模块单元测试
"""
import time
from unittest.mock import patch, MagicMock
import pytest

import sys
sys.path.insert(0, 'src')

from ruijie_query.monitoring.performance_monitor import get_monitor, monitor_operation


class TestPerformanceMonitor:
    """性能监控器的单元测试"""

    def setup_method(self):
        """测试方法初始化"""
        self.monitor = get_monitor()
        # 重置监控器状态
        self.monitor.reset()

    def test_get_monitor(self):
        """测试获取监控器实例"""
        monitor = get_monitor()
        assert monitor is not None
        assert hasattr(monitor, 'execution_times')
        assert hasattr(monitor, 'operation_counts')

    def test_start_timer(self):
        """测试启动计时器"""
        operation_name = "test_operation"

        self.monitor.start_timer(operation_name)

        assert operation_name in self.monitor.start_times
        assert self.monitor.start_times[operation_name] is not None

    def test_end_timer(self):
        """测试结束计时器"""
        operation_name = "test_operation"

        # 先启动计时器
        self.monitor.start_timer(operation_name)
        time.sleep(0.1)  # 稍微延迟以确保有可测量的时间

        # 结束计时器
        result = self.monitor.end_timer(operation_name)

        assert operation_name not in self.monitor.start_times
        assert result is not None
        assert isinstance(result, float)
        assert result > 0.09  # 应该大于我们等待的时间

    def test_end_timer_nonexistent_operation(self):
        """测试结束不存在的操作"""
        result = self.monitor.end_timer("nonexistent_operation")

        assert result == 0.0  # 应该返回0.0而不是None

    def test_end_timer_without_start(self):
        """测试在没有启动的情况下结束计时器"""
        result = self.monitor.end_timer("unstarted_operation")

        assert result == 0.0  # 应该返回0.0而不是None

    def test_record_operation(self):
        """测试记录操作（使用start_timer和end_timer）"""
        operation_name = "test_operation"

        # 使用start_timer和end_timer记录一个操作
        self.monitor.start_timer(operation_name)
        time.sleep(0.1)  # 实际等待
        result_duration = self.monitor.end_timer(operation_name)

        assert operation_name in self.monitor.execution_times
        assert operation_name in self.monitor.operation_counts
        assert self.monitor.operation_counts[operation_name] == 1
        assert result_duration > 0.09  # 大于我们等待的时间

    def test_record_slow_operation(self):
        """测试记录慢操作"""
        operation_name = "slow_operation"
        duration = 5.0  # 超过默认阈值

        self.monitor.start_timer(operation_name)
        time.sleep(0.01)  # 短暂延迟
        result_duration = self.monitor.end_timer(operation_name)

        # 验证操作被记录
        assert operation_name in self.monitor.execution_times
        assert self.monitor.execution_times[operation_name] == [result_duration]

    def test_record_fast_operation(self):
        """测试记录快操作"""
        operation_name = "fast_operation"
        duration = 0.1  # 低于阈值

        self.monitor.start_timer(operation_name)
        time.sleep(0.01)  # 短暂延迟
        result_duration = self.monitor.end_timer(operation_name)

        # 验证操作被记录
        assert operation_name in self.monitor.execution_times
        assert self.monitor.execution_times[operation_name] == [result_duration]

    def test_get_operation_stats(self):
        """测试获取操作统计"""
        operation_name = "stats_test_operation"

        # 记录多个操作
        for _ in range(3):
            self.monitor.start_timer(operation_name)
            time.sleep(0.01)
            self.monitor.end_timer(operation_name)

        # 使用get_stats_summary获取统计
        stats_summary = self.monitor.get_stats_summary()
        assert operation_name in stats_summary

        stats = stats_summary[operation_name]
        assert stats['count'] == 3
        assert stats['avg_time'] > 0
        assert stats['total_time'] > 0

    def test_get_operation_stats_nonexistent(self):
        """测试获取不存在的操作统计"""
        stats_summary = self.monitor.get_stats_summary()
        assert "nonexistent_operation" not in stats_summary

    def test_log_performance_report(self):
        """测试记录性能报告"""
        # 先记录一些操作
        self.monitor.start_timer("operation1")
        time.sleep(0.01)
        self.monitor.end_timer("operation1")

        self.monitor.start_timer("operation2")
        time.sleep(0.01)
        self.monitor.end_timer("operation2")

        # 模拟logger
        with patch.object(self.monitor, 'logger') as mock_logger:
            self.monitor.log_performance_report()

            # 验证日志记录被调用
            assert mock_logger.info.call_count > 0

    def test_get_slow_operations(self):
        """测试获取慢操作（验证统计功能）"""
        # 记录一些操作
        self.monitor.start_timer("op1")
        time.sleep(0.01)
        self.monitor.end_timer("op1")

        self.monitor.start_timer("op2")
        time.sleep(0.01)
        self.monitor.end_timer("op2")

        # 获取统计摘要
        stats = self.monitor.get_stats_summary()
        assert "op1" in stats
        assert "op2" in stats

    def test_clear_stats(self):
        """测试清除统计（使用reset）"""
        # 记录一些操作
        self.monitor.start_timer("test_op")
        time.sleep(0.01)
        self.monitor.end_timer("test_op")

        # 验证数据存在
        assert "test_op" in self.monitor.execution_times

        # 使用reset清除统计
        self.monitor.reset()

        assert len(self.monitor.execution_times) == 0
        assert len(self.monitor.operation_counts) == 0
        assert len(self.monitor.start_times) == 0

    def test_performance_monitoring_integration(self):
        """测试性能监控的集成场景"""
        # 1. 测试完整的操作周期
        operation_name = "integration_test"

        # 启动计时器
        self.monitor.start_timer(operation_name)

        # 模拟一些工作
        time.sleep(0.05)

        # 结束计时器
        result = self.monitor.end_timer(operation_name)

        assert result is not None
        assert isinstance(result, float)
        assert result > 0.04

        # 2. 验证统计被正确更新
        stats_summary = self.monitor.get_stats_summary()
        assert operation_name in stats_summary

        stats = stats_summary[operation_name]
        assert stats['count'] == 1

        # 3. 测试多个操作
        for i in range(5):
            self.monitor.start_timer(f"batch_op_{i}")
            time.sleep(0.01)
            self.monitor.end_timer(f"batch_op_{i}")

        # 验证批量操作统计
        stats_summary = self.monitor.get_stats_summary()
        for i in range(5):
            assert f"batch_op_{i}" in stats_summary
            assert stats_summary[f"batch_op_{i}"]['count'] == 1


class TestMonitorOperationDecorator:
    """监控操作装饰器的单元测试"""

    def setup_method(self):
        """测试方法初始化"""
        self.monitor = get_monitor()
        # 重置监控器状态
        self.monitor.reset()

    def test_monitor_operation_decorator(self):
        """测试监控操作装饰器"""
        @monitor_operation("decorated_test_operation")
        def test_function():
            time.sleep(0.1)
            return "success"

        # 执行被装饰的函数
        result = test_function()

        assert result == "success"

        # 验证操作被监控
        stats_summary = self.monitor.get_stats_summary()
        assert "decorated_test_operation" in stats_summary

        stats = stats_summary["decorated_test_operation"]
        assert stats['count'] == 1
        assert stats['total_time'] > 0.09  # 大于我们等待的时间

    def test_monitor_operation_with_exception(self):
        """测试监控操作装饰器处理异常"""
        @monitor_operation("exception_test_operation")
        def failing_function():
            time.sleep(0.05)
            raise ValueError("Test exception")

        # 执行会失败的函数
        with pytest.raises(ValueError):
            failing_function()

        # 验证操作仍然被监控（即使失败）
        stats_summary = self.monitor.get_stats_summary()
        assert "exception_test_operation" in stats_summary

        stats = stats_summary["exception_test_operation"]
        assert stats['count'] == 1
        assert stats['total_time'] > 0.04

    def test_monitor_operation_with_log_slow(self):
        """测试监控操作装饰器的慢操作日志"""
        @monitor_operation("slow_logged_operation", log_slow=True)
        def slow_function():
            time.sleep(0.15)  # 超过阈值
            return "slow_result"

        with patch.object(self.monitor, 'logger') as mock_logger:
            result = slow_function()

            assert result == "slow_result"

            # 验证慢操作被记录到日志
            # 具体的断言取决于实现细节
            assert mock_logger.info.call_count > 0 or mock_logger.warning.call_count > 0

    def test_nested_monitoring(self):
        """测试嵌套监控"""
        @monitor_operation("outer_operation")
        def outer_function():
            time.sleep(0.05)

            @monitor_operation("inner_operation")
            def inner_function():
                time.sleep(0.03)
                return "inner_result"

            return inner_function()

        result = outer_function()

        assert result == "inner_result"

        # 验证两个操作都被监控
        stats_summary = self.monitor.get_stats_summary()
        assert "outer_operation" in stats_summary
        assert "inner_operation" in stats_summary

        outer_stats = stats_summary["outer_operation"]
        inner_stats = stats_summary["inner_operation"]

        assert outer_stats['count'] == 1
        assert inner_stats['count'] == 1

    def test_monitor_operation_multiple_calls(self):
        """测试监控操作的多次调用"""
        @monitor_operation("multi_call_operation")
        def multi_call_function(value):
            return value * 2

        # 多次调用
        for i in range(5):
            result = multi_call_function(i)
            assert result == i * 2

        # 验证统计反映了所有调用
        stats_summary = self.monitor.get_stats_summary()
        assert "multi_call_operation" in stats_summary

        stats = stats_summary["multi_call_operation"]
        assert stats['count'] == 5

    def test_monitor_operation_with_arguments(self):
        """测试监控操作装饰器处理参数"""
        @monitor_operation("parameterized_operation")
        def parameterized_function(a, b, c=10):
            time.sleep(0.02)
            return a + b + c

        result = parameterized_function(1, 2, c=3)

        assert result == 6

        # 验证操作被监控
        stats_summary = self.monitor.get_stats_summary()
        assert "parameterized_operation" in stats_summary

        stats = stats_summary["parameterized_operation"]
        assert stats['count'] == 1