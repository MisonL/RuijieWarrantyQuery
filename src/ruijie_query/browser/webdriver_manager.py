import logging  # 导入 logging 模块
import os # 导入 os 模块
import platform # 导入 platform 模块
import shutil # 导入 shutil 模块
import sys # 导入 sys 模块
import json
import hashlib
import requests
from pathlib import Path # 导入 Path 用于获取主目录
from typing import Optional, Dict, Tuple, List, Any
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager  # 导入 ChromeDriverManager
try:
    from webdriver_manager.core.os_manager import ChromeType
except ImportError:
    # Fallback for older versions - suppress IDE warning
    ChromeType = None  # type: ignore

# 导入性能监控模块
from ..monitoring.performance_monitor import get_monitor, monitor_operation

# --- 增强的 ChromeDriver 管理器 ---
class EnhancedChromeDriverManager:
    """
    增强的ChromeDriver管理器，支持版本兼容性检查、断点续传、离线备选方案
    """
    # 为测试兼容性添加类型注释
    cache: Dict[str, Any]  # type: ignore

    def __init__(self, logger):
        self.logger = logger
        self.cache_dir = Path.home() / ".wdm_cache"
        self.cache_dir.mkdir(exist_ok=True)
        self.version_cache_file = self.cache_dir / "version_cache.json"
        self.download_stats_file = self.cache_dir / "download_stats.json"

        # 加载缓存数据
        self.version_cache = self._load_cache(self.version_cache_file, {})
        self.download_stats = self._load_cache(self.download_stats_file, {})

        # ChromeDriver下载URL模板
        self.download_urls = {
            "windows": "https://storage.googleapis.com/chrome-for-testing-public/{version}/win64.zip",
            "mac-x64": "https://storage.googleapis.com/chrome-for-testing-public/{version}/mac-x64.zip",
            "mac-arm64": "https://storage.googleapis.com/chrome-for-testing-public/{version}/mac-arm64.zip",
            "linux64": "https://storage.googleapis.com/chrome-for-testing-public/{version}/linux64.zip"
        }

    @property
    def cache(self):
        """为测试兼容性提供的 cache 属性，返回 version_cache"""
        return self.version_cache

    @cache.setter
    def cache(self, value):
        """为测试兼容性提供的 cache 属性 setter"""
        self.version_cache.clear()
        self.version_cache.update(value)

    def _load_cache(self, cache_file, default):
        """加载JSON缓存文件"""
        try:
            if cache_file.exists():
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.debug(f"加载缓存文件失败 {cache_file}: {e}")
        return default

    def _save_cache(self, cache_file, data):
        """保存JSON缓存文件"""
        try:
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.warning(f"保存缓存文件失败 {cache_file}: {e}")

    def get_chrome_version(self) -> Optional[str]:
        """
        获取当前安装的Chrome浏览器版本
        """
        try:
            import subprocess

            system = platform.system()
            if system == "Windows":
                # Windows: 使用reg查询版本
                result = subprocess.run(
                    ['reg', 'query', 'HKEY_CURRENT_USER\\Software\\Google\\Chrome\\BLBeacon', '/v', 'version'],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    version = result.stdout.strip().split()[-1]
                    self.logger.debug(f"通过注册表获取Chrome版本: {version}")
                    return version
            elif system == "Darwin":  # macOS
                # macOS: 使用mdls查询版本
                result = subprocess.run(
                    ['mdls', '-name', 'kMDItemVersion', '-raw', '/Applications/Google Chrome.app'],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    version = result.stdout.strip()
                    self.logger.debug(f"通过mdls获取Chrome版本: {version}")
                    return version
            else:  # Linux
                # Linux: 尝试多个命令
                commands = ['google-chrome --version', 'chromium-browser --version', 'chromium --version']
                for cmd in commands:
                    try:
                        result = subprocess.run(cmd.split(), capture_output=True, text=True, timeout=10)
                        if result.returncode == 0:
                            version = result.stdout.strip().split()[-1]
                            self.logger.debug(f"通过 {cmd} 获取Chrome版本: {version}")
                            return version
                    except (subprocess.TimeoutExpired, FileNotFoundError):
                        continue

        except Exception as e:
            self.logger.warning(f"获取Chrome版本失败: {e}")

        self.logger.warning("无法获取Chrome版本，将使用最新版本的ChromeDriver")
        return None

    def get_compatible_chromedriver_version(self, chrome_version: Optional[str] = None) -> Optional[str]:
        """
        获取与Chrome浏览器兼容的ChromeDriver版本
        """
        if not chrome_version:
            chrome_version = self.get_chrome_version()

        if not chrome_version:
            return None

        # 检查缓存
        cache_key = f"chrome_{chrome_version}"
        if cache_key in self.version_cache:
            cached_version = self.version_cache[cache_key]["driver_version"]
            self.logger.info(f"使用缓存的ChromeDriver版本: {cached_version}")
            return cached_version

        try:
            # 使用ChromeDriverManager获取兼容版本
            from webdriver_manager.chrome import ChromeDriverManager

            # 使用标准的ChromeDriverManager instead of EnhancedChromeDriverManager
            chrome_manager = ChromeDriverManager()
            driver_path = chrome_manager.install()

            # 解析版本信息
            if driver_path and os.path.exists(driver_path):
                # 尝试从路径中提取版本信息
                version_info = self._extract_version_from_path(driver_path)
                if version_info:
                    # 缓存版本信息
                    self.version_cache[cache_key] = {
                        "driver_version": version_info,
                        "chrome_version": chrome_version,
                        "timestamp": str(Path().cwd())
                    }
                    self._save_cache(self.version_cache_file, self.version_cache)
                    self.logger.info(f"获取到兼容的ChromeDriver版本: {version_info}")
                    return version_info

        except Exception as e:
            self.logger.warning(f"通过ChromeDriverManager获取兼容版本失败: {e}")

        # 备用方案：使用主版本号匹配
        major_version = chrome_version.split('.')[0]
        fallback_version = f"{major_version}.0.0.0"
        self.logger.warning(f"使用备用版本匹配: ChromeDriver {fallback_version}")
        return fallback_version

    def _extract_version_from_path(self, driver_path: str) -> Optional[str]:
        """从驱动文件路径中提取版本信息"""
        try:
            # ChromeDriver路径通常包含版本信息
            path_parts = Path(driver_path).parts
            for part in path_parts:
                # 查找类似 115.0.0.0 的版本格式
                import re
                version_match = re.search(r'\d+\.\d+\.\d+\.\d+', part)
                if version_match:
                    return version_match.group()
        except Exception as e:
            self.logger.debug(f"从路径提取版本失败: {e}")
        return None

    def download_with_resume(self, url: str, target_path: Path, expected_hash: Optional[str] = None) -> bool:
        """
        支持断点续传的下载功能
        """
        try:
            # 检查是否已有部分下载的文件
            temp_path = target_path.with_suffix(target_path.suffix + '.part')
            resume_header = {}
            if temp_path.exists():
                resume_header['Range'] = f'bytes={temp_path.stat().st_size}-'
                self.logger.info(f"检测到部分下载文件，从 {temp_path.stat().st_size} 字节处继续下载")

            response = requests.get(url, headers=resume_header, stream=True, timeout=30)
            response.raise_for_status()

            # 获取文件总大小
            total_size = int(response.headers.get('content-length', 0))
            if total_size == 0:
                # 如果没有content-length，尝试直接下载
                with open(temp_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
            else:
                # 分块下载并显示进度
                downloaded = 0
                with open(temp_path, 'ab') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if downloaded % (1024 * 1024) == 0:  # 每MB显示一次进度
                                progress = (downloaded / total_size) * 100
                                self.logger.debug(f"下载进度: {progress:.1f}% ({downloaded}/{total_size} 字节)")

            # 验证文件完整性
            if expected_hash:
                actual_hash = self._calculate_file_hash(temp_path)
                if actual_hash != expected_hash:
                    self.logger.error(f"文件哈希校验失败: 期望 {expected_hash}, 实际 {actual_hash}")
                    temp_path.unlink(missing_ok=True)
                    return False

            # 移动到目标位置
            temp_path.rename(target_path)
            self.logger.info(f"下载完成: {target_path}")
            return True

        except Exception as e:
            self.logger.error(f"下载失败: {e}")
            # 清理部分下载的文件
            temp_path = target_path.with_suffix(target_path.suffix + '.part')
            temp_path.unlink(missing_ok=True)
            return False

    def _calculate_file_hash(self, file_path: Path, algorithm: str = 'sha256') -> str:
        """计算文件哈希值"""
        try:
            hash_obj = hashlib.new(algorithm)
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    hash_obj.update(chunk)
            return hash_obj.hexdigest()
        except Exception as e:
            self.logger.error(f"计算文件哈希失败: {e}")
            return ""

    def get_offline_driver_path(self, system: str, arch: str) -> Optional[str]:
        """
        查找离线备选驱动路径
        """
        # 检查常见位置
        offline_paths = [
            # 用户指定路径
            os.environ.get('CHROMEDRIVER_PATH'),
            # 项目内路径
            os.path.join(os.path.dirname(__file__), '..', 'drivers', system, arch),
            # 系统路径
            '/usr/local/bin/chromedriver',
            '/usr/bin/chromedriver',
            '/opt/homebrew/bin/chromedriver',
            # 用户主目录
            os.path.expanduser('~/bin/chromedriver'),
            os.path.expanduser('~/.local/bin/chromedriver'),
        ]

        for path in offline_paths:
            if path and os.path.exists(path):
                self.logger.info(f"找到离线ChromeDriver: {path}")
                return path

        return None

    def cleanup_cache(self):
        """清理所有缓存数据（用于测试兼容性）"""
        try:
            # 完全清空缓存数据
            self.version_cache.clear()
            self.download_stats.clear()

            # 保存空缓存到文件
            self._save_cache(self.version_cache_file, self.version_cache)
            self._save_cache(self.download_stats_file, self.download_stats)

            self.logger.info("缓存清理完成")
        except Exception as e:
            self.logger.warning(f"清理缓存失败: {e}")

    def get_download_stats(self) -> Dict:
        """获取下载统计信息"""
        return self.download_stats.copy()


# --- WebDriver 管理类 ---
class WebDriverManager:
    def __init__(self, chrome_driver_path=None, logger=None):  # 添加 logger 参数
        self.chrome_driver_path = chrome_driver_path
        self.driver = None
        self.logger = logger or logging.getLogger(
            __name__
        )  # 使用传入的 logger 或创建新的
        # 项目根目录下的 drivers 文件夹路径
        self.project_drivers_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "drivers"))

        # 初始化增强的ChromeDriver管理器
        self.enhanced_driver_manager = EnhancedChromeDriverManager(self.logger)

        # 驱动管理策略配置
        self.driver_strategies = {
            'version_check': True,      # 启用版本兼容性检查
            'offline_fallback': True,   # 启用离线备选方案
            'download_resume': True,    # 启用断点续传
            'cache_cleanup': True,      # 启用缓存清理
            'hash_verification': True,  # 启用文件哈希验证
        }

    def _get_platform_specific_driver_path(self):
        """根据操作系统和架构确定本地驱动路径"""
        system = platform.system()
        arch = platform.machine()

        if system == "Windows":
            os_name = "Windows"
            arch_name = "win64" if platform.architecture()[0] == "64bit" else "win32"
            exe_name = "chromedriver.exe"
        elif system == "Linux":
            os_name = "Linux"
            arch_name = "linux64" # 假设只支持 64 位
            exe_name = "chromedriver"
        elif system == "Darwin": # macOS
            os_name = "macOS"
            arch_name = "mac-arm64" if arch == "arm64" else "mac-x64"
            exe_name = "chromedriver"
        else:
            self.logger.warning(f"不支持的操作系统: {system}")
            return None, None

        driver_dir = os.path.join(self.project_drivers_path, os_name, arch_name)
        driver_path = os.path.join(driver_dir, exe_name)
        return driver_dir, driver_path

    @monitor_operation("WebDriver浏览器启动", log_slow=True)
    def initialize_driver(self):
        """
        初始化Selenium WebDriver。
        增强的驱动管理策略:
        1. 优先使用配置指定的路径
        2. 检查项目内预置驱动
        3. 使用增强的自动下载机制（版本检查、断点续传）
        4. 离线备选方案
        5. 智能缓存管理
        """
        self.logger.info("正在初始化增强版 WebDriver...")

        # 配置Chrome选项
        options = Options()

        # 🆕 优化3：WebDriver启动性能优化参数（快速实施）
        options.add_argument('--headless')  # 无头模式，不显示浏览器窗口
        options.add_argument('--disable-gpu')  # 禁用GPU加速
        options.add_argument('--no-sandbox')  # 沙盒模式
        options.add_argument('--disable-dev-shm-usage')  # 禁用/dev/shm使用
        options.add_argument('--disable-extensions')  # 禁用浏览器扩展
        options.add_argument('--disable-images')  # 🆕 禁用图片加载，提升启动速度
        options.add_argument('--disable-logging')  # 🆕 禁用日志输出
        options.add_argument('--silent')  # 🆕 静默模式，减少输出
        options.add_argument('--disable-background-timer-throttling')  # 🆕 禁用后台节流
        options.add_argument('--disable-renderer-backgrounding')  # 🆕 禁用渲染器后台

        driver_path = None
        driver_strategy = "unknown"

        try:
            # 策略1: 使用配置文件指定的路径
            if self.chrome_driver_path and os.path.exists(self.chrome_driver_path):
                driver_path = self.chrome_driver_path
                driver_strategy = "config_specified"
                self.logger.info(f"使用配置指定的 ChromeDriver: {driver_path}")

            # 策略2: 检查项目内预置驱动
            if not driver_path:
                driver_path = self._find_project_driver()
                if driver_path:
                    driver_strategy = "project_preinstalled"
                    self.logger.info(f"使用项目预置 ChromeDriver: {driver_path}")

            # 策略3: 尝试离线备选方案
            if not driver_path and self.driver_strategies.get('offline_fallback', False):
                driver_path = self._find_offline_driver()
                if driver_path:
                    driver_strategy = "offline_fallback"
                    self.logger.info(f"使用离线备选 ChromeDriver: {driver_path}")

            # 策略4: 增强的自动下载
            if not driver_path:
                driver_path, strategy = self._enhanced_download_driver()
                if driver_path:
                    driver_strategy = strategy
                    self.logger.info(f"使用自动下载 ChromeDriver: {driver_path}")

            # 如果所有策略都失败
            if not driver_path:
                self.logger.error("所有 ChromeDriver 获取策略都失败了")
                self.logger.error("请检查:")
                self.logger.error("1. Chrome 浏览器是否正确安装")
                self.logger.error("2. 网络连接是否正常")
                self.logger.error("3. 是否可以在 config.ini 中手动指定 chrome_driver_path")
                self.logger.error("4. 是否有足够的磁盘空间")
                return None

            # 验证和准备驱动的最后步骤
            driver_path = self._prepare_driver_executable(driver_path)
            if not driver_path:
                return None

            # 创建并返回 WebDriver 实例
            service = Service(executable_path=driver_path)
            self.driver = webdriver.Chrome(service=service, options=options)

            self.logger.info(f"WebDriver 初始化成功 ({driver_strategy})")
            self.logger.info(f"使用路径: {driver_path}")

            # 记录下载统计
            if driver_strategy.startswith("auto_download"):
                self.enhanced_driver_manager.download_stats[f"last_success_{driver_strategy}"] = {
                    "timestamp": str(Path().cwd()),
                    "driver_path": driver_path,
                    "status": "success"
                }
                self.enhanced_driver_manager._save_cache(
                    self.enhanced_driver_manager.download_stats_file,
                    self.enhanced_driver_manager.download_stats
                )

            return self.driver

        except Exception as e:
            self.logger.error(f"WebDriver 初始化失败: {e}", exc_info=True)
            return None

    def _find_project_driver(self) -> Optional[str]:
        """查找项目内预置的驱动"""
        try:
            local_driver_dir, local_driver_path = self._get_platform_specific_driver_path()
            if local_driver_path and os.path.exists(local_driver_path):
                self.logger.debug(f"在项目目录找到驱动: {local_driver_path}")
                return local_driver_path
            else:
                self.logger.debug(f"项目目录 {local_driver_dir} 中未找到驱动")
        except Exception as e:
            self.logger.debug(f"查找项目驱动时出错: {e}")
        return None

    def _find_offline_driver(self) -> Optional[str]:
        """查找离线备选驱动"""
        try:
            system, arch = self._get_system_arch()
            offline_path = self.enhanced_driver_manager.get_offline_driver_path(system, arch)
            if offline_path:
                # 验证文件是否可执行
                if self._verify_driver_executable(offline_path):
                    return offline_path
                else:
                    self.logger.warning(f"离线驱动文件不可执行: {offline_path}")
        except Exception as e:
            self.logger.debug(f"查找离线驱动时出错: {e}")
        return None

    def _enhanced_download_driver(self) -> Tuple[Optional[str], str]:
        """增强的自动下载机制"""
        try:
            strategy = "auto_download_enhanced"
            self.logger.info("开始增强版自动下载 ChromeDriver...")

            # 获取Chrome版本信息
            chrome_version = self.enhanced_driver_manager.get_chrome_version()
            self.logger.info(f"检测到 Chrome 版本: {chrome_version or '未知'}")

            # 获取兼容的ChromeDriver版本
            driver_version = self.enhanced_driver_manager.get_compatible_chromedriver_version(chrome_version)
            if not driver_version:
                self.logger.warning("无法确定兼容的 ChromeDriver 版本，使用默认下载策略")
                strategy = "auto_download_default"

            # 计算目标路径
            target_driver_dir, target_driver_path = self._get_platform_specific_driver_path()
            if not target_driver_dir or not target_driver_path:
                raise Exception("无法确定项目内特定平台的驱动程序目标路径。")

            # 确保目标目录存在
            os.makedirs(target_driver_dir, exist_ok=True)

            # 尝试增强下载
            success = self._download_driver_enhanced(driver_version, Path(target_driver_path))
            if success:
                return str(Path(target_driver_path)), strategy

            # 增强下载失败，回退到传统方法
            self.logger.warning("增强下载失败，回退到传统下载方法")
            fallback_result = self._fallback_download_driver(Path(target_driver_path))
            return str(fallback_result[0]) if fallback_result[0] else None, fallback_result[1]

        except Exception as e:
            self.logger.error(f"增强下载 ChromeDriver 失败: {e}")
            return None, "failed"

    def _download_driver_enhanced(self, driver_version: Optional[str], target_path: Path) -> bool:
        """增强的驱动下载实现"""
        try:
            # 尝试使用requests直接下载（如果提供版本信息）
            if driver_version:
                system, arch = self._get_system_arch()
                download_url = self._get_download_url(driver_version, system, arch)

                if download_url:
                    self.logger.info(f"尝试直接下载: {download_url}")
                    success = self.enhanced_driver_manager.download_with_resume(
                        download_url, target_path
                    )
                    if success:
                        return True

            # 如果直接下载失败，使用传统webdriver-manager
            self.logger.info("回退到 webdriver-manager 下载")
            return self._download_with_webdriver_manager(target_path)

        except Exception as e:
            self.logger.error(f"增强下载失败: {e}")
            return False

    def _get_download_url(self, version: str, system: str, arch: str) -> Optional[str]:
        """获取ChromeDriver下载URL"""
        try:
            # 使用Chrome for Testing的官方URL格式
            url_key = f"{system.lower()}-{arch}" if system == "Darwin" else system.lower()
            if url_key not in self.enhanced_driver_manager.download_urls:
                return None

            url_template = self.enhanced_driver_manager.download_urls[url_key]
            # 构建URL，注意Chrome for Testing的URL格式可能不同
            base_url = "https://storage.googleapis.com/chrome-for-testing-public"

            if system == "Windows":
                return f"{base_url}/{version}/win64/chromedriver-win64.zip"
            elif system == "Darwin":
                if arch == "arm64":
                    return f"{base_url}/{version}/mac-arm64/chromedriver-mac-arm64.zip"
                else:
                    return f"{base_url}/{version}/mac-x64/chromedriver-mac-x64.zip"
            elif system == "Linux":
                return f"{base_url}/{version}/linux64/chromedriver-linux64.zip"

        except Exception as e:
            self.logger.debug(f"构建下载URL失败: {e}")
        return None

    def _download_with_webdriver_manager(self, target_path: Path) -> bool:
        """使用webdriver-manager下载（增强版）"""
        try:
            self.logger.info("使用 webdriver-manager 下载 ChromeDriver...")

            # 使用ChromeDriverManager下载
            chrome_manager = ChromeDriverManager()
            cached_driver_path = chrome_manager.install()

            if not cached_driver_path or not os.path.exists(cached_driver_path):
                self.logger.error("webdriver-manager 返回无效路径")
                return False

            # 复制到目标路径
            shutil.copy2(cached_driver_path, target_path)
            self.logger.info(f"成功下载并复制 ChromeDriver 到: {target_path}")

            # 清理webdriver-manager缓存
            if self.driver_strategies.get('cache_cleanup', True):
                self._cleanup_webdriver_manager_cache()

            return True

        except Exception as e:
            self.logger.error(f"webdriver-manager 下载失败: {e}")
            return False

    def _fallback_download_driver(self, target_path: Path) -> Tuple[Optional[Path], str]:
        """回退下载策略"""
        try:
            # 尝试简单的webdriver-manager下载
            self.logger.info("尝试回退下载策略...")
            if self._download_with_webdriver_manager(target_path):
                return target_path, "auto_download_fallback"
            else:
                return None, "download_failed"

        except Exception as e:
            self.logger.error(f"回退下载失败: {e}")
            return None, "download_failed"

    def _prepare_driver_executable(self, driver_path: str) -> Optional[str]:
        """准备可执行的驱动文件"""
        try:
            # 检查文件是否存在
            if not os.path.exists(driver_path):
                self.logger.error(f"驱动文件不存在: {driver_path}")
                return None

            # 在Linux/macOS上设置执行权限
            if platform.system() in ["Linux", "Darwin"]:
                try:
                    os.chmod(driver_path, 0o755)
                    self.logger.debug(f"已设置执行权限: {driver_path}")
                except Exception as chmod_err:
                    self.logger.warning(f"设置执行权限失败: {chmod_err}")

            # 验证文件完整性
            if not self._verify_driver_executable(driver_path):
                return None

            return driver_path

        except Exception as e:
            self.logger.error(f"准备驱动文件失败: {e}")
            return None

    def _verify_driver_executable(self, driver_path: str) -> bool:
        """验证驱动文件是否可执行"""
        try:
            if platform.system() == "Windows":
                # Windows上检查文件是否存在和大小
                return os.path.exists(driver_path) and os.path.getsize(driver_path) > 1024
            else:
                # Unix系统上检查是否可执行
                return os.access(driver_path, os.X_OK)

        except Exception as e:
            self.logger.warning(f"验证驱动可执行性失败: {e}")
            return False

    def _cleanup_webdriver_manager_cache(self):
        """清理webdriver-manager缓存"""
        try:
            wdm_cache_path = Path.home() / ".wdm"
            if wdm_cache_path.exists() and wdm_cache_path.is_dir():
                self.logger.info(f"清理 webdriver-manager 缓存: {wdm_cache_path}")
                shutil.rmtree(wdm_cache_path)
                self.logger.info("缓存清理成功")
        except Exception as e:
            self.logger.warning(f"清理缓存失败: {e}")

    def _get_system_arch(self) -> Tuple[str, str]:
        """获取系统和架构信息"""
        system = platform.system()
        arch = platform.machine()

        if system == "Windows":
            arch_name = "win64" if platform.architecture()[0] == "64bit" else "win32"
        elif system == "Darwin":  # macOS
            arch_name = "mac-arm64" if arch == "arm64" else "mac-x64"
        elif system == "Linux":
            arch_name = "linux64"
        else:
            arch_name = "unknown"

        return system, arch_name

    def quit_driver(self):
        """
        关闭WebDriver。
        """
        if self.driver:
            self.logger.info("正在关闭 WebDriver...")
            self.driver.quit()
            self.driver = None
            self.logger.info("WebDriver 已关闭。")
        else:
            self.logger.warning("WebDriver 未初始化，无需关闭。")
