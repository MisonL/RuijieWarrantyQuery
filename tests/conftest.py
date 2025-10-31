# -*- coding: utf-8 -*-
"""
Pytest配置文件 - 提供共享的fixture和工具函数
"""
import tempfile
import os
import configparser
import pytest


@pytest.fixture
def temp_config_file():
    """创建临时配置文件fixture"""
    def _create_config_file(content=None):
        """创建临时配置文件"""
        fd, path = tempfile.mkstemp(suffix='.ini')
        try:
            with os.fdopen(fd, 'w') as f:
                if content:
                    f.write(content)
                else:
                    # 创建基本配置文件
                    f.write("""[General]
excel_file_path = Serial-Number.xlsx
sheet_name = Sheet1
sn_column_name = Serial Number
query_delay = 2
save_interval = 10
max_query_attempts = 3
max_captcha_retries = 2

[CaptchaSettings]
captcha_primary_solver = ddddocr
captcha_enable_ddddocr = True
captcha_enable_ai = False
ddddocr_max_attempts = 3

[AI_Settings]
retry_attempts = 3
retry_delay = 5
rate_limit_delay = 30
ai_test_timeout = 120

[ResultColumns]
型号 = 型号
保修状态 = 保修状态
查询状态 = 查询状态

[Logging]
log_level = INFO
log_to_console = True
log_max_bytes = 1024KB
log_backup_count = 5
""")
        except:
            os.close(fd)
            raise
        return path

    return _create_config_file


@pytest.fixture
def complete_config_file(temp_config_file):
    """创建完整的配置文件"""
    return temp_config_file()


@pytest.fixture
def minimal_config_file(temp_config_file):
    """创建最小配置文件"""
    return temp_config_file("""[General]
excel_file_path = test.xlsx
sheet_name = Sheet1
sn_column_name = Serial Number

[AI_Settings]
retry_attempts = 3
retry_delay = 5

[ResultColumns]
查询状态 = 查询状态
""")


@pytest.fixture
def invalid_config_file(temp_config_file):
    """创建无效配置文件"""
    return temp_config_file("""[General]
excel_file_path = invalid.xlsx
sheet_name = Sheet1

[AI_Settings]
retry_attempts = invalid_number

[ResultColumns]
查询状态 = 查询状态
""")


@pytest.fixture
def mock_logger():
    """创建模拟logger"""
    import logging
    logger = logging.getLogger('test_logger')
    logger.setLevel(logging.DEBUG)
    return logger