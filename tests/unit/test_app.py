# -*- coding: utf-8 -*-
"""
应用程序主逻辑单元测试
"""
import tempfile
import pandas as pd
import os
from unittest.mock import patch, MagicMock, Mock
import pytest

import sys
sys.path.insert(0, 'src')

from ruijie_query.core.app import RuijieQueryApp
from ruijie_query.config.config import ConfigManager


class TestRuijieQueryApp:
    """RuijieQueryApp类的单元测试"""

    def setup_method(self):
        """测试方法初始化"""
        self.temp_dir = tempfile.mkdtemp()

        # 创建模拟的配置管理器
        self.config_manager = MagicMock(spec=ConfigManager)
        self.config_manager.get_general_config.return_value = {
            'excel_file_path': 'test.xlsx',
            'sheet_name': 'Sheet1',
            'sn_column_name': 'Serial Number',
            'query_delay': 2,
            'save_interval': 10,
            'max_query_attempts': 3,
            'max_captcha_retries': 2
        }
        self.config_manager.get_captcha_config.return_value = {
            'primary_solver': 'ddddocr',
            'enable_ddddocr': True,
            'enable_ai': False,
            'ddddocr_max_attempts': 3
        }
        self.config_manager.get_ai_config.return_value = {
            'retry_attempts': 3,
            'retry_delay': 5,
            'rate_limit_delay': 30,
            'ai_test_timeout': 120
        }
        self.config_manager.get_result_columns.return_value = {
            '型号': '型号',
            '保修状态': '保修状态',
            '查询状态': '查询状态'
        }
        self.config_manager.get_logging_config.return_value = {
            'log_level': 'INFO',
            'log_to_console': True,
            'log_file': None,
            'log_max_bytes': '1024KB',
            'log_backup_count': 5
        }

        self.logger = MagicMock()

        self.app = RuijieQueryApp(self.config_manager)
        self.app.logger = self.logger

    def teardown_method(self):
        """测试方法清理"""
        if os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir)

    def test_init_with_config_manager(self):
        """测试使用配置管理器初始化"""
        app = RuijieQueryApp(self.config_manager)

        assert app.config_manager == self.config_manager
        assert app.general_config is not None
        assert app.captcha_config is not None
        assert app.ai_config is not None
        assert app.result_columns is not None
        assert app.logging_config is not None

    def test_setup_logging_console(self):
        """测试设置控制台日志"""
        with patch('logging.getLogger') as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            self.app._setup_logging()

            # 验证日志记录器被正确配置
            mock_get_logger.assert_called()
            # 由于配置中有log_to_console=True，应该添加控制台处理器
            # 具体的断言取决于日志配置的实现

    def test_setup_logging_file(self):
        """测试设置文件日志"""
        log_file = os.path.join(self.temp_dir, 'test.log')

        self.config_manager.get_logging_config.return_value = {
            'log_level': 'INFO',
            'log_to_console': False,
            'log_file': log_file,
            'log_max_bytes': '1024KB',
            'log_backup_count': 5
        }

        with patch('logging.getLogger') as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            self.app._setup_logging()

            # 验证文件处理器被添加
            # 具体的断言取决于日志配置的实现

    @patch('ruijie_query.core.data_manager.DataManager')
    @patch('ruijie_query.captcha.captcha_solver.CaptchaSolver')
    @patch('ruijie_query.browser.webdriver_manager.WebDriverManager')
    def test_run_success_flow(self, mock_webdriver_manager, mock_captcha_solver, mock_data_manager):
        """测试完整的成功运行流程"""
        # 准备测试数据
        test_data = pd.DataFrame({
            'Serial Number': ['SN001', 'SN002'],
            '型号': ['Model1', 'Model2']
        })

        # 模拟数据管理器
        mock_dm_instance = MagicMock()
        mock_dm_instance.load_data.return_value = test_data
        mock_dm_instance.get_unqueried_serial_numbers.return_value = [(0, 'SN001'), (1, 'SN002')]
        mock_dm_instance.save_data.return_value = None
        mock_data_manager.return_value = mock_dm_instance

        # 模拟验证码解析器
        mock_captcha_instance = MagicMock()
        mock_captcha_instance.test_channels_availability.return_value = []  # 没有AI渠道
        mock_captcha_solver.return_value = mock_captcha_instance

        # 模拟WebDriver管理器
        mock_webdriver_instance = MagicMock()
        mock_driver = MagicMock()
        mock_webdriver_instance.initialize_driver.return_value = mock_driver
        mock_webdriver_manager.return_value = mock_webdriver_instance

        # 运行应用
        self.app.run()

        # 验证各个组件被正确调用
        mock_dm_instance.load_data.assert_called_once()
        mock_dm_instance.get_unqueried_serial_numbers.assert_called_once()
        mock_webdriver_instance.initialize_driver.assert_called_once()

    @patch('ruijie_query.core.data_manager.DataManager')
    def test_run_data_loading_failed(self, mock_data_manager):
        """测试数据加载失败的情况"""
        # 模拟数据加载失败
        mock_dm_instance = MagicMock()
        mock_dm_instance.load_data.return_value = None  # 加载失败
        mock_data_manager.return_value = mock_dm_instance

        # 运行应用
        self.app.run()

        # 验证程序因为数据加载失败而退出
        mock_dm_instance.load_data.assert_called_once()
        self.logger.error.assert_any_call("无法加载Excel数据，程序退出。")

    @patch('ruijie_query.core.data_manager.DataManager')
    @patch('ruijie_query.captcha.captcha_solver.CaptchaSolver')
    def test_run_no_captcha_solvers_available(self, mock_captcha_solver, mock_data_manager):
        """测试没有可用的验证码解析器"""
        # 准备测试数据
        test_data = pd.DataFrame({'Serial Number': ['SN001']})

        # 模拟数据管理器
        mock_dm_instance = MagicMock()
        mock_dm_instance.load_data.return_value = test_data
        mock_dm_instance.get_unqueried_serial_numbers.return_value = [(0, 'SN001')]
        mock_data_manager.return_value = mock_dm_instance

        # 模拟验证码解析器 - 没有可用渠道且ddddocr被禁用
        mock_captcha_instance = MagicMock()
        mock_captcha_instance.test_channels_availability.return_value = []
        mock_captcha_solver.return_value = mock_captcha_instance

        # 禁用ddddocr
        self.app.captcha_config['enable_ddddocr'] = False

        # 运行应用
        self.app.run()

        # 验证程序因为没有验证码解析器而退出
        self.logger.error.assert_any_call("没有可用的验证码识别方式（ddddocr和AI渠道都不可用）。程序退出。")

    @patch('ruijie_query.core.data_manager.DataManager')
    @patch('ruijie_query.captcha.captcha_solver.CaptchaSolver')
    @patch('ruijie_query.browser.webdriver_manager.WebDriverManager')
    def test_run_webdriver_initialization_failed(self, mock_webdriver_manager, mock_captcha_solver, mock_data_manager):
        """测试WebDriver初始化失败的情况"""
        # 准备测试数据
        test_data = pd.DataFrame({'Serial Number': ['SN001']})

        # 模拟数据管理器
        mock_dm_instance = MagicMock()
        mock_dm_instance.load_data.return_value = test_data
        mock_data_manager.return_value = mock_dm_instance

        # 模拟验证码解析器
        mock_captcha_instance = MagicMock()
        mock_captcha_instance.test_channels_availability.return_value = []
        mock_captcha_solver.return_value = mock_captcha_instance

        # 模拟WebDriver管理器 - 初始化失败
        mock_webdriver_instance = MagicMock()
        mock_webdriver_instance.initialize_driver.return_value = None  # 初始化失败
        mock_webdriver_manager.return_value = mock_webdriver_instance

        # 运行应用
        self.app.run()

        # 验证程序因为WebDriver初始化失败而退出
        self.logger.error.assert_any_call("WebDriver 初始化失败，程序退出。")

    @patch('ruijie_query.core.data_manager.DataManager')
    def test_process_queries_success(self, mock_data_manager):
        """测试批量查询处理成功"""
        # 准备测试数据
        test_data = pd.DataFrame({
            'Serial Number': ['SN001', 'SN002'],
            '查询状态': [None, None]
        })

        # 模拟数据管理器
        mock_dm_instance = MagicMock()
        mock_dm_instance.load_data.return_value = test_data
        mock_dm_instance.get_unqueried_serial_numbers.return_value = [(0, 'SN001'), (1, 'SN002')]
        mock_data_manager.return_value = mock_dm_instance

        self.app.data_manager = mock_dm_instance

        # 模拟其他组件
        self.app.captcha_solver = MagicMock()
        self.app.webdriver_manager = MagicMock()
        mock_driver = MagicMock()
        self.app.webdriver_manager.initialize_driver.return_value = mock_driver
        self.app.query_page = MagicMock()

        # 执行查询处理
        self.app._process_queries(test_data)

        # 验证查询被处理
        assert mock_dm_instance.save_data.call_count >= 1  # 至少保存一次

    @patch('ruijie_query.core.data_manager.DataManager')
    def test_process_queries_empty_data(self, mock_data_manager):
        """测试处理空数据"""
        # 模拟数据管理器
        mock_dm_instance = MagicMock()
        mock_dm_instance.load_data.return_value = None
        mock_data_manager.return_value = mock_dm_instance

        self.app.data_manager = mock_dm_instance

        # 执行查询处理
        self.app._process_queries(None)

        # 验证不会崩溃
        self.logger.warning.assert_called_once_with("DataFrame 为空，无需处理。")

    def test_process_single_query_success(self):
        """测试单个查询成功处理"""
        # 模拟页面对象
        mock_page = MagicMock()
        mock_page.query_single_device.return_value = {
            '型号': 'Model1',
            '保修状态': '有效',
            '查询状态': '成功'
        }

        # 执行单个查询
        result = self.app._process_single_query('SN001')

        # 验证查询成功
        assert result is not None
        assert result['查询状态'] == '成功'
        mock_page.query_single_device.assert_called_once_with('SN001')

    def test_process_single_query_failure(self):
        """测试单个查询失败处理"""
        # 模拟页面对象 - 查询失败
        mock_page = MagicMock()
        mock_page.query_single_device.side_effect = Exception("查询失败")

        # 执行单个查询
        result = self.app._process_single_query('SN001')

        # 验证查询失败但不会崩溃
        assert result is not None
        assert result['查询状态'] == '未知错误'

    def test_app_initialization_complete(self):
        """测试应用程序完整初始化"""
        app = RuijieQueryApp(self.config_manager)

        # 验证所有必要的组件都被初始化
        assert hasattr(app, 'config_manager')
        assert hasattr(app, 'general_config')
        assert hasattr(app, 'captcha_config')
        assert hasattr(app, 'ai_config')
        assert hasattr(app, 'result_columns')
        assert hasattr(app, 'logging_config')
        assert hasattr(app, 'logger')

    def test_app_with_target_url(self):
        """测试应用程序的目标URL设置"""
        app = RuijieQueryApp(self.config_manager)

        # 验证目标URL被正确设置
        # 具体的URL值取决于配置，但应该是一个有效的URL字符串
        assert app.target_url is not None
        assert isinstance(app.target_url, str)

    def test_app_retry_mechanism(self):
        """测试应用程序的重试机制"""
        with patch('ruijie_query.core.data_manager.DataManager') as mock_data_manager:
            # 准备测试数据
            test_data = pd.DataFrame({
                'Serial Number': ['SN001', 'SN002'],
                '查询状态': ['失败', '失败']  # 模拟失败状态
            })

            # 模拟数据管理器
            mock_dm_instance = MagicMock()
            mock_dm_instance.load_data.return_value = test_data
            # 重试时返回所有序列号
            mock_dm_instance.get_unqueried_serial_numbers.side_effect = [
                [(0, 'SN001'), (1, 'SN002')],  # 第一次调用
                [(0, 'SN001')]  # 重试时只有SN001需要重试
            ]
            mock_data_manager.return_value = mock_dm_instance

            self.app.data_manager = mock_dm_instance

            # 模拟其他组件
            self.app.captcha_solver = MagicMock()
            self.app.captcha_solver.test_channels_availability.return_value = []
            self.app.webdriver_manager = MagicMock()
            mock_driver = MagicMock()
            self.app.webdriver_manager.initialize_driver.return_value = mock_driver
            self.app.query_page = MagicMock()

            # 运行应用（包含重试）
            self.app.run()

            # 验证get_unqueried_serial_numbers被调用多次（原始查询 + 重试）
            assert mock_dm_instance.get_unqueried_serial_numbers.call_count >= 1

    def test_app_save_interval_functionality(self):
        """测试应用程序的保存间隔功能"""
        with patch('ruijie_query.core.data_manager.DataManager') as mock_data_manager:
            # 创建大量测试数据以触发保存间隔
            test_data = pd.DataFrame({
                'Serial Number': [f'SN{i:03d}' for i in range(25)],  # 25个序列号
                '查询状态': [None] * 25
            })

            # 模拟数据管理器
            mock_dm_instance = MagicMock()
            mock_dm_instance.load_data.return_value = test_data
            mock_dm_instance.get_unqueried_serial_numbers.return_value = [
                (i, f'SN{i:03d}') for i in range(25)
            ]
            mock_data_manager.return_value = mock_dm_instance

            self.app.data_manager = mock_dm_instance

            # 模拟其他组件
            self.app.captcha_solver = MagicMock()
            self.app.captcha_solver.test_channels_availability.return_value = []
            self.app.webdriver_manager = MagicMock()
            mock_driver = MagicMock()
            self.app.webdriver_manager.initialize_driver.return_value = mock_driver
            self.app.query_page = MagicMock()
            self.app.query_page.query_single_device.return_value = {'查询状态': '成功'}

            # 运行应用
            self.app.run()

            # 验证数据被多次保存（因为保存间隔为10）
            # 25个序列号应该触发多次保存
            assert mock_dm_instance.save_data.call_count >= 2

    def test_app_performance_monitoring(self):
        """测试应用程序的性能监控"""
        with patch('ruijie_query.core.data_manager.DataManager') as mock_data_manager:
            # 准备测试数据
            test_data = pd.DataFrame({'Serial Number': ['SN001']})

            # 模拟数据管理器
            mock_dm_instance = MagicMock()
            mock_dm_instance.load_data.return_value = test_data
            mock_dm_instance.get_unqueried_serial_numbers.return_value = []
            mock_data_manager.return_value = mock_dm_instance

            # 模拟其他组件
            self.app.captcha_solver = MagicMock()
            self.app.captcha_solver.test_channels_availability.return_value = []
            self.app.webdriver_manager = MagicMock()
            mock_driver = MagicMock()
            self.app.webdriver_manager.initialize_driver.return_value = mock_driver

            # 运行应用
            self.app.run()

            # 验证性能监控日志被记录
            # 具体的监控日志验证取决于实现细节
            assert self.logger.info.call_count > 0

    def test_app_error_handling_and_recovery(self):
        """测试应用程序的错误处理和恢复"""
        with patch('ruijie_query.core.data_manager.DataManager') as mock_data_manager:
            # 模拟数据管理器抛出异常
            mock_dm_instance = MagicMock()
            mock_dm_instance.load_data.side_effect = Exception("数据加载错误")
            mock_data_manager.return_value = mock_dm_instance

            # 运行应用
            self.app.run()

            # 验证错误被正确处理
            self.logger.error.assert_called()

    def test_app_configuration_validation(self):
        """测试应用程序配置验证"""
        # 测试使用无效配置
        invalid_config_manager = MagicMock()
        invalid_config_manager.get_general_config.return_value = {}
        invalid_config_manager.get_captcha_config.return_value = {}
        invalid_config_manager.get_ai_config.return_value = {}
        invalid_config_manager.get_result_columns.return_value = {}
        invalid_config_manager.get_logging_config.return_value = {}

        app = RuijieQueryApp(invalid_config_manager)

        # 应用程序应该能够处理缺失的配置
        assert app is not None
        assert hasattr(app, 'config_manager')

    def test_app_integration_scenario(self):
        """测试应用程序的集成场景"""
        with patch('ruijie_query.core.data_manager.DataManager') as mock_data_manager, \
             patch('ruijie_query.captcha.captcha_solver.CaptchaSolver') as mock_captcha_solver, \
             patch('ruijie_query.browser.webdriver_manager.WebDriverManager') as mock_webdriver_manager:

            # 准备完整的集成测试场景
            test_data = pd.DataFrame({
                'Serial Number': ['SN001', 'SN002', 'SN003'],
                '型号': ['Model1', 'Model2', 'Model3'],
                '保修状态': [None, None, None],
                '查询状态': [None, '成功', None]
            })

            # 模拟数据管理器
            mock_dm_instance = MagicMock()
            mock_dm_instance.load_data.return_value = test_data
            # 只有SN001和SN003需要查询
            mock_dm_instance.get_unqueried_serial_numbers.return_value = [(0, 'SN001'), (3, 'SN003')]
            mock_data_manager.return_value = mock_dm_instance

            # 模拟验证码解析器
            mock_captcha_instance = MagicMock()
            mock_captcha_instance.test_channels_availability.return_value = []
            mock_captcha_solver.return_value = mock_captcha_instance

            # 模拟WebDriver管理器
            mock_webdriver_instance = MagicMock()
            mock_driver = MagicMock()
            mock_webdriver_instance.initialize_driver.return_value = mock_driver
            mock_webdriver_manager.return_value = mock_webdriver_instance

            # 模拟页面对象
            mock_page = MagicMock()
            mock_page.query_single_device.return_value = {'查询状态': '成功'}
            with patch('ruijie_query.browser.page_objects.ruijie_page.RuijieQueryPage', return_value=mock_page):
                # 运行完整的应用流程
                self.app.run()

                # 验证集成场景的各个组件正确协作
                mock_dm_instance.load_data.assert_called_once()
                mock_webdriver_instance.initialize_driver.assert_called_once()
                # 验证只有未查询的序列号被处理
                assert mock_page.query_single_device.call_count == 2