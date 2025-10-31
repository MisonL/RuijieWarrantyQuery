# -*- coding: utf-8 -*-
"""
WebDriver管理模块单元测试
"""
import os
import tempfile
import platform
from unittest.mock import patch, MagicMock, Mock
from pathlib import Path
import pytest

import sys
sys.path.insert(0, 'src')

from ruijie_query.browser.webdriver_manager import WebDriverManager, EnhancedChromeDriverManager


class TestEnhancedChromeDriverManager:
    """EnhancedChromeDriverManager类的单元测试"""

    def setup_method(self):
        """测试方法初始化"""
        self.logger = MagicMock()
        self.manager = EnhancedChromeDriverManager(logger=self.logger)
        # 清空缓存以确保测试的一致性
        self.manager.version_cache.clear()
        self.manager.download_stats.clear()
        self.manager.cache.clear()

    def test_init(self):
        """测试初始化"""
        assert self.manager.logger == self.logger
        assert self.manager.cache == {}
        assert self.manager.download_stats == {}

    def test_get_chrome_version_success(self):
        """测试成功获取Chrome版本"""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.stdout = "Google Chrome 119.0.6045.159"

            version = self.manager.get_chrome_version()

            assert version == "119.0.6045.159"

    def test_get_chrome_version_no_chrome(self):
        """测试未安装Chrome的情况"""
        with patch('subprocess.run', side_effect=FileNotFoundError("Chrome not found")):
            version = self.manager.get_chrome_version()

            assert version is None

    def test_get_compatible_chromedriver_version(self):
        """测试获取兼容的ChromeDriver版本"""
        with patch.object(self.manager, 'get_chrome_version') as mock_version:
            mock_version.return_value = "119.0.6045.159"

            version = self.manager.get_compatible_chromedriver_version()

            assert version is not None
            assert "119" in version

    def test_get_compatible_chromedriver_version_unknown_chrome(self):
        """测试未知Chrome版本的兼容版本获取"""
        with patch.object(self.manager, 'get_chrome_version') as mock_version:
            mock_version.return_value = None

            version = self.manager.get_compatible_chromedriver_version()

            assert version is not None
            assert version == "latest"

    def test_extract_version_from_path(self):
        """测试从路径提取版本信息"""
        driver_path = "/path/to/chromedriver_119.0.6045.159.exe"

        version = self.manager._extract_version_from_path(driver_path)

        assert version == "119.0.6045.159"

    def test_extract_version_from_path_no_version(self):
        """测试从无版本信息的路径提取"""
        driver_path = "/path/to/chromedriver"

        version = self.manager._extract_version_from_path(driver_path)

        assert version is None

    def test_calculate_file_hash(self):
        """测试计算文件哈希"""
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            temp_file.write("test content")
            temp_file_path = temp_file.name

        try:
            hash_value = self.manager._calculate_file_hash(Path(temp_file_path))

            assert hash_value is not None
            assert len(hash_value) == 64  # SHA256 哈希长度
        finally:
            os.unlink(temp_file_path)

    def test_cleanup_cache(self):
        """测试清理缓存"""
        self.manager.cache = {"test_key": "test_value"}
        self.manager.download_stats = {"test_stat": 1}

        self.manager.cleanup_cache()

        assert self.manager.cache == {}
        assert self.manager.download_stats == {}

    def test_get_download_stats(self):
        """测试获取下载统计"""
        self.manager.download_stats = {
            "total_downloads": 10,
            "successful_downloads": 8,
            "failed_downloads": 2
        }

        stats = self.manager.get_download_stats()

        assert stats == self.manager.download_stats


