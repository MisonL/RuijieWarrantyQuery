import logging  # 导入 logging 模块
import os # 导入 os 模块
import platform # 导入 platform 模块
import shutil # 导入 shutil 模块
import sys # 导入 sys 模块
from pathlib import Path # 导入 Path 用于获取主目录
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager  # 导入 ChromeDriverManager

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

    def initialize_driver(self):
        """
        初始化Selenium WebDriver。
        查找顺序:
        1. config.ini 中指定的路径
        2. 项目 drivers 目录下对应平台和架构的路径
        3. 使用 webdriver-manager 下载到项目 drivers 目录下对应平台和架构的路径，并删除缓存。
        """
        self.logger.info("正在初始化 WebDriver...")
        options = webdriver.ChromeOptions()
        # options.add_argument('--headless') # 如果需要无头模式，取消注释
        # options.add_argument('--disable-gpu') # 在某些系统上可能需要

        driver_path = None

        # 1. 检查 config.ini 中指定的路径
        config_driver_path = self.chrome_driver_path
        if config_driver_path and os.path.exists(config_driver_path):
            self.logger.info(f"使用 config.ini 中指定的 ChromeDriver 路径: {config_driver_path}")
            driver_path = config_driver_path

        # 2. 如果 config 中未指定或无效，检查项目 drivers 目录
        if not driver_path:
            local_driver_dir, local_driver_path = self._get_platform_specific_driver_path()
            if local_driver_path and os.path.exists(local_driver_path):
                self.logger.info(f"在项目目录下找到 ChromeDriver: {local_driver_path}")
                driver_path = local_driver_path
            else:
                self.logger.info(f"在项目目录 {local_driver_dir or self.project_drivers_path} 未找到 ChromeDriver。")

        # 3. 如果本地项目目录也没有，则尝试使用 webdriver-manager 自动下载、复制并删除缓存
        if not driver_path:
            try:
                # 调用 install() 让其下载到默认位置或缓存
                self.logger.info("让 webdriver-manager 下载/获取 ChromeDriver...")
                installed_driver_path_cache = ChromeDriverManager().install()

                if not installed_driver_path_cache or not os.path.exists(installed_driver_path_cache):
                     raise Exception(f"webdriver-manager install() 返回无效路径或文件不存在: {installed_driver_path_cache}")

                self.logger.info(f"webdriver-manager 获取 ChromeDriver 成功 (缓存路径): {installed_driver_path_cache}")

                # 计算项目内的目标路径
                target_driver_dir, target_driver_path = self._get_platform_specific_driver_path()
                if not target_driver_dir or not target_driver_path:
                    raise Exception("无法确定项目内特定平台的驱动程序目标路径。")

                # 确保目标目录存在
                os.makedirs(target_driver_dir, exist_ok=True)

                # 将驱动从缓存路径复制到项目目标路径
                try:
                    self.logger.info(f"将 ChromeDriver 从 '{installed_driver_path_cache}' 复制到 '{target_driver_path}'")
                    shutil.copy2(installed_driver_path_cache, target_driver_path) # copy2 保留元数据

                    # 验证复制是否成功
                    if os.path.exists(target_driver_path):
                        self.logger.info(f"成功将 ChromeDriver 复制到项目目录: {target_driver_path}")
                        driver_path = target_driver_path # 使用项目内的路径

                        # --- 添加删除缓存目录的逻辑 ---
                        try:
                            wdm_cache_path = Path.home() / ".wdm"
                            if wdm_cache_path.exists() and wdm_cache_path.is_dir():
                                self.logger.info(f"尝试删除 webdriver-manager 缓存目录: {wdm_cache_path}")
                                shutil.rmtree(wdm_cache_path)
                                self.logger.info(f"成功删除缓存目录: {wdm_cache_path}")
                            else:
                                self.logger.debug(f"缓存目录不存在或不是目录，无需删除: {wdm_cache_path}")
                        except Exception as rm_err:
                            # 删除缓存失败通常不影响主流程，记录警告即可
                            self.logger.warning(f"删除 webdriver-manager 缓存目录时出错: {rm_err}", exc_info=False)
                        # --- 缓存删除逻辑结束 ---

                    else:
                        raise Exception(f"复制后目标文件 '{target_driver_path}' 不存在。")

                except Exception as copy_err:
                    # 如果复制失败，记录错误，driver_path 保持为 None，让后续逻辑处理
                    self.logger.error(f"将 ChromeDriver 从缓存复制到项目目录失败: {copy_err}", exc_info=True)
                    # 初始化将失败，因为 driver_path 仍为 None

            except Exception as e:
                self.logger.error(
                    f"使用 webdriver-manager 获取或复制 ChromeDriver 失败: {e}",
                    exc_info=True,
                )
                self.logger.error(
                    "请确保已正确安装 Chrome 浏览器，或在 config.ini 中配置 'chrome_driver_path'，或手动将正确的 ChromeDriver 放置在 'drivers/<OS>/<arch>/' 目录下。"
                )
                return None

        # 如果最终 driver_path 仍然为 None
        if not driver_path:
             self.logger.error("无法确定有效的 ChromeDriver 路径，WebDriver 初始化失败。")
             return None

        # 使用最终确定的 driver_path 初始化 Service
        try:
            # 确保驱动文件有执行权限 (尤其是在 Linux/macOS 上复制后可能需要)
            if platform.system() in ["Linux", "Darwin"]:
                try:
                    os.chmod(driver_path, 0o755)
                    self.logger.debug(f"已设置 ChromeDriver 执行权限: {driver_path}")
                except Exception as chmod_err:
                    self.logger.warning(f"设置 ChromeDriver 执行权限失败: {chmod_err}", exc_info=False)

            service = Service(executable_path=driver_path)
            self.driver = webdriver.Chrome(service=service, options=options)
            self.logger.info(f"WebDriver 初始化成功 (使用路径: {driver_path})。")
            return self.driver
        except Exception as e:
            self.logger.error(f"使用路径 '{driver_path}' 初始化 WebDriver 时发生错误: {e}", exc_info=True)
            self.logger.error(
                "请确保 ChromeDriver 路径正确，并且与您的 Chrome 浏览器版本兼容。"
            )
            return None

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
