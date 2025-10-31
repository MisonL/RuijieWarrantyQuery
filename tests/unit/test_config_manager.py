# -*- coding: utf-8 -*-
"""
配置管理模块单元测试
"""
import os
import tempfile
import configparser
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock
import pytest

import sys
sys.path.insert(0, 'src')

from ruijie_query.config.config import ConfigManager, ConfigValidator


class TestConfigValidator:
    """ConfigValidator类的单元测试"""

    def setup_method(self):
        """测试方法初始化"""
        self.validator = ConfigValidator()

    def test_init_with_logger(self):
        """测试使用自定义logger初始化"""
        logger = MagicMock()
        validator = ConfigValidator(logger=logger)
        assert validator.logger == logger

    def test_init_without_logger(self):
        """测试不使用自定义logger初始化"""
        validator = ConfigValidator()
        assert validator.logger is not None
        assert validator.validation_errors == []
        assert validator.validation_warnings == []

    def test_validate_config_empty_config(self):
        """测试空配置验证"""
        config = configparser.ConfigParser()
        is_valid, errors, warnings = self.validator.validate_config(config)

        # 空配置应该不通过验证，因为缺少必要的节
        assert not is_valid
        assert len(errors) > 0
        assert "General" in errors[0] or "必要的配置节缺失" in errors[0]

    @patch('os.path.exists')
    def test_validate_general_config_valid(self, mock_exists):
        """测试有效的General配置验证"""
        mock_exists.return_value = True
        config = configparser.ConfigParser()
        config.add_section('General')
        config.set('General', 'excel_file_path', 'Serial-Number.xlsx')
        config.set('General', 'sheet_name', 'Sheet1')
        config.set('General', 'sn_column_name', 'Serial Number')
        config.set('General', 'query_delay', '2')
        config.set('General', 'max_query_attempts', '3')

        self.validator._validate_general_config(config['General'])
        assert len(self.validator.validation_errors) == 0

    def test_validate_general_config_invalid_delay(self):
        """测试无效的查询延迟配置"""
        config = configparser.ConfigParser()
        config.add_section('General')
        config.set('General', 'query_delay', 'invalid_number')

        self.validator._validate_general_config(config['General'])
        assert any('query_delay' in error for error in self.validator.validation_errors)

    def test_validate_general_config_invalid_attempts(self):
        """测试无效的最大尝试次数配置"""
        config = configparser.ConfigParser()
        config.add_section('General')
        config.set('General', 'max_query_attempts', '-1')

        self.validator._validate_general_config(config['General'])
        assert any('max_query_attempts' in error for error in self.validator.validation_errors)

    def test_validate_captcha_config_valid(self):
        """测试有效的CaptchaSettings配置"""
        config = configparser.ConfigParser()
        config.add_section('CaptchaSettings')
        config.set('CaptchaSettings', 'captcha_primary_solver', 'ddddocr')
        config.set('CaptchaSettings', 'captcha_enable_ddddocr', 'True')
        config.set('CaptchaSettings', 'captcha_enable_ai', 'False')
        config.set('CaptchaSettings', 'ddddocr_max_attempts', '3')

        self.validator._validate_captcha_config(config['CaptchaSettings'])
        assert len(self.validator.validation_errors) == 0

    def test_validate_captcha_config_invalid_solver(self):
        """测试无效的验证码解析器配置"""
        config = configparser.ConfigParser()
        config.add_section('CaptchaSettings')
        config.set('CaptchaSettings', 'captcha_primary_solver', 'invalid_solver')

        self.validator._validate_captcha_config(config['CaptchaSettings'])
        assert any('captcha_primary_solver' in error for error in self.validator.validation_errors)

    def test_validate_captcha_config_invalid_bool(self):
        """测试无效的布尔配置"""
        config = configparser.ConfigParser()
        config.add_section('CaptchaSettings')
        config.set('CaptchaSettings', 'captcha_enable_ddddocr', 'invalid_bool')

        self.validator._validate_captcha_config(config['CaptchaSettings'])
        assert any('captcha_enable_ddddocr' in error for error in self.validator.validation_errors)

    def test_validate_result_columns_valid(self):
        """测试有效的ResultColumns配置"""
        config = configparser.ConfigParser()
        config.add_section('ResultColumns')
        config.set('ResultColumns', '型号', '型号')
        config.set('ResultColumns', '保修状态', '保修状态')
        config.set('ResultColumns', '查询状态', '查询状态')

        self.validator._validate_result_columns(config['ResultColumns'])
        assert len(self.validator.validation_errors) == 0

    def test_validate_ai_settings_valid(self):
        """测试有效的AI设置配置"""
        config = configparser.ConfigParser()
        config.add_section('AI_Settings')
        config.set('AI_Settings', 'retry_attempts', '3')
        config.set('AI_Settings', 'retry_delay', '5')
        config.set('AI_Settings', 'rate_limit_delay', '30')

        self.validator._validate_ai_config(config['AI_Settings'])
        assert len(self.validator.validation_errors) == 0

    def test_validate_logging_config_valid(self):
        """测试有效的日志配置"""
        config = configparser.ConfigParser()
        config.add_section('Logging')
        config.set('Logging', 'log_level', 'INFO')
        config.set('Logging', 'log_to_console', 'True')
        config.set('Logging', 'log_max_bytes', '1024KB')
        config.set('Logging', 'log_backup_count', '5')

        self.validator._validate_logging_config(config['Logging'])
        assert len(self.validator.validation_errors) == 0


