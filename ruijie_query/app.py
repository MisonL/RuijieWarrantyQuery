import logging
import sys  # 导入 sys 模块用于设置日志输出流
from logging.handlers import RotatingFileHandler # 导入 RotatingFileHandler

# 导入各个模块的类
from .data import DataManager
from .webdriver_manager import WebDriverManager
from .page_objects import RuijieQueryPage
from .captcha_solver import CaptchaSolver

import pandas as pd  # RuijieQueryApp 中使用了 pd.DataFrame
import time  # RuijieQueryApp 中使用了 time.sleep

# --- 主应用程序类 ---


class RuijieQueryApp:
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.general_config = self.config_manager.get_general_config()
        # 获取新的AI配置结构
        self.ai_config = self.config_manager.get_ai_config()
        self.result_columns = self.config_manager.get_result_columns()
        self.logging_config = self.config_manager.get_logging_config()  # 获取日志配置
        self.target_url = "https://www.ruijie.com.cn/fw/bx/"  # 锐捷官网固定 URL
        self.config = self.config_manager.get_config()  # 获取完整的 config 对象

        # 初始化日志记录器
        self._setup_logging()
        self.logger = logging.getLogger(__name__)  # 获取当前模块的日志记录器

        self.data_manager = DataManager(
            self.general_config["excel_file_path"],
            self.general_config["sheet_name"],
            self.general_config["sn_column_name"],
            self.result_columns,
            self.logger,  # 传递日志记录器
        )
        self.webdriver_manager = WebDriverManager(
            self.general_config["chrome_driver_path"], self.logger  # 传递日志记录器
        )
        # 将通用AI设置和渠道列表传递给 CaptchaSolver
        self.captcha_solver = CaptchaSolver(
            self.ai_config, # 传递包含通用设置和渠道列表的字典
            self.ai_config["channels"], # 传递渠道列表
            self.logger,  # 传递日志记录器
        )
        # 传递 config 对象和日志记录器给 RuijieQueryPage
        self.query_page = None  # 在运行过程中初始化

    def _setup_logging(self):
        """
        配置日志记录器。
        """
        log_level = self.logging_config["log_level"]
        log_file = self.logging_config.get("log_file") # Use .get() for safety
        log_to_console = self.logging_config.get("log_to_console", True) # Use .get() with default
        # 从配置获取 max_bytes 和 backup_count (ConfigManager 已处理解析)
        max_bytes = self.logging_config.get("max_bytes", 1024 * 1024) # 获取整数值
        backup_count = self.logging_config.get("backup_count", 5) # 获取整数值

        # 创建根记录器并设置级别
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)

        # 定义日志格式
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        # 如果配置了日志文件，添加文件处理器
        if log_file:
            try:
                # 使用 RotatingFileHandler 替代 FileHandler
                file_handler = RotatingFileHandler(
                    log_file,
                    maxBytes=max_bytes,
                    backupCount=backup_count,
                    encoding="utf-8"
                )
                file_handler.setLevel(log_level)
                file_handler.setFormatter(formatter)
                root_logger.addHandler(file_handler)
            except Exception as e:
                print(f"警告：无法创建日志文件 '{log_file}': {e}")
                # 如果文件处理器创建失败，确保控制台处理器仍然工作
                log_to_console = True  # 强制输出到控制台

        # 如果配置了输出到控制台，添加控制台处理器
        if log_to_console:
            console_handler = logging.StreamHandler(sys.stdout)  # 输出到标准输出
            console_handler.setLevel(log_level)
            console_handler.setFormatter(formatter)
            root_logger.addHandler(console_handler)

        # 避免重复添加处理器
        root_logger.propagate = False

    def run(self):
        """
        运行批量查询程序。
        """
        self.logger.info("程序开始运行。")

        df = self.data_manager.load_data()

        if df is None:
            self.logger.error("无法加载Excel数据，程序退出。")
            return

        # 测试AI渠道可用性并更新可用渠道列表
        available_channels = self.captcha_solver.test_channels_availability()
        if not available_channels:
            self.logger.error("没有可用的 AI 渠道，无法进行验证码识别。程序退出。")
            # 注意：这里不需要 quit_driver，因为 driver 还没有初始化
            return # 没有可用渠道，退出程序

        driver = self.webdriver_manager.initialize_driver()
        if driver is None:
            self.logger.error("WebDriver 初始化失败，程序退出。")
            return

        # 在这里初始化 RuijieQueryPage 并传递 config 对象和日志记录器
        self.query_page = RuijieQueryPage(
            driver, self.target_url, self.config, self.logger
        )  # 使用 self.target_url, self.config 和 self.logger


        self.logger.info(f"将使用 {len(available_channels)} 个可用 AI 渠道进行验证码识别。")
        # CaptchaSolver 实例内部已经更新了 channels 列表，这里无需再次设置

        total_rows = len(df)
        self.logger.info(f"开始处理 {total_rows} 个序列号...")

        # 第一次查询
        self._process_queries(df)

        # 补漏机制：检查未成功查询的序列号并进行二次查询
        unqueried_items = self.data_manager.get_unqueried_serial_numbers(
            self.general_config["sn_column_name"]
        )
        if unqueried_items:
            self.logger.info(
                f"\n检测到 {len(unqueried_items)} 个序列号未成功查询，"
                f"尝试进行补漏..."
            )
            # 创建一个只包含未查询成功序列号的临时DataFrame
            unqueried_df = pd.DataFrame(
                unqueried_items,
                columns=["index", self.general_config["sn_column_name"]],
            )
            # 将索引设置为原始DataFrame的索引，方便更新
            unqueried_df.set_index("index", inplace=True)

            self._process_queries(unqueried_df, is_retry=True)
        else:
            self.logger.info("\n所有序列号均已成功查询。")

        # 所有序列号处理完毕或程序中断，保存最终结果
        self.logger.info("\n--- 所有序列号处理完毕或程序中断 ---")
        self.data_manager.save_data()
        # 关闭浏览器
        self.webdriver_manager.quit_driver()
        self.logger.info("程序执行完毕。")

    def _process_queries(self, df_to_process, is_retry=False):
        """
        处理DataFrame中的序列号查询。
        """
        total_rows = len(df_to_process)
        for i, (index, row) in enumerate(df_to_process.iterrows()):
            serial_number = row[self.general_config["sn_column_name"]]
            prefix = "补漏查询" if is_retry else "处理"
            self.logger.info(
                f"\n--- {prefix}第 {i + 1}/{total_rows} 个序列号: "
                f"{serial_number} ---"
            )

            query_results = self._process_single_query(serial_number)

            # 将查询结果更新到DataFrame
            self.data_manager.update_result(index, query_results)

            # 根据 save_interval 配置决定是否保存数据
            save_interval = self.general_config.get("save_interval", 0) # 获取保存间隔，默认为0（不定期保存）
            # 注意：这里的 i 是从 0 开始的迭代索引
            if save_interval > 0 and (i + 1) % save_interval == 0:
                self.logger.info(f"已处理 {i + 1} 个序列号，达到保存间隔，正在保存数据...")
                self.data_manager.save_data()
            elif i == total_rows - 1: # 确保在处理最后一个序列号后总是保存
                 self.logger.info("已处理完最后一个序列号，正在保存最终数据...")
                 self.data_manager.save_data()
            # else: # 如果不满足保存条件，则不保存，减少频繁写入

            # 添加查询延时
            if i < total_rows - 1:  # 最后一个序列号后不需要延时
                self.logger.info(
                    f"等待 {self.general_config['query_delay']} 秒进行下一次查询..."
                )
                time.sleep(self.general_config["query_delay"])

    def _process_single_query(self, serial_number):
        """
        处理单个序列号的查询流程。
        """
        results = {"查询状态": "未知错误"}  # 默认状态
        # 从配置获取重试次数
        max_query_attempts = self.general_config.get("max_query_attempts", 3)
        max_captcha_retries = self.general_config.get("max_captcha_retries", 2)

        self.logger.info(f"开始查询序列号: {serial_number}")

        for query_attempt in range(max_query_attempts):
            self.logger.info(f"查询尝试 {query_attempt + 1}/{max_query_attempts}...")
            try:
                # 每次尝试都重新打开页面并输入序列号，确保页面状态正确
                self.query_page.open_page()
                self.query_page.enter_serial_number(serial_number)

                captcha_solution = None
                # 使用从配置读取的 max_captcha_retries
                for captcha_retry in range(max_captcha_retries + 1):
                    self.logger.info(
                        f"尝试获取验证码图片 (验证码重试 {captcha_retry + 1}/"
                        f"{max_captcha_retries + 1})..."
                    )
                    # 获取验证码图片数据
                    self.logger.info("正在获取验证码图片...")
                    captcha_image_data = self.query_page.get_captcha_image_data()
                    if not captcha_image_data:
                        self.logger.error("获取验证码图片失败。")
                        results["查询状态"] = "获取验证码图片失败"
                        break # 获取图片失败，跳出验证码重试循环

                    # 解决验证码
                    self.logger.info("尝试使用 AI 识别验证码...")
                    ai_start_time = time.time() # 记录 AI 识别开始时间
                    captcha_solution = self.captcha_solver.solve_captcha(captcha_image_data)
                    ai_end_time = time.time() # 记录 AI 识别结束时间
                    ai_recognition_time = ai_end_time - ai_start_time
                    self.logger.info(f"AI 验证码识别耗时: {ai_recognition_time:.2f} 秒。")

                    if captcha_solution:
                        self.logger.info("AI 验证码识别成功。")
                        break  # 识别成功，跳出验证码重试循环
                    else:
                        self.logger.warning(
                            f"AI 验证码识别失败 (验证码重试 {captcha_retry + 1}/"
                            f"{max_captcha_retries + 1})。"
                        )
                        if captcha_retry < max_captcha_retries:
                            self.logger.info("尝试刷新验证码并重试...")
                            if not self.query_page.refresh_captcha():
                                self.logger.error("刷新验证码失败，无法重试。")
                                break  # 刷新失败，无法继续重试验证码
                        else:
                            self.logger.error("达到最大验证码识别重试次数。")

                if not captcha_solution:
                    self.logger.error("AI 验证码识别最终失败，跳过当前查询尝试。")
                    results["查询状态"] = "AI 验证码识别失败"
                    # 不返回，继续外层循环进行下一次查询尝试

                else: # 如果验证码识别成功
                    self.logger.info(f"输入验证码: {captcha_solution}")
                    self.query_page.enter_captcha_solution(captcha_solution)
                    self.query_page.submit_query()
                    self.logger.info("提交查询。")

                    # 提交后，等待结果或错误信息出现
                    self.logger.info("提交查询，等待结果或错误信息...")
                    # 提交后，等待结果或错误信息出现，或验证码刷新
                    self.logger.info("提交查询，等待结果、错误信息或验证码刷新...")
                    # 增加一个循环，以较短间隔检查页面状态
                    wait_time_after_submit = 20 # 提交后等待总时间 (秒)，适当增加以应对慢响应
                    check_interval = 0.5 # 检查间隔 (秒)，缩短间隔以更快响应
                    found_relevant_change = False
                    start_wait_time = time.time()

                    while time.time() - start_wait_time < wait_time_after_submit:
                        # 检查是否出现了结果表格
                        if self.query_page.wait_for_results():
                            self.logger.info("查询结果表格已显示。")
                            found_relevant_change = True
                            break # 找到结果，跳出等待循环

                        # 检查是否出现了错误信息
                        error_message = self.query_page._check_error_message()
                        if error_message:
                            self.logger.warning(f"页面显示错误信息: {error_message}")
                            results["查询状态"] = f"查询失败: {error_message}"
                            found_relevant_change = True
                            break # 找到错误信息，跳出等待循环

                        # 如果既没有结果也没有错误，检查验证码是否刷新
                        if self.query_page.is_captcha_page_and_refreshed():
                             self.logger.warning("检测到验证码已刷新，可能是验证码错误。")
                             results["查询状态"] = "验证码错误，尝试重试"
                             found_relevant_change = True # 视为一种“结果”（需要重试）
                             break # 验证码刷新，跳出等待循环

                        time.sleep(check_interval) # 等待一段时间后再次检查

                    if found_relevant_change:
                        # 如果找到了结果表格且没有错误信息
                        if "查询状态" not in results or not results["查询状态"].startswith("查询失败"):
                             # 尝试解析结果
                             self.logger.info("尝试解析查询结果...")
                             parsed_results = self.query_page.parse_query_result(
                                 serial_number
                             )  # 传递 serial_number

                             if parsed_results:
                                 results = parsed_results
                                 # 如果解析结果中没有查询状态，默认为成功
                                 if "查询状态" not in results:
                                     results["查询状态"] = "成功"
                                 self.logger.info(f"查询结果解析成功: {results}")
                                 return results # 查询成功，返回结果并结束函数
                             else:
                                 # 如果 parse_query_result 返回 None 或空字典，
                                 # 表示解析失败或序列号无效
                                 if "查询状态" not in results or results["查询状态"] == "未知错误":
                                     results["查询状态"] = "查询失败或序列号无效"  # 或者更具体的错误信息
                                 self.logger.warning(
                                     f"查询结果解析失败或序列号无效。最终状态: {results['查询状态']}"
                                 )
                                 # 不返回，继续外层循环进行下一次查询尝试
                         # 如果找到了错误信息或检测到验证码刷新，则 results["查询状态"] 已经被设置
                         # 不返回，继续外层循环进行下一次查询尝试
                    else:
                        self.logger.warning("提交查询后，在规定时间内未检测到结果、错误信息或验证码刷新。")
                        results["查询状态"] = "提交后无响应或未知错误"
                        # 不返回，继续外层循环进行下一次查询尝试



            except Exception as e:
                self.logger.error(
                    f"查询序列号 {serial_number} 时发生错误: {e}", exc_info=True
                )  # 记录详细错误信息
                results["查询状态"] = f"查询错误: {e}"
                # 不返回，继续外层循环进行下一次查询尝试

        # 如果所有查询尝试都失败
        self.logger.error(f"序列号 {serial_number} 达到最大查询尝试次数，查询最终失败。")
        # 确保 results 中有最终的查询状态
        if "查询状态" not in results or results["查询状态"] == "未知错误":
             results["查询状态"] = "达到最大查询尝试次数"
        return results # 返回最终的失败结果