class TestWebDriverManager:
    """WebDriverManager类的单元测试"""

    def setup_method(self):
        """测试方法初始化"""
        self.logger = MagicMock()
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """测试方法清理"""
        if os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir)

    def test_init_with_custom_path(self):
        """测试使用自定义路径初始化"""
        custom_path = "/custom/chromedriver"
        manager = WebDriverManager(chrome_driver_path=custom_path, logger=self.logger)

        assert manager.chrome_driver_path == custom_path
        assert manager.logger == self.logger
        assert manager.enhanced_driver_manager is not None

    def test_init_without_custom_path(self):
        """测试不使用自定义路径初始化"""
        manager = WebDriverManager(logger=self.logger)

        assert manager.chrome_driver_path is None
        assert manager.logger == self.logger
        assert manager.enhanced_driver_manager is not None

    def test_get_platform_specific_driver_path_darwin(self):
        """测试macOS平台的驱动路径获取"""
        manager = WebDriverManager(logger=self.logger)

        driver_dir, driver_path = manager._get_platform_specific_driver_path()

        assert driver_dir is not None
        assert driver_path is not None
        assert "macOS" in driver_dir
        assert "chromedriver" in driver_path

    @patch('platform.system')
    def test_get_platform_specific_driver_path_unsupported(self, mock_platform):
        """测试不支持的操作系统的驱动路径获取"""
        mock_platform.return_value = "Unknown OS"

        manager = WebDriverManager(logger=self.logger)

        driver_dir, driver_path = manager._get_platform_specific_driver_path()

        assert driver_dir is None
        assert driver_path is None
        self.logger.warning.assert_called_once()

    def test_find_project_driver_exists(self):
        """测试查找存在的项目内驱动"""
        # 创建模拟的驱动文件
        os.makedirs(os.path.join(self.temp_dir, "drivers", "test_os", "test_arch"), exist_ok=True)
        driver_path = os.path.join(self.temp_dir, "drivers", "test_os", "test_arch", "chromedriver")
        with open(driver_path, 'w') as f:
            f.write("fake driver")

        manager = WebDriverManager(logger=self.logger)
        manager.project_drivers_path = os.path.join(self.temp_dir, "drivers")

        with patch.object(manager, '_get_platform_specific_driver_path') as mock_path:
            mock_path.return_value = (os.path.join(self.temp_dir, "drivers", "test_os", "test_arch"), driver_path)

            result = manager._find_project_driver()

            assert result == driver_path

    def test_find_project_driver_not_exists(self):
        """测试查找不存在的项目内驱动"""
        manager = WebDriverManager(logger=self.logger)
        manager.project_drivers_path = "/non/existent/path"

        result = manager._find_project_driver()

        assert result is None

    def test_find_offline_driver_exists(self):
        """测试查找存在的离线驱动"""
        # 创建离线驱动目录结构
        offline_dir = os.path.join(self.temp_dir, "offline_drivers")
        os.makedirs(offline_dir, exist_ok=True)

        manager = WebDriverManager(logger=self.logger)

        with patch.object(manager.enhanced_driver_manager, 'get_offline_driver_path') as mock_offline:
            mock_offline.return_value = os.path.join(offline_dir, "chromedriver")

            result = manager._find_offline_driver()

            assert result == os.path.join(offline_dir, "chromedriver")

    def test_find_offline_driver_not_exists(self):
        """测试查找不存在的离线驱动"""
        manager = WebDriverManager(logger=self.logger)

        with patch.object(manager.enhanced_driver_manager, 'get_offline_driver_path') as mock_offline:
            mock_offline.return_value = None

            result = manager._find_offline_driver()

            assert result is None

    @patch('selenium.webdriver.chrome.options.Options')
    @patch('selenium.webdriver.Chrome')
    def test_initialize_driver_config_specified_success(self, mock_chrome, mock_options):
        """测试使用配置指定的驱动成功初始化"""
        # 创建模拟的驱动文件
        driver_path = os.path.join(self.temp_dir, "chromedriver")
        with open(driver_path, 'w') as f:
            f.write("fake driver")

        manager = WebDriverManager(chrome_driver_path=driver_path, logger=self.logger)
        mock_driver = MagicMock()
        mock_chrome.return_value = mock_driver

        result = manager.initialize_driver()

        assert result == mock_driver
        mock_chrome.assert_called_once()
        self.logger.info.assert_any_call(f"使用配置指定的 ChromeDriver: {driver_path}")

    @patch('selenium.webdriver.Chrome')
    def test_initialize_driver_project_driver_success(self, mock_chrome):
        """测试使用项目内驱动成功初始化"""
        # 创建模拟的驱动文件
        driver_dir = os.path.join(self.temp_dir, "drivers", "test_os", "test_arch")
        os.makedirs(driver_dir, exist_ok=True)
        driver_path = os.path.join(driver_dir, "chromedriver")
        with open(driver_path, 'w') as f:
            f.write("fake driver")

        manager = WebDriverManager(logger=self.logger)
        manager.project_drivers_path = os.path.join(self.temp_dir, "drivers")

        mock_driver = MagicMock()
        mock_chrome.return_value = mock_driver

        result = manager.initialize_driver()

        assert result == mock_driver
        mock_chrome.assert_called_once()

    @patch('selenium.webdriver.Chrome')
    @patch('pathlib.Path.exists')
    def test_initialize_driver_enhanced_download_success(self, mock_exists, mock_chrome):
        """测试增强下载驱动成功初始化"""
        # 创建模拟的驱动文件
        driver_path = os.path.join(self.temp_dir, "chromedriver")
        with open(driver_path, 'w') as f:
            f.write("fake driver")

        manager = WebDriverManager(logger=self.logger)

        # 模拟所有查找方法都失败
        with patch.object(manager, '_find_project_driver', return_value=None), \
             patch.object(manager, '_find_offline_driver', return_value=None), \
             patch.object(manager, '_enhanced_download_driver', return_value=(driver_path, "enhanced_download")):

            mock_driver = MagicMock()
            mock_chrome.return_value = mock_driver

            result = manager.initialize_driver()

            assert result == mock_driver
            mock_chrome.assert_called_once()

    def test_initialize_driver_all_methods_fail(self):
        """测试所有驱动获取方法都失败的情况"""
        manager = WebDriverManager(logger=self.logger)

        # 模拟所有方法都返回None
        with patch.object(manager, '_find_project_driver', return_value=None), \
             patch.object(manager, '_find_offline_driver', return_value=None), \
             patch.object(manager, '_enhanced_download_driver', return_value=(None, "failed")):

            result = manager.initialize_driver()

            assert result is None
            self.logger.error.assert_called()

    def test_quit_driver_with_driver(self):
        """测试在有驱动实例时退出"""
        manager = WebDriverManager(logger=self.logger)
        mock_driver = MagicMock()
        manager.driver = mock_driver

        manager.quit_driver()

        mock_driver.quit.assert_called_once()
        self.logger.info.assert_called_once_with("WebDriver 已关闭。")

    def test_quit_driver_without_driver(self):
        """测试在没有驱动实例时退出"""
        manager = WebDriverManager(logger=self.logger)
        manager.driver = None

        manager.quit_driver()

        # 应该不抛出异常
        self.logger.info.assert_called_once_with("没有活动的 WebDriver 实例需要关闭。")

    @patch('selenium.webdriver.Chrome')
    def test_get_system_arch(self, mock_chrome):
        """测试获取系统架构信息"""
        manager = WebDriverManager(logger=self.logger)

        system, arch = manager._get_system_arch()

        assert system in ["Windows", "Linux", "Darwin"]
        assert arch in ["win64", "win32", "linux64", "mac-arm64", "mac-x64"]

    @patch('pathlib.Path.exists')
    def test_verify_driver_executable_valid(self, mock_exists):
        """测试验证有效的可执行驱动"""
        mock_exists.return_value = True

        manager = WebDriverManager(logger=self.logger)

        with patch('os.access', return_value=True), \
             patch('platform.system', return_value='Linux'):

            result = manager._verify_driver_executable("/fake/path/chromedriver")

            assert result is True

    @patch('pathlib.Path.exists')
    def test_verify_driver_executable_not_exists(self, mock_exists):
        """测试验证不存在的可执行驱动"""
        mock_exists.return_value = False

        manager = WebDriverManager(logger=self.logger)

        result = manager._verify_driver_executable("/fake/path/chromedriver")

        assert result is False

    def test_prepare_driver_executable_success(self):
        """测试成功准备可执行驱动"""
        driver_path = os.path.join(self.temp_dir, "chromedriver")
        with open(driver_path, 'w') as f:
            f.write("fake driver")

        manager = WebDriverManager(logger=self.logger)

        with patch('os.access', return_value=True), \
             patch('platform.system', return_value='Linux'):

            result = manager._prepare_driver_executable(driver_path)

            assert result == driver_path

    def test_prepare_driver_executable_fail(self):
        """测试准备可执行驱动失败"""
        manager = WebDriverManager(logger=self.logger)

        result = manager._prepare_driver_executable("/fake/path/chromedriver")

        assert result is None

    @patch('webdriver_manager.ChromeDriverManager')
    def test_download_with_webdriver_manager_success(self, mock_manager):
        """测试使用webdriver-manager成功下载"""
        mock_manager_instance = MagicMock()
        mock_manager_instance.install.return_value = "/fake/path/chromedriver"
        mock_manager.return_value = mock_manager_instance

        manager = WebDriverManager(logger=self.logger)
        target_path = Path(self.temp_dir) / "target"

        result = manager._download_with_webdriver_manager(target_path)

        assert result is True

    def test_cleanup_webdriver_manager_cache(self):
        """测试清理webdriver-manager缓存"""
        manager = WebDriverManager(logger=self.logger)

        # 模拟缓存目录
        cache_dir = os.path.expanduser("~/.wdm")

        with patch('os.path.exists', return_value=True), \
             patch('shutil.rmtree') as mock_rmtree:

            manager._cleanup_webdriver_manager_cache()

            self.logger.info.assert_any_call("清理 webdriver-manager 缓存: ~/.wdm")

    def test_webdriver_manager_integration(self):
        """测试WebDriver管理器的集成场景"""
        # 创建模拟的驱动文件
        driver_path = os.path.join(self.temp_dir, "chromedriver")
        with open(driver_path, 'w') as f:
            f.write("fake driver")

        manager = WebDriverManager(chrome_driver_path=driver_path, logger=self.logger)

        # 1. 测试初始化前的状态
        assert manager.driver is None

        # 2. 模拟成功初始化（实际不会真正启动浏览器）
        with patch('selenium.webdriver.Chrome') as mock_chrome:
            mock_driver = MagicMock()
            mock_chrome.return_value = mock_driver

            driver = manager.initialize_driver()

            assert driver is not None
            assert manager.driver is not None

        # 3. 测试退出驱动
        manager.quit_driver()
        assert manager.driver is None

    def test_driver_strategies_configuration(self):
        """测试驱动管理策略配置"""
        manager = WebDriverManager(logger=self.logger)

        strategies = manager.driver_strategies

        assert strategies['version_check'] is True
        assert strategies['offline_fallback'] is True
        assert strategies['download_resume'] is True
        assert strategies['cache_cleanup'] is True
        assert strategies['hash_verification'] is True