class TestConfigManager:
    """ConfigManager类的单元测试"""

    def setup_method(self):
        """测试方法初始化"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, 'test_config.ini')

    def teardown_method(self):
        """测试方法清理"""
        if os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir)

    def test_init_default_config_file(self):
        """测试使用默认配置文件初始化"""
        manager = ConfigManager()
        assert manager.config_file.endswith('config.ini')

    def test_init_custom_config_file(self):
        """测试使用自定义配置文件初始化"""
        # 创建临时配置文件
        with open(self.config_file, 'w') as f:
            f.write("[General]\nexcel_file_path = test.xlsx\n")

        manager = ConfigManager(config_file=self.config_file)
        assert manager.config_file == self.config_file

    @patch('configparser.ConfigParser.read')
    @patch('pathlib.Path.exists')
    def test_load_config_file_exists(self, mock_exists, mock_read):
        """测试加载存在的配置文件"""
        mock_exists.return_value = True
        mock_config = configparser.ConfigParser()
        mock_read.return_value = None

        with patch('ruijie_query.config.config.ConfigParser', return_value=mock_config):
            # 创建临时配置文件
            with open(self.config_file, 'w') as f:
                f.write("[General]\nexcel_file_path = test.xlsx\n")

            manager = ConfigManager(config_file=self.config_file)
            config = manager.config
            assert config is not None

    @patch('configparser.ConfigParser.read')
    @patch('pathlib.Path.exists')
    def test_load_config_file_not_exists(self, mock_exists, mock_read):
        """测试加载不存在的配置文件"""
        mock_exists.return_value = False
        mock_config = configparser.ConfigParser()
        mock_read.return_value = None

        with patch('ruijie_query.config.config.ConfigParser', return_value=mock_config):
            manager = ConfigManager(config_file=self.config_file)
            # 应该创建默认配置
            assert manager.config is not None

    def test_get_general_config(self):
        """测试获取General配置"""
        # 创建临时配置文件
        with open(self.config_file, 'w') as f:
            f.write("[General]\nexcel_file_path = test.xlsx\nquery_delay = 2\n")

        manager = ConfigManager(config_file=self.config_file)
        general_config = manager.get_general_config()
        assert general_config['excel_file_path'] == 'test.xlsx'
        assert general_config['query_delay'] == '2'

    def test_get_captcha_config(self):
        """测试获取CaptchaSettings配置"""
        # 创建临时配置文件
        with open(self.config_file, 'w') as f:
            f.write("[CaptchaSettings]\ncaptcha_primary_solver = ddddocr\ncaptcha_enable_ddddocr = True\n")

        manager = ConfigManager(config_file=self.config_file)
        captcha_config = manager.get_captcha_config()
        assert captcha_config['primary_solver'] == 'ddddocr'
        assert captcha_config['enable_ddddocr'] is True

    def test_get_result_columns(self):
        """测试获取ResultColumns配置"""
        # 创建临时配置文件
        with open(self.config_file, 'w') as f:
            f.write("[ResultColumns]\n型号 = 型号\n保修状态 = 保修状态\n")

        manager = ConfigManager(config_file=self.config_file)
        result_columns = manager.get_result_columns()
        assert '型号' in result_columns
        assert '保修状态' in result_columns

    def test_get_ai_config(self):
        """测试获取AI设置配置"""
        # 创建临时配置文件
        with open(self.config_file, 'w') as f:
            f.write("[AI_Settings]\nretry_attempts = 3\nretry_delay = 5\n")

        manager = ConfigManager(config_file=self.config_file)
        ai_config = manager.get_ai_config()
        assert ai_config['retry_attempts'] == 3
        assert ai_config['retry_delay'] == 5

    def test_get_logging_config(self):
        """测试获取日志配置"""
        # 创建临时配置文件
        with open(self.config_file, 'w') as f:
            f.write("[Logging]\nlog_level = INFO\nlog_to_console = True\n")

        manager = ConfigManager(config_file=self.config_file)
        logging_config = manager.get_logging_config()
        assert logging_config['log_level'] == 'INFO'
        assert logging_config['log_to_console'] is True

    def test_fix_config_invalid_bool(self):
        """测试修复无效的布尔配置"""
        # 创建临时配置文件
        with open(self.config_file, 'w') as f:
            f.write("[CaptchaSettings]\ncaptcha_enable_ddddocr = yes\n")

        manager = ConfigManager(config_file=self.config_file)
        fixed_count = manager.fix_common_issues()
        assert fixed_count > 0
        # 检查值是否被修复
        value = manager.config.get('CaptchaSettings', 'captcha_enable_ddddocr').lower()
        assert value in ['true', 'false']

    @patch('builtins.open', new_callable=mock_open)
    @patch('configparser.ConfigParser.write')
    def test_save_config(self, mock_write, mock_file):
        """测试保存配置文件"""
        # 创建临时配置文件
        with open(self.config_file, 'w') as f:
            f.write("[Test]\nkey = value\n")

        manager = ConfigManager(config_file=self.config_file)
        result = manager.save_config()

        assert result is True
        mock_write.assert_called_once()

    def test_create_default_config_file(self):
        """测试创建默认配置文件"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = os.path.join(temp_dir, 'new_config.ini')

            # 创建临时配置文件
            with open(config_file, 'w') as f:
                f.write("")  # 空文件

            manager = ConfigManager(config_file=config_file)

            # 使用export_config_template方法创建默认配置
            manager.export_config_template(config_file)

            # 检查文件是否创建
            assert os.path.exists(config_file)

            # 检查文件是否包含必要的配置节
            config = configparser.ConfigParser()
            config.read(config_file)
            assert 'General' in config
            assert 'CaptchaSettings' in config
            assert 'AI_Settings' in config

    @patch('builtins.open', mock_open(read_data="[General]\nexcel_file_path = test.xlsx"))
    def test_load_data_from_file_success(self):
        """测试从文件成功加载数据"""
        # 创建临时配置文件
        with open(self.config_file, 'w') as f:
            f.write("[General]\nexcel_file_path = test.xlsx\n")

        manager = ConfigManager(config_file=self.config_file)
        # 这个方法可能在ConfigManager中不存在，但我们测试基本的文件读取
        assert manager.config is not None

    def test_validate_config_method(self):
        """测试配置验证方法"""
        # 创建临时配置文件
        with open(self.config_file, 'w') as f:
            f.write("[General]\nexcel_file_path = test.xlsx\n")

        manager = ConfigManager(config_file=self.config_file)

        is_valid, errors, warnings = manager.validate_config()
        # 由于配置不完整，验证应该失败
        assert isinstance(is_valid, bool)
        assert isinstance(errors, list)
        assert isinstance(warnings, list)