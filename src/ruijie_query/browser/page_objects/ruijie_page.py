import logging  # 导入 logging 模块
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from typing import List, Tuple, Optional, Union, Dict, Any, Sequence
import re


class LocatorManager:
    """
    智能定位器管理器 - 实现多定位器fallback机制
    解决网页元素定位不稳定的问题
    """
    def __init__(self, logger):
        self.logger = logger
        self.locator_cache = {}  # 缓存成功的定位器
        self.failed_locators = set()  # 记录失败的定位器

    def find_element_with_fallback(self, driver, locators: Sequence[Tuple[str, str]], timeout: int = 10) -> Optional[Any]:
        """
        使用多个定位器尝试查找元素，支持fallback机制

        Args:
            driver: WebDriver实例
            locators: 定位器列表，格式为 [("css selector", "selector"), ...]
            timeout: 等待超时时间

        Returns:
            找到的元素或None
        """
        if not locators:
            return None

        # 尝试每个定位器
        for i, (by, selector) in enumerate(locators):
            locator_key = f"{by}_{selector}"

            # 跳过之前失败的定位器
            if locator_key in self.failed_locators:
                self.logger.debug(f"跳过之前失败的定位器: {selector}")
                continue

            try:
                self.logger.debug(f"尝试定位器 {i+1}/{len(locators)}: {by} -> {selector}")
                element = WebDriverWait(driver, timeout).until(
                    EC.presence_of_element_located((by, selector))
                )

                # 成功找到，记录到缓存
                self.locator_cache[locator_key] = element
                if locator_key in self.failed_locators:
                    self.failed_locators.remove(locator_key)

                self.logger.debug(f"成功找到元素，使用定位器: {selector}")
                return element

            except Exception as e:
                self.logger.debug(f"定位器失败 {selector}: {e}")
                self.failed_locators.add(locator_key)
                continue

        self.logger.warning(f"所有定位器都失败了: {[loc[1] for loc in locators]}")
        return None

    def find_elements_with_fallback(self, driver, locators: Sequence[Tuple[str, str]], timeout: int = 10) -> List[Any]:
        """
        使用多个定位器尝试查找多个元素
        """
        elements = []
        for by, selector in locators:
            try:
                found_elements = driver.find_elements(by, selector)
                if found_elements:
                    elements.extend(found_elements)
                    self.logger.debug(f"找到 {len(found_elements)} 个元素，使用定位器: {selector}")
                    break
            except Exception as e:
                self.logger.debug(f"定位器失败 {selector}: {e}")
                continue

        return elements

    def clear_failed_locators(self):
        """清除失败定位器记录，重新尝试"""
        self.failed_locators.clear()
        self.logger.info("已清除失败定位器记录")


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

        # 初始化智能定位器管理器
        self.locator_manager = LocatorManager(self.logger)

        # 多定位器配置 - 支持fallback机制
        # 1. 序列号输入框定位器
        self.serial_input_locators = [
            ("css selector", 'textarea[name="serialNumber"]'),
            ("css selector", 'textarea[name="sn"]'),
            ("css selector", '#serialNumber'),
            ("xpath", "//textarea[contains(@name, 'serial')]"),
            ("css selector", '.serial-input'),
            ("tag name", 'textarea'),  # 最后的fallback
        ]

        # 2. 验证码图片定位器
        self.captcha_img_locators = [
            ("css selector", "img.verification-code"),
            ("css selector", "img.captcha"),
            ("css selector", "#captcha-img"),
            ("xpath", "//img[contains(@src, 'captcha') or contains(@src, 'code')]"),
            ("css selector", ".verification-code img"),
            ("tag name", "img"),  # 最后的fallback，需要后续过滤
        ]

        # 3. 验证码输入框定位器
        self.captcha_input_locators = [
            ("css selector", 'input[name="imageCode"]'),
            ("css selector", 'input[name="captcha"]'),
            ("css selector", '#captcha'),
            ("xpath", "//input[contains(@name, 'captcha') or contains(@name, 'code')]"),
            ("css selector", '.captcha-input'),
        ]

        # 4. 提交按钮定位器
        self.submit_button_locators = [
            ("css selector", "button.xulie-bottom-left"),
            ("css selector", "button[type='submit']"),
            ("css selector", ".submit-btn"),
            ("xpath", "//button[contains(text(), '查询') or contains(text(), '提交')]"),
            ("css selector", "#submit"),
            ("css selector", "input[type='submit']"),
        ]

        # 5. 结果表格定位器 (最重要的改进)
        self.result_table_locators = [
            ("css selector", "div.chaxun-content-center table"),
            ("css selector", ".result-table"),
            ("css selector", ".query-result table"),
            ("css selector", "table.result"),
            ("css selector", "#result-table"),
            ("xpath", "//table[contains(@class, 'result') or contains(@class, 'data')]"),
            ("xpath", "//div[contains(@class, 'content')]//table"),
            ("css selector", "table"),  # 最后的fallback
        ]

        # 6. 错误信息定位器集合
        self.error_locators = {
            "验证码错误": [
                ("xpath", "//*[contains(text(), '验证码错误')]"),
                ("xpath", "//*[contains(text(), '验证码不正确')]"),
                ("xpath", "//*[contains(text(), 'code error')]"),
                ("css selector", ".captcha-error"),
                ("css selector", ".error-message"),
            ],
            "序列号无效": [
                ("xpath", "//*[contains(text(), '未找到您查询的产品')]"),
                ("xpath", "//*[contains(text(), '序列号无效')]"),
                ("xpath", "//*[contains(text(), '序列号不存在')]"),
                ("xpath", "//*[contains(text(), '产品不存在')]"),
                ("css selector", ".sn-not-found"),
            ],
            "系统错误": [
                ("xpath", "//*[contains(text(), '系统错误')]"),
                ("xpath", "//*[contains(text(), '服务器错误')]"),
                ("xpath", "//*[contains(text(), '网络错误')]"),
                ("xpath", "//*[contains(text(), '系统繁忙')]"),
                ("css selector", ".system-error"),
            ],
            "网络超时": [
                ("xpath", "//*[contains(text(), '超时')]"),
                ("xpath", "//*[contains(text(), 'timeout')]"),
                ("xpath", "//*[contains(text(), '请求超时')]"),
            ]
        }

        # 页面结构检测结果缓存
        self._page_structure_cache = {}

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
        serial_input = self.locator_manager.find_element_with_fallback(
            self.driver, self.serial_input_locators, timeout=10
        )

        if serial_input:
            serial_input.clear()
            serial_input.send_keys(serial_number)
            self.logger.debug("序列号输入成功")
        else:
            self.logger.error("无法找到序列号输入框，所有定位器都失败了")
            raise Exception("无法定位序列号输入框")

    def get_captcha_image_data(self):
        """
        获取验证码图片数据。
        """
        self.logger.info("获取验证码图片数据...")
        captcha_img = self.locator_manager.find_element_with_fallback(
            self.driver, self.captcha_img_locators, timeout=10
        )

        if not captcha_img:
            self.logger.error("无法找到验证码图片，所有定位器都失败了")
            return None

        # 验证图片是否有效（高度大于0）
        try:
            WebDriverWait(self.driver, 5).until(
                lambda driver: captcha_img.size["height"] > 0 and captcha_img.size["width"] > 0
            )
        except Exception as e:
            self.logger.warning(f"验证码图片尺寸异常: {e}")
            return None

        # 如果是通用的img标签，需要进一步验证是否是验证码图片
        if captcha_img.tag_name == "img":
            src = captcha_img.get_attribute("src") or ""
            # 检查src是否包含验证码相关关键词
            if not any(keyword in src.lower() for keyword in ['captcha', 'code', 'verify', 'valid']):
                # 检查alt或其他属性
                alt = captcha_img.get_attribute("alt") or ""
                if not any(keyword in alt.lower() for keyword in ['captcha', 'code', 'verify', 'valid']):
                    self.logger.warning(f"找到的图片可能不是验证码图片: src={src}, alt={alt}")
                    # 仍然返回，因为可能是动态生成的验证码

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
            # 使用多定位器找到验证码图片
            captcha_img = self.locator_manager.find_element_with_fallback(
                self.driver, self.captcha_img_locators, timeout=10
            )

            if not captcha_img:
                self.logger.error("无法找到验证码图片进行刷新")
                return False

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
            # 检查查询页面特有元素是否存在
            serial_input = self.locator_manager.find_element_with_fallback(
                self.driver, self.serial_input_locators, timeout=2
            )
            captcha_input = self.locator_manager.find_element_with_fallback(
                self.driver, self.captcha_input_locators, timeout=2
            )

            if not serial_input or not captcha_input:
                self.logger.debug("页面不再是查询页面。")
                return False

            self.logger.debug("页面仍为查询页面。")

            # 检查验证码图片是否存在且 src 属性与上次记录的不同
            current_captcha_img = self.locator_manager.find_element_with_fallback(
                self.driver, self.captcha_img_locators, timeout=2
            )

            if not current_captcha_img:
                self.logger.debug("未找到验证码图片。")
                return False

            current_captcha_src = current_captcha_img.get_attribute("src")
            self.logger.debug(f"当前验证码 src: {current_captcha_src}, 上次记录 src: {self._last_captcha_src}")

            # 只有当有上次记录的 src 且当前 src 不同时，才认为是刷新了
            if self._last_captcha_src and current_captcha_src != self._last_captcha_src:
                self.logger.info("检测到验证码已刷新。")
                return True
            else:
                self.logger.debug("验证码未刷新或无上次记录。")
                return False

        except Exception as e:
            self.logger.debug(f"检查验证码刷新状态时出错: {e}")
            # 如果查询页面特有元素不存在，说明可能已经跳转到结果页或其他页面
            return False


    def enter_captcha_solution(self, captcha_solution):
        """
        输入验证码。
        """
        self.logger.info(f"输入验证码: {captcha_solution}")
        captcha_input = self.locator_manager.find_element_with_fallback(
            self.driver, self.captcha_input_locators, timeout=10
        )

        if captcha_input:
            captcha_input.clear()
            captcha_input.send_keys(captcha_solution)
            self.logger.debug("验证码输入成功")
        else:
            self.logger.error("无法找到验证码输入框，所有定位器都失败了")
            raise Exception("无法定位验证码输入框")

    def submit_query(self):
        """
        提交查询。
        """
        self.logger.info("提交查询。")
        submit_button = self.locator_manager.find_element_with_fallback(
            self.driver, self.submit_button_locators, timeout=10
        )

        if submit_button:
            # 确保按钮可点击
            WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable(submit_button)
            )
            submit_button.click()
            self.logger.debug("查询提交成功")
        else:
            self.logger.error("无法找到提交按钮，所有定位器都失败了")
            raise Exception("无法定位提交按钮")

    def wait_for_results(self):
        """
        等待查询结果显示。
        """
        self.logger.info("等待查询结果表格显示...")
        try:
            # 使用多定位器等待结果表格出现
            result_table = self.locator_manager.find_element_with_fallback(
                self.driver, self.result_table_locators, timeout=30
            )

            if result_table:
                self.logger.info("查询结果表格已显示。")
                return True
            else:
                self.logger.warning("无法找到结果表格，所有定位器都失败了")
                return False
        except Exception as e:
            self.logger.warning(
                f"等待查询结果表格超时或发生错误: {e}"
            )
            return False

    def parse_query_result(self, serial_number):
        """
        解析查询结果页面，提取各个字段的值。
        智能适配不同的表格结构，支持动态表头解析和多定位器fallback。
        """
        results = {}
        self.logger.info(f"解析序列号 '{serial_number}' 的查询结果...")

        try:
            # 1. 使用多定位器找到结果表格
            result_table = self.locator_manager.find_element_with_fallback(
                self.driver, self.result_table_locators, timeout=15
            )

            if not result_table:
                self.logger.error("无法找到结果表格，所有定位器都失败了")
                results["查询状态"] = "结果表格定位失败"
                return results

            self.logger.debug("找到结果表格。")

            # 2. 智能查找包含当前序列号的数据行
            data_row = None
            data_cells = []

            # 多种策略查找数据行
            row_search_strategies = [
                # 策略1：精确文本匹配
                f".//td[text()='{serial_number}']",
                # 策略2：包含文本匹配
                f".//td[contains(text(), '{serial_number}')]",
                # 策略3：去除空格后匹配
                f".//td[normalize-space()='{serial_number}']",
                # 策略4：基于序列号模式匹配（适用于序列号有固定格式的情况）
                f".//td[matches(text(), '^{re.escape(serial_number)}$')]"
            ]

            for strategy in row_search_strategies:
                try:
                    serial_number_cell = result_table.find_element(By.XPATH, strategy)
                    if serial_number_cell:
                        data_row = serial_number_cell.find_element(By.XPATH, "./ancestor::tr")
                        data_cells = data_row.find_elements(By.TAG_NAME, "td")
                        self.logger.debug(f"使用策略 '{strategy}' 找到序列号单元格，数据行包含 {len(data_cells)} 个单元格。")
                        break
                except Exception:
                    continue

            if not data_row or not data_cells:
                self.logger.warning(f"未找到序列号 '{serial_number}' 对应的数据行")
                # 尝试查找错误信息
                error_message = self._check_error_message()
                if error_message:
                    self.logger.warning(f"页面显示错误信息: {error_message}")
                    results["查询状态"] = f"查询失败: {error_message}"
                    return results
                else:
                    results["查询状态"] = "未找到序列号对应的数据行"
                    return results

            # 3. 智能表头解析 - 支持多种表格结构
            header_map = self._parse_table_headers(result_table)
            if not header_map:
                self.logger.error("无法解析表格表头")
                results["查询状态"] = "表格结构错误（无法解析表头）"
                return results

            # 4. 动态字段映射和数据提取
            results = self._extract_data_with_mapping(data_cells, header_map, results)

            # 5. 最终错误检查
            error_message = self._check_error_message()
            if error_message:
                self.logger.warning(f"页面显示错误信息: {error_message}")
                results["查询状态"] = f"查询失败: {error_message}"
                return results

            self.logger.info("查询结果解析完成。")
            return results

        except Exception as e:
            self.logger.error(f"解析查询结果时发生错误: {e}", exc_info=True)
            results["查询状态"] = f"解析异常: {e}"
            return results

    def _parse_table_headers(self, result_table) -> Dict[str, int]:
        """
        智能解析表格表头，支持多种HTML结构
        """
        header_map = {}

        # 策略1: 查找 thead 中的 th
        try:
            thead_ths = result_table.find_elements(By.CSS_SELECTOR, "thead th")
            if thead_ths:
                header_map = {cell.text.strip(): index for index, cell in enumerate(thead_ths) if cell.text.strip()}
                self.logger.debug(f"从 thead 解析到表头: {header_map}")
                return header_map
        except Exception as e:
            self.logger.debug(f"解析 thead 失败: {e}")

        # 策略2: 查找 tbody 中的第一行 th
        try:
            tbody_first_row_ths = result_table.find_elements(By.CSS_SELECTOR, "tbody tr:first-child th")
            if tbody_first_row_ths:
                header_map = {cell.text.strip(): index for index, cell in enumerate(tbody_first_row_ths) if cell.text.strip()}
                self.logger.debug(f"从 tbody 第一行 th 解析到表头: {header_map}")
                return header_map
        except Exception as e:
            self.logger.debug(f"解析 tbody 第一行 th 失败: {e}")

        # 策略3: 查找所有 th 元素
        try:
            all_ths = result_table.find_elements(By.TAG_NAME, "th")
            if all_ths:
                header_map = {cell.text.strip(): index for index, cell in enumerate(all_ths) if cell.text.strip()}
                self.logger.debug(f"从所有 th 解析到表头: {header_map}")
                return header_map
        except Exception as e:
            self.logger.debug(f"解析所有 th 失败: {e}")

        # 策略4: 假设第一行是表头（使用 td）
        try:
            first_row_tds = result_table.find_elements(By.CSS_SELECTOR, "tbody tr:first-child td")
            if first_row_tds and len(first_row_tds) >= len(self.config["ResultColumns"]) - 1:
                header_map = {cell.text.strip(): index for index, cell in enumerate(first_row_tds) if cell.text.strip()}
                self.logger.warning(f"假设第一行为表头，解析结果: {header_map}")
                return header_map
        except Exception as e:
            self.logger.debug(f"假设第一行为表头失败: {e}")

        # 策略5: 查找包含关键字的行作为表头
        try:
            header_keywords = ['型号', '设备类型', '保修', '服务', '序列号', '开始时间', '结束时间']
            for row in result_table.find_elements(By.CSS_SELECTOR, "tr"):
                cells = row.find_elements(By.TAG_NAME, "td")
                if cells:
                    cell_texts = [cell.text.strip() for cell in cells if cell.text.strip()]
                    # 如果这一行包含多个关键字，可能是表头
                    keyword_count = sum(1 for text in cell_texts if any(keyword in text for keyword in header_keywords))
                    if keyword_count >= 2:  # 至少包含2个关键字
                        header_map = {text: index for index, text in enumerate(cell_texts) if text}
                        self.logger.debug(f"基于关键字识别表头: {header_map}")
                        return header_map
        except Exception as e:
            self.logger.debug(f"基于关键字识别表头失败: {e}")

        return {}

    def _extract_data_with_mapping(self, data_cells, header_map, results):
        """
        根据表头映射提取数据
        """
        # 检查必要的列是否存在
        required_web_fields = list(self.config["ResultColumns"].values())
        missing_headers = [field for field in required_web_fields if field not in header_map and field != "查询状态"]

        if missing_headers:
            self.logger.warning(f"表格缺少以下字段: {missing_headers}")
            # 尝试模糊匹配
            header_map = self._fuzzy_match_headers(header_map, missing_headers)

        # 提取数据
        for excel_col, web_field in self.config["ResultColumns"].items():
            if web_field == "查询状态":
                continue

            if web_field in header_map:
                col_index = header_map[web_field]
                if col_index < len(data_cells):
                    cell_text = self._extract_cell_text(data_cells[col_index], web_field)
                    results[excel_col] = cell_text
                    self.logger.debug(f"提取字段 '{web_field}' (列 {col_index}) -> '{excel_col}': '{cell_text}'")
                else:
                    self.logger.warning(f"列索引 {col_index} 超出数据行范围")
                    results[excel_col] = None
            else:
                self.logger.warning(f"字段 '{web_field}' 未在表头中找到")
                results[excel_col] = None

        return results

    def _extract_cell_text(self, cell, field_name):
        """
        提取单元格文本，支持特殊情况处理
        """
        cell_text = cell.text.strip()

        # 特殊字段处理
        if field_name == "保修状态" and not cell_text:
            # 尝试获取子元素文本
            try:
                child_elements = cell.find_elements(By.XPATH, ".//*")
                child_text = " ".join([elem.text.strip() for elem in child_elements if elem.text.strip()])
                cell_text = child_text if child_text else cell_text
            except Exception as e:
                self.logger.debug(f"获取子元素文本失败: {e}")

        return cell_text

    def _fuzzy_match_headers(self, header_map, missing_headers):
        """
        模糊匹配表头字段
        """
        fuzzy_matches = {}

        for missing_field in missing_headers:
            # 简化匹配逻辑，查找包含关键词的表头
            for header_text, index in header_map.items():
                # 直接匹配
                if missing_field in header_text or header_text in missing_field:
                    fuzzy_matches[missing_field] = index
                    self.logger.info(f"模糊匹配: '{missing_field}' -> '{header_text}' (索引 {index})")
                    break

                # 关键词匹配
                field_keywords = missing_field.split()
                header_keywords = header_text.split()
                if any(keyword in header_text for keyword in field_keywords):
                    fuzzy_matches[missing_field] = index
                    self.logger.info(f"关键词匹配: '{missing_field}' -> '{header_text}' (索引 {index})")
                    break

        # 更新header_map
        header_map.update(fuzzy_matches)
        return header_map

    def _check_error_message(self):
        """
        检查页面上是否存在错误信息。
        使用多定位器fallback机制，支持多种错误类型和检测策略。
        """
        # 尝试查找不同类型的错误信息
        for error_type, locators in self.error_locators.items():
            try:
                # 使用多定位器查找错误信息
                error_element = self.locator_manager.find_element_with_fallback(
                    self.driver, locators, timeout=1  # 很短的等待时间
                )

                if error_element and error_element.is_displayed():
                    error_text = error_element.text.strip()
                    if error_text:  # 确保有实际文本内容
                        self.logger.debug(f"检测到页面错误信息 ({error_type}): {error_text}")
                        return error_type  # 返回标准化的错误类型
            except Exception as e:
                self.logger.debug(f"检查错误信息 '{error_type}' 时出错: {e}")
                continue  # 继续检查下一种错误类型

        # 额外策略：查找通用的错误容器
        general_error_locators = [
            ("css selector", ".error-message"),
            ("css selector", ".alert-error"),
            ("css selector", ".warning"),
            ("xpath", "//div[contains(@class, 'error')]"),
            ("xpath", "//div[contains(@class, 'alert')]"),
            ("xpath", "//span[contains(@class, 'error')]"),
            ("xpath", "//p[contains(@class, 'error')]"),
        ]

        try:
            general_error = self.locator_manager.find_element_with_fallback(
                self.driver, general_error_locators, timeout=1
            )

            if general_error and general_error.is_displayed():
                error_text = general_error.text.strip()
                if error_text and len(error_text) > 3:  # 确保错误信息不是太短
                    self.logger.debug(f"检测到通用错误信息: {error_text}")
                    return f"通用错误: {error_text[:100]}"  # 限制长度
        except Exception as e:
            self.logger.debug(f"检查通用错误信息时出错: {e}")

        # 策略：查找页面是否有明显的错误状态指示
        try:
            # 检查页面标题是否包含错误信息
            page_title = self.driver.title.lower()
            error_keywords = ['错误', 'error', '失败', 'failed', '无效', 'invalid']
            if any(keyword in page_title for keyword in error_keywords):
                self.logger.debug(f"页面标题可能包含错误: {self.driver.title}")
                return "页面标题异常"

            # 检查URL是否有错误参数
            current_url = self.driver.current_url
            if 'error' in current_url.lower() or 'failed' in current_url.lower():
                self.logger.debug(f"URL可能包含错误信息: {current_url}")
                return "URL包含错误参数"
        except Exception as e:
            self.logger.debug(f"检查页面状态时出错: {e}")

        self.logger.debug("未检测到明确的页面错误信息。")
        return None  # 未找到错误信息

    def reset_locator_cache(self):
        """
        重置定位器缓存和失败记录，用于处理页面结构变化
        """
        self.locator_manager.clear_failed_locators()
        self._page_structure_cache.clear()
        self.logger.info("已重置定位器缓存和页面结构缓存")

    def get_page_structure_info(self):
        """
        获取当前页面的结构信息，用于调试和优化定位器
        """
        structure_info = {}

        # 检查基本元素是否存在
        basic_elements = {
            'serial_input': self.serial_input_locators,
            'captcha_img': self.captcha_img_locators,
            'captcha_input': self.captcha_input_locators,
            'submit_button': self.submit_button_locators,
            'result_table': self.result_table_locators
        }

        for element_name, locators in basic_elements.items():
            working_locator = None
            for by, selector in locators:
                try:
                    element = self.driver.find_element(by, selector)
                    if element and element.is_displayed():
                        working_locator = (by, selector)
                        break
                except Exception:
                    continue
            structure_info[element_name] = working_locator

        return structure_info
