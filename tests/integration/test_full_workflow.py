# -*- coding: utf-8 -*-
"""
集成测试 - 完整工作流程
"""
import tempfile
import pandas as pd
import os
import time
from unittest.mock import patch, MagicMock
import pytest

import sys
sys.path.insert(0, 'src')

from ruijie_query.core.app import RuijieQueryApp
from ruijie_query.config.config import ConfigManager
from ruijie_query.core.data_manager import DataManager
from ruijie_query.captcha.captcha_solver import CaptchaSolver
from ruijie_query.browser.webdriver_manager import WebDriverManager


class TestFullWorkflowIntegration:
    """完整工作流程集成测试"""

    def setup_method(self):
        """测试方法初始化"""
        self.temp_dir = tempfile.mkdtemp()

        # 创建测试Excel文件
        self.excel_file = os.path.join(self.temp_dir, 'test_integration.xlsx')
        self.create_test_excel_file()

        # 创建临时配置文件
        self.config_file = os.path.join(self.temp_dir, 'test_config.ini')
        self.create_test_config_file()

    def teardown_method(self):
        """测试方法清理"""
        if os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir)

    def create_test_excel_file(self):
        """创建测试Excel文件"""
        test_data = pd.DataFrame({
            'Serial Number': ['SN001', 'SN002', 'SN003', 'SN004', 'SN005'],
            '型号': ['Model1', 'Model2', 'Model3', 'Model4', 'Model5'],
            '保修状态': [None, '有效', None, '失效', None],
            '查询状态': [None, '成功', None, None, None]
        })
        test_data.to_excel(self.excel_file, sheet_name='Sheet1', index=False)

    def create_test_config_file(self):
        """创建测试配置文件"""
        config_content = """[General]
excel_file_path = {excel_file}
sheet_name = Sheet1
sn_column_name = Serial Number
query_delay = 1
save_interval = 3
max_query_attempts = 2
max_captcha_retries = 2

[CaptchaSettings]
captcha_primary_solver = ddddocr
captcha_enable_ddddocr = True
captcha_enable_ai = False
ddddocr_max_attempts = 2

[AI_Settings]
retry_attempts = 2
retry_delay = 2
rate_limit_delay = 10
ai_test_timeout = 30

[ResultColumns]
型号 = 型号
保修状态 = 保修状态
查询状态 = 查询状态

[Logging]
log_level = INFO
log_to_console = False
""".format(excel_file=self.excel_file)

        with open(self.config_file, 'w') as f:
            f.write(config_content)

    def test_config_manager_and_data_manager_integration(self):
        """测试配置管理器和数据管理器的集成"""
        # 1. 使用配置管理器加载配置
        config_manager = ConfigManager(config_file=self.config_file)

        # 2. 使用数据管理器加载数据
        data_manager = DataManager(
            file_path=self.excel_file,
            sheet_name='Sheet1',
            sn_column='Serial Number',
            result_columns={'型号': '型号', '保修状态': '保修状态', '查询状态': '查询状态'}
        )

        # 3. 执行数据加载
        df = data_manager.load_data()

        # 4. 验证集成结果
        assert df is not None
        assert len(df) == 5
        assert 'Serial Number' in df.columns
        assert '型号' in df.columns
        assert '保修状态' in df.columns
        assert '查询状态' in df.columns

        # 5. 测试数据更新和保存
        data_manager.update_result(0, {
            '型号': 'UpdatedModel1',
            '保修状态': '有效',
            '查询状态': '成功'
        })

        data_manager.save_data()

        # 6. 重新加载验证更新
        df_loaded = pd.read_excel(self.excel_file, sheet_name='Sheet1')
        assert df_loaded.at[0, '型号'] == 'UpdatedModel1'
        assert df_loaded.at[0, '保修状态'] == '有效'
        assert df_loaded.at[0, '查询状态'] == '成功'

    def test_captcha_solver_integration(self):
        """测试验证码识别器的集成"""
        # 1. 配置验证码解析器
        captcha_config = {
            'primary_solver': 'ddddocr',
            'enable_ddddocr': True,
            'enable_ai': False,
            'ddddocr_max_attempts': 2
        }

        ai_settings = {
            'retry_attempts': 2,
            'retry_delay': 2,
            'rate_limit_delay': 10,
            'ai_test_timeout': 30
        }

        channels = []  # 没有AI渠道

        # 2. 创建验证码解析器
        captcha_solver = CaptchaSolver(
            captcha_config=captcha_config,
            ai_settings=ai_settings,
            channels=channels
        )

        # 3. 测试渠道可用性
        available_channels = captcha_solver.test_channels_availability()

        # 应该没有AI渠道可用
        assert len(available_channels) == 0

        # 4. 测试ddddocr可用性
        # 这里我们只测试初始化，因为实际的图像识别需要真实的图像数据
        assert captcha_solver.ddddocr_enabled_internal is True

    def test_webdriver_manager_integration(self):
        """测试WebDriver管理器的集成"""
        # 1. 创建WebDriver管理器
        webdriver_manager = WebDriverManager()

        # 2. 测试平台检测
        driver_dir, driver_path = webdriver_manager._get_platform_specific_driver_path()

        assert driver_dir is not None
        assert driver_path is not None

        # 3. 测试驱动策略配置
        assert webdriver_manager.driver_strategies['version_check'] is True
        assert webdriver_manager.driver_strategies['offline_fallback'] is True
        assert webdriver_manager.driver_strategies['download_resume'] is True

    def test_app_initialization_integration(self):
        """测试应用程序初始化的集成"""
        # 1. 创建配置管理器
        config_manager = ConfigManager(config_file=self.config_file)

        # 2. 模拟其他组件的初始化
        with patch('ruijie_query.core.data_manager.DataManager') as mock_data_manager, \
             patch('ruijie_query.captcha.captcha_solver.CaptchaSolver') as mock_captcha_solver, \
             patch('ruijie_query.browser.webdriver_manager.WebDriverManager') as mock_webdriver_manager:

            # 3. 初始化应用程序
            app = RuijieQueryApp(config_manager)

            # 4. 验证所有组件被正确初始化
            assert app.config_manager == config_manager
            assert app.general_config is not None
            assert app.captcha_config is not None
            assert app.ai_config is not None
            assert app.result_columns is not None
            assert app.logging_config is not None

            # 5. 验证设置被正确应用
            assert app.general_config['excel_file_path'] == self.excel_file
            assert app.general_config['sheet_name'] == 'Sheet1'
            assert app.captcha_config['enable_ddddocr'] is True
            assert app.captcha_config['enable_ai'] is False

    def test_full_query_workflow_integration(self):
        """测试完整查询工作流程的集成"""
        # 1. 创建配置管理器
        config_manager = ConfigManager(config_file=self.config_file)

        # 2. 模拟完整的应用程序流程
        with patch('ruijie_query.core.data_manager.DataManager') as mock_data_manager, \
             patch('ruijie_query.captcha.captcha_solver.CaptchaSolver') as mock_captcha_solver, \
             patch('ruijie_query.browser.webdriver_manager.WebDriverManager') as mock_webdriver_manager, \
             patch('ruijie_query.browser.page_objects.ruijie_page.RuijieQueryPage') as mock_page_class:

            # 3. 准备测试数据
            test_data = pd.DataFrame({
                'Serial Number': ['SN001', 'SN002', 'SN003'],
                '查询状态': [None, None, None]
            })

            # 4. 模拟数据管理器
            mock_dm_instance = MagicMock()
            mock_dm_instance.load_data.return_value = test_data
            mock_dm_instance.get_unqueried_serial_numbers.return_value = [(0, 'SN001'), (1, 'SN002'), (2, 'SN003')]
            mock_dm_instance.save_data.return_value = None
            mock_data_manager.return_value = mock_dm_instance

            # 5. 模拟验证码解析器
            mock_captcha_instance = MagicMock()
            mock_captcha_instance.test_channels_availability.return_value = []
            mock_captcha_solver.return_value = mock_captcha_instance

            # 6. 模拟WebDriver管理器
            mock_webdriver_instance = MagicMock()
            mock_driver = MagicMock()
            mock_webdriver_instance.initialize_driver.return_value = mock_driver
            mock_webdriver_manager.return_value = mock_webdriver_instance

            # 7. 模拟页面对象
            mock_page = MagicMock()
            mock_page.query_single_device.return_value = {'查询状态': '成功'}
            mock_page_class.return_value = mock_page

            # 8. 运行应用程序
            app = RuijieQueryApp(config_manager)
            app.logger = MagicMock()  # 使用模拟的logger

            # 9. 执行运行流程
            app.run()

            # 10. 验证各个组件正确协作
            mock_dm_instance.load_data.assert_called_once()
            mock_captcha_instance.test_channels_availability.assert_called_once()
            mock_webdriver_instance.initialize_driver.assert_called_once()

            # 11. 验证查询被处理（每个序列号应该被查询一次）
            assert mock_page.query_single_device.call_count == 3

            # 12. 验证数据被保存
            assert mock_dm_instance.save_data.call_count >= 1

    def test_error_handling_integration(self):
        """测试集成场景下的错误处理"""
        # 1. 创建配置管理器
        config_manager = ConfigManager(config_file=self.config_file)

        # 2. 模拟组件初始化失败
        with patch('ruijie_query.core.data_manager.DataManager') as mock_data_manager:
            # 模拟数据加载失败
            mock_dm_instance = MagicMock()
            mock_dm_instance.load_data.return_value = None  # 加载失败
            mock_data_manager.return_value = mock_dm_instance

            # 3. 运行应用程序
            app = RuijieQueryApp(config_manager)
            app.logger = MagicMock()

            # 4. 执行运行流程
            app.run()

            # 5. 验证错误被正确处理
            mock_dm_instance.load_data.assert_called_once()
            app.logger.error.assert_any_call("无法加载Excel数据，程序退出。")

    def test_performance_monitoring_integration(self):
        """测试性能监控在集成场景下的工作"""
        from ruijie_query.monitoring.performance_monitor import get_monitor

        # 1. 获取监控器
        monitor = get_monitor()

        # 2. 重置之前的统计
        monitor.reset()

        # 3. 执行一些模拟操作
        monitor.start_timer("integration_test_operation")
        time.sleep(0.01)
        monitor.end_timer("integration_test_operation")

        monitor.start_timer("integration_test_operation")
        time.sleep(0.01)
        monitor.end_timer("integration_test_operation")

        monitor.start_timer("another_operation")
        time.sleep(0.01)
        monitor.end_timer("another_operation")

        # 4. 验证统计正确
        stats_summary = monitor.get_stats_summary()
        assert "integration_test_operation" in stats_summary

        stats1 = stats_summary["integration_test_operation"]
        assert stats1['count'] == 2
        assert stats1['total_time'] > 0

        assert "another_operation" in stats_summary
        stats2 = stats_summary["another_operation"]
        assert stats2['count'] == 1
        assert stats2['total_time'] > 0

    def test_save_interval_integration(self):
        """测试保存间隔在集成场景下的工作"""
        # 1. 创建包含大量数据的测试文件
        large_data = pd.DataFrame({
            'Serial Number': [f'SN{i:03d}' for i in range(25)],
            '查询状态': [None] * 25
        })
        large_data.to_excel(self.excel_file, sheet_name='Sheet1', index=False)

        # 2. 更新配置以使用较小的保存间隔
        updated_config = """[General]
excel_file_path = {excel_file}
sheet_name = Sheet1
sn_column_name = Serial Number
query_delay = 0.1
save_interval = 5
max_query_attempts = 1
max_captcha_retries = 1

[CaptchaSettings]
captcha_primary_solver = ddddocr
captcha_enable_ddddocr = True
captcha_enable_ai = False
ddddocr_max_attempts = 1

[AI_Settings]
retry_attempts = 1
retry_delay = 1
rate_limit_delay = 5
ai_test_timeout = 10

[ResultColumns]
查询状态 = 查询状态

[Logging]
log_level = INFO
log_to_console = False
""".format(excel_file=self.excel_file)

        with open(self.config_file, 'w') as f:
            f.write(updated_config)

        # 3. 创建配置管理器
        config_manager = ConfigManager(config_file=self.config_file)

        # 4. 模拟应用程序流程
        with patch('ruijie_query.core.data_manager.DataManager') as mock_data_manager, \
             patch('ruijie_query.captcha.captcha_solver.CaptchaSolver') as mock_captcha_solver, \
             patch('ruijie_query.browser.webdriver_manager.WebDriverManager') as mock_webdriver_manager, \
             patch('ruijie_query.browser.page_objects.ruijie_page.RuijieQueryPage') as mock_page_class:

            # 5. 模拟数据管理器
            mock_dm_instance = MagicMock()
            mock_dm_instance.load_data.return_value = large_data
            mock_dm_instance.get_unqueried_serial_numbers.return_value = [
                (i, f'SN{i:03d}') for i in range(25)
            ]
            mock_data_manager.return_value = mock_dm_instance

            # 6. 模拟其他组件
            mock_captcha_instance = MagicMock()
            mock_captcha_instance.test_channels_availability.return_value = []
            mock_captcha_solver.return_value = mock_captcha_instance

            mock_webdriver_instance = MagicMock()
            mock_driver = MagicMock()
            mock_webdriver_instance.initialize_driver.return_value = mock_driver
            mock_webdriver_manager.return_value = mock_webdriver_instance

            mock_page = MagicMock()
            mock_page.query_single_device.return_value = {'查询状态': '成功'}
            mock_page_class.return_value = mock_page

            # 7. 运行应用程序
            app = RuijieQueryApp(config_manager)
            app.logger = MagicMock()

            app.run()

            # 8. 验证保存被多次调用（因为保存间隔为5，有25个序列号）
            assert mock_dm_instance.save_data.call_count >= 4  # 至少4次保存（5个批次）

    def test_resume_functionality_integration(self):
        """测试断点续传功能的集成"""
        # 1. 创建包含部分查询结果的数据文件
        partial_data = pd.DataFrame({
            'Serial Number': ['SN001', 'SN002', 'SN003', 'SN004', 'SN005'],
            '查询状态': ['成功', '失败', None, '成功', None]
        })
        partial_data.to_excel(self.excel_file, sheet_name='Sheet1', index=False)

        # 2. 创建配置管理器
        config_manager = ConfigManager(config_file=self.config_file)

        # 3. 模拟应用程序流程
        with patch('ruijie_query.core.data_manager.DataManager') as mock_data_manager, \
             patch('ruijie_query.captcha.captcha_solver.CaptchaSolver') as mock_captcha_solver, \
             patch('ruijie_query.browser.webdriver_manager.WebDriverManager') as mock_webdriver_manager, \
             patch('ruijie_query.browser.page_objects.ruijie_page.RuijieQueryPage') as mock_page_class:

            # 4. 模拟数据管理器
            mock_dm_instance = MagicMock()
            mock_dm_instance.load_data.return_value = partial_data
            # 只返回未成功查询的序列号
            mock_dm_instance.get_unqueried_serial_numbers.return_value = [(2, 'SN003'), (4, 'SN005')]
            mock_data_manager.return_value = mock_dm_instance

            # 5. 模拟其他组件
            mock_captcha_instance = MagicMock()
            mock_captcha_instance.test_channels_availability.return_value = []
            mock_captcha_solver.return_value = mock_captcha_instance

            mock_webdriver_instance = MagicMock()
            mock_driver = MagicMock()
            mock_webdriver_instance.initialize_driver.return_value = mock_driver
            mock_webdriver_manager.return_value = mock_webdriver_instance

            mock_page = MagicMock()
            mock_page.query_single_device.return_value = {'查询状态': '成功'}
            mock_page_class.return_value = mock_page

            # 6. 运行应用程序
            app = RuijieQueryApp(config_manager)
            app.logger = MagicMock()

            app.run()

            # 7. 验证只处理未成功查询的序列号
            assert mock_page.query_single_device.call_count == 2  # 只有SN003和SN005

            # 验证正确的序列号被处理
            calls = mock_page.query_single_device.call_args_list
            serial_numbers = [call[0][0] for call in calls]
            assert 'SN003' in serial_numbers
            assert 'SN005' in serial_numbers
            assert 'SN001' not in serial_numbers  # 已成功，跳过
            assert 'SN002' not in serial_numbers  # 失败但不是None，跳过
            assert 'SN004' not in serial_numbers  # 已成功，跳过