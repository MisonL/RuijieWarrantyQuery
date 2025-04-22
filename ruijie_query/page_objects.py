import logging  # 导入 logging 模块
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# --- 锐捷查询页面交互类 ---
class RuijieQueryPage:
    def __init__(
        self, driver, target_url, config, logger=None
    ):  # 接收 config 对象和 logger
        self.driver = driver
        self.target_url = target_url
        self.config = config  # 保存 config 对象
        self.logger = logger or logging.getLogger(
            __name__
        )  # 使用传入的 logger 或创建新的
        self._last_captcha_src = None # 添加属性用于存储上一次验证码图片的 src

        # 网页元素定位器
        self.serial_input_locator = (By.CSS_SELECTOR, 'textarea[name="serialNumber"]')
        self.captcha_img_locator = (By.CSS_SELECTOR, "img.verification-code")
        self.captcha_input_locator = (By.CSS_SELECTOR, 'input[name="imageCode"]')
        self.submit_button_locator = (By.CSS_SELECTOR, "button.xulie-bottom-left")
        # 更新结果区域定位器，根据用户提供的HTML片段，结果在一个表格中
        # 尝试通过查找包含特定文本（如“序列号”）的th元素的父级表格来定位结果表格
        self.result_table_locator = (By.CSS_SELECTOR, "div.chaxun-content-center table")
        # 错误信息定位器 (尝试多种可能的错误提示)
        # 1. 明确的错误消息容器 (如果存在) - 需要根据实际页面调整
        # self.error_container_locator = (By.CSS_SELECTOR, "div.error-message-class")
        # 2. 基于文本内容的定位器 (更通用)
        self.captcha_error_locator = (By.XPATH, "//*[contains(text(), '验证码错误')]")
        self.sn_not_found_locator = (By.XPATH, "//*[contains(text(), '未找到您查询的产品') or contains(text(), '序列号无效')]")
        # 可以根据需要添加其他错误文本的定位器

    def open_page(self):
        """
        打开查询页面。
        """
        self.logger.info(f"打开查询页面: {self.target_url}")
        self.driver.get(self.target_url)

    def enter_serial_number(self, serial_number):
        """
        输入序列号。
        """
        self.logger.info(f"输入序列号: {serial_number}")
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located(self.serial_input_locator)
        )
        serial_input = self.driver.find_element(*self.serial_input_locator)
        serial_input.send_keys(serial_number)

    def get_captcha_image_data(self):
        """
        获取验证码图片数据。
        """
        self.logger.info("获取验证码图片数据...")
        # 增加等待条件，确保图片可见且高度大于 0
        WebDriverWait(self.driver, 10).until(
            EC.visibility_of_element_located(self.captcha_img_locator)
        )
        captcha_img = self.driver.find_element(*self.captcha_img_locator)
        # 进一步检查元素大小，确保高度大于 0
        WebDriverWait(self.driver, 10).until(
            lambda driver: captcha_img.size["height"] > 0
        )
        self.logger.info("成功获取验证码图片数据。")
        # 记录当前验证码图片的 src 属性
        self._last_captcha_src = captcha_img.get_attribute("src")
        self.logger.debug(f"记录当前验证码 src: {self._last_captcha_src}")
        return captcha_img.screenshot_as_png

    def refresh_captcha(self):
        """
        尝试刷新验证码图片。
        根据网络分析，点击验证码图片会触发新的图片加载。
        等待条件为验证码图片的 src 属性发生变化。
        """
        self.logger.info("尝试刷新验证码...")
        try:
            # 确保验证码图片可见
            WebDriverWait(self.driver, 10).until(
                EC.visibility_of_element_located(self.captcha_img_locator)
            )
            captcha_img = self.driver.find_element(*self.captcha_img_locator)

            # 获取当前的 src 属性
            initial_src = captcha_img.get_attribute("src")
            self.logger.debug(f"刷新前验证码 src: {initial_src}")

            # 点击验证码图片触发刷新
            captcha_img.click()
            self.logger.debug("已点击验证码图片。")

            # 等待验证码图片的 src 属性变化
            WebDriverWait(self.driver, 10).until(
                lambda driver: captcha_img.get_attribute("src") != initial_src
            )
            self.logger.info("验证码刷新成功，检测到 src 属性变化。")
            # 刷新成功后，更新记录的 src
            self._last_captcha_src = captcha_img.get_attribute("src")
            self.logger.debug(f"刷新后更新记录的 src: {self._last_captcha_src}")
            return True
        except Exception as e:
            self.logger.error(f"刷新验证码失败或超时: {e}", exc_info=True)
            return False

    def is_captcha_page_and_refreshed(self):
        """
        检查当前页面是否仍然是查询页面，并且验证码图片是否已经刷新。
        用于判断提交验证码后是否因错误导致页面刷新。
        """
        self.logger.debug("检查页面是否为查询页且验证码已刷新...")
        try:
            # 检查查询页面特有元素是否存在 (例如序列号输入框或验证码输入框)
            # 使用较短的等待时间，快速判断页面类型
            WebDriverWait(self.driver, 2).until( # 缩短等待时间
                EC.presence_of_element_located(self.serial_input_locator)
            )
            WebDriverWait(self.driver, 2).until( # 缩短等待时间
                EC.presence_of_element_located(self.captcha_input_locator)
            )
            self.logger.debug("页面仍为查询页面。")

            # 检查验证码图片是否存在且 src 属性与上次记录的不同
            WebDriverWait(self.driver, 2).until( # 缩短等待时间
                EC.visibility_of_element_located(self.captcha_img_locator)
            )
            current_captcha_img = self.driver.find_element(*self.captcha_img_locator)
            current_captcha_src = current_captcha_img.get_attribute("src")
            self.logger.debug(f"当前验证码 src: {current_captcha_src}, 上次记录 src: {self._last_captcha_src}")

            # 只有当有上次记录的 src 且当前 src 不同时，才认为是刷新了
            if self._last_captcha_src and current_captcha_src != self._last_captcha_src:
                self.logger.info("检测到验证码已刷新。")
                return True
            else:
                self.logger.debug("验证码未刷新或无上次记录。")
                return False

        except Exception:
            # 如果查询页面特有元素不存在，说明可能已经跳转到结果页或其他页面
            self.logger.debug("页面不再是查询页面。")
            return False # 不在查询页面，则验证码未刷新（或已成功跳转）


    def enter_captcha_solution(self, captcha_solution):
        """
        输入验证码。
        """
        self.logger.info(f"输入验证码: {captcha_solution}")
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located(self.captcha_input_locator)
        )
        captcha_input = self.driver.find_element(*self.captcha_input_locator)
        captcha_input.send_keys(captcha_solution)

    def submit_query(self):
        """
        提交查询。
        """
        self.logger.info("提交查询。")
        WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable(self.submit_button_locator)
        )
        submit_button = self.driver.find_element(*self.submit_button_locator)
        submit_button.click()

    def wait_for_results(self):
        """
        等待查询结果显示。
        """
        self.logger.info("等待查询结果表格显示...")
        try:
            # 等待结果表格出现
            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located(self.result_table_locator)
            )  # 增加等待时间
            self.logger.info("查询结果表格已显示。")
            return True
        except Exception as e:
            self.logger.warning(
                f"等待查询结果表格超时或发生错误: {e}"
            )  # 使用 warning 级别，因为超时不一定是致命错误
            return False

    def parse_query_result(self, serial_number):
        """
        解析查询结果页面，提取各个字段的值。
        根据用户提供的HTML片段，结果在一个表格中。
        尝试通过查找包含当前序列号的td元素的父级tr来定位结果数据行。
        TODO: 根据锐捷官网实际页面结构，优化结果解析逻辑，使其更鲁棒，例如通过查找列标题定位数据。
        """
        results = {}
        self.logger.info(f"解析序列号 '{serial_number}' 的查询结果...")
        try:
            # 找到结果表格
            # TODO: 根据锐捷官网实际表格的 class 或 ID 调整 self.result_table_locator
            result_table = self.driver.find_element(*self.result_table_locator)
            self.logger.debug("找到结果表格。")

            # 找到包含当前序列号的td元素
            serial_number_cell_locator = (By.XPATH, f".//td[text()='{serial_number}']")
            try:
                # 增加等待时间，确保序列号单元格加载
                serial_number_cell = WebDriverWait(
                    result_table, 15
                ).until(  # 增加等待时间
                    EC.presence_of_element_located(serial_number_cell_locator)
                )
                self.logger.debug(f"找到序列号 '{serial_number}' 对应的单元格。")
                # 找到包含该td元素的父级tr（结果数据行）
                data_row = serial_number_cell.find_element(By.XPATH, "./ancestor::tr")
                data_cells = data_row.find_elements(By.TAG_NAME, "td")
                self.logger.debug(f"找到数据行，包含 {len(data_cells)} 个单元格。")
            except Exception as e:
                self.logger.warning(
                    f"未找到序列号 '{serial_number}' 对应的数据行或单元格: {e}"
                )
                # 如果未找到特定序列号的行，可能是序列号无效或查询失败，尝试查找错误信息
                error_message = self._check_error_message()
                if error_message:
                    self.logger.warning(f"页面显示错误信息: {error_message}")
                    results["查询状态"] = f"查询失败: {error_message}"
                    return results
                else:
                    self.logger.warning("未找到结果数据行或错误信息。")
                    return None  # 未找到结果数据或错误信息

            # 根据config.ini中的ResultColumns映射关系提取数据
            # --- 改进：动态解析表头以确定列索引，增加对不同表格结构的兼容性 ---
            header_cells = []
            try:
                # 优先尝试查找 thead 中的 th
                header_cells = result_table.find_elements(By.CSS_SELECTOR, "thead th")
                if not header_cells:
                    # 如果 thead 中没有 th，尝试查找 tbody 中第一行的 th (有些表格结构如此)
                    self.logger.debug("未在 thead 中找到 th，尝试查找 tbody tr:first-child th")
                    header_cells = result_table.find_elements(By.CSS_SELECTOR, "tbody tr:first-child th")
                if not header_cells:
                    # 如果还没有找到 th，尝试直接查找表格内所有的 th
                    self.logger.debug("未在 tbody tr:first-child 中找到 th，尝试查找 table th")
                    header_cells = result_table.find_elements(By.TAG_NAME, "th")
                if not header_cells:
                    # 最后尝试，假设第一行是表头，并且使用 td
                    self.logger.debug("未找到 th 元素，尝试假设 tbody tr:first-child td 为表头")
                    first_row_cells = result_table.find_elements(By.CSS_SELECTOR, "tbody tr:first-child td")
                    # 检查第一行单元格的数量是否与预期列数大致相符，避免误判
                    # -1 因为 config 中包含内部的 "查询状态" 列
                    if len(first_row_cells) >= len(self.config["ResultColumns"]) - 1:
                         header_cells = first_row_cells
                         self.logger.warning("未找到明确的表头 (th)，假设第一行 (td) 为表头。")
                    else:
                         self.logger.error(f"无法在结果表格中找到表头元素。第一行 td 数量 ({len(first_row_cells)}) 与预期列数不符。")
                         results["查询状态"] = "结果表格结构错误（无法定位表头）"
                         return results
            except Exception as header_ex:
                self.logger.error(f"查找表头时发生异常: {header_ex}", exc_info=True)
                results["查询状态"] = "结果表格结构错误（查找表头异常）"
                return results

            # 检查是否成功找到 header_cells
            if not header_cells:
                self.logger.error("最终未能定位到结果表格的表头元素。")
                results["查询状态"] = "结果表格结构错误（无法定位表头）"
                return results

            header_map = {cell.text.strip(): index for index, cell in enumerate(header_cells) if cell.text.strip()} # 过滤空表头
            self.logger.debug(f"解析到的表头映射: {header_map}")

            # 检查必要的列是否存在于表头中 (基于 header_map 的键)
            required_web_fields = list(self.config["ResultColumns"].values())
            missing_headers = [field for field in required_web_fields if field not in header_map and field != "查询状态"] # 查询状态是内部添加的
            if missing_headers:
                self.logger.error(f"结果表格缺少必要的表头: {missing_headers}")
                results["查询状态"] = "结果表格结构错误（缺少表头）"
                return results # 返回错误状态

            # 根据 config.ini 中的 ResultColumns 映射关系和 header_map 提取数据
            for excel_col, web_field in self.config["ResultColumns"].items():
                if web_field == "查询状态": # 跳过内部状态字段
                    continue

                if web_field in header_map:
                    col_index = header_map[web_field]
                    if col_index < len(data_cells):
                        cell_text = data_cells[col_index].text.strip()
                        # 特殊处理“保修状态”列
                        if web_field == "保修状态":
                            if not cell_text: # 文本为空时尝试获取子元素
                                try:
                                    child_elements = data_cells[col_index].find_elements(By.XPATH, ".//*")
                                    child_text = " ".join([elem.text.strip() for elem in child_elements if elem.text.strip()])
                                    cell_text = child_text if child_text else data_cells[col_index].text.strip()
                                    self.logger.debug(f"保修状态单元格文本为空，尝试获取子元素文本: '{cell_text}'")
                                except Exception as child_e:
                                    self.logger.warning(f"获取保修状态子元素文本时发生错误: {child_e}")
                                    cell_text = data_cells[col_index].text.strip() # 回退

                        results[excel_col] = cell_text
                        self.logger.debug(f"提取字段 '{web_field}' (列 {col_index}) -> Excel 列 '{excel_col}': '{cell_text}'")
                    else:
                        self.logger.warning(f"警告：数据行单元格数量 ({len(data_cells)}) 少于表头 '{web_field}' 的索引 ({col_index})。")
                        results[excel_col] = None # 数据缺失
                else:
                    # 这个分支理论上不应该执行，因为前面检查了 missing_headers
                    self.logger.warning(f"警告：config.ini 中的网页字段 '{web_field}' 未在表头中找到。")
                    results[excel_col] = None # 字段未找到

            # 检查是否有错误或序列号无效的提示（在找到结果行后再次检查，以防万一）
            error_message = self._check_error_message()
            if error_message:
                self.logger.warning(f"页面显示错误信息: {error_message}")
                results["查询状态"] = f"查询失败: {error_message}"
                # 如果找到了错误信息，即使提取了部分数据，也标记为失败
                return results

            self.logger.info("查询结果解析完成。")
            return results

        except Exception as e:
            self.logger.error(f"解析查询结果时发生错误: {e}", exc_info=True)
            return None  # 解析失败

    def _check_error_message(self):
        """
        检查页面上是否存在错误信息。
        !!! 需要根据锐捷官网实际错误信息元素的HTML结构来编写 !!!
        TODO: 根据锐捷官网实际错误信息元素的HTML结构，实现准确的错误信息捕获。
        """
        # 尝试查找不同类型的错误信息
        error_locators = {
            "验证码错误": self.captcha_error_locator,
            "序列号无效或未找到产品": self.sn_not_found_locator,
            # 可以添加更多错误类型和对应的定位器
        }

        for error_type, locator in error_locators.items():
            try:
                # 使用非常短的等待时间，因为错误信息通常会立即显示
                error_element = WebDriverWait(self.driver, 0.5).until(
                    EC.visibility_of_element_located(locator)
                )
                # error_element = self.driver.find_element(*locator) # 不等待的版本
                if error_element.is_displayed():
                    error_text = error_element.text.strip()
                    # 可以选择返回预定义的错误类型或实际的错误文本
                    self.logger.debug(f"检测到页面错误信息 ({error_type}): {error_text}")
                    return error_type # 返回标准化的错误类型
                    # return error_text # 或者返回原始文本
            except Exception:
                continue # 未找到当前类型的错误，继续检查下一种

        # 如果以上定位器都未找到，可以尝试查找通用的错误容器（如果定义了）
        # try:
        #     if hasattr(self, 'error_container_locator'):
        #         error_container = WebDriverWait(self.driver, 0.5).until(
        #             EC.visibility_of_element_located(self.error_container_locator)
        #         )
        #         if error_container.is_displayed():
        #             error_text = error_container.text.strip()
        #             if error_text: # 确保容器内有文本
        #                 self.logger.debug(f"检测到通用错误容器信息: {error_text}")
        #                 return f"查询失败: {error_text}" # 返回通用错误
        # except Exception:
        #     pass

        self.logger.debug("未检测到明确的页面错误信息。")
        return None # 未找到错误信息
