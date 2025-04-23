import logging
import time
import base64
import random

# 移除顶层 ddddocr 导入尝试

# 导入通用 AI API 客户端库
# 请根据您选择的 AI 服务 (Gemini, Grok, OpenAI 兼容等) 安装相应的库
# 例如: pip install google-generativeai (for Gemini)
# 例如: pip install openai (for OpenAI compatible)
genai = None
openai = None

# --- 验证码处理类 ---

class CaptchaSolver:
    def __init__(
        self,
        captcha_config, # 验证码设置 (primary_solver, enable_ddddocr, etc.)
        ai_settings, # 通用 AI 设置 (retry_attempts, retry_delay, rate_limit_delay)
        channels, # AI 渠道配置列表
        logger=None,
    ):
        self.captcha_config = captcha_config
        self.ai_settings = ai_settings
        self.channels = channels # AI 渠道
        self.logger = logger or logging.getLogger(__name__)

        # --- 初始化 ddddocr (如果启用且已安装) ---
        self.ocr = None
        self.ddddocr_enabled_internal = False # 内部状态，表示是否成功初始化

        # --- 初始化 ddddocr (如果启用) ---
        if self.captcha_config.get("enable_ddddocr", False):
            try:
                import ddddocr # 在需要时才尝试导入
                try:
                    # show_ad=False 避免广告信息打印到控制台
                    self.ocr = ddddocr.DdddOcr(show_ad=False)
                    self.ddddocr_enabled_internal = True
                    self.logger.info("DdddOcr 初始化成功。")
                except Exception as init_e: # 捕获初始化错误
                    self.logger.error(f"DdddOcr 初始化失败: {init_e}。将禁用 ddddocr。", exc_info=True)
                    self.ocr = None # 确保 ocr 为 None
                    self.ddddocr_enabled_internal = False
            except ImportError: # 捕获导入错误
                self.logger.warning("配置启用了 ddddocr，但 'ddddocr' 库未安装或导入失败。请运行 'pip install ddddocr'。将禁用 ddddocr。")
                self.ddddocr_enabled_internal = False # 确保内部状态为 False
        else:
             self.logger.info("配置中禁用了 ddddocr。")


        # --- 尝试导入 AI 库 (只需导入一次) ---
        global genai, openai
        try:
            import google.generativeai as genai
            self.logger.info("成功导入 google-generativeai 库。")
        except ImportError:
            self.logger.warning(
                "未安装 'google-generativeai' 库。配置使用 Gemini 的渠道将无法工作。"
                "请运行 'pip install google-generativeai'"
            )
            genai = None # 确保 genai 为 None

        try:
            import openai
            self.logger.info("成功导入 openai 库。")
        except ImportError:
            self.logger.warning(
                "未安装 'openai' 库。配置使用 OpenAI, Grok 或 OpenAI 兼容 API 的渠道将无法工作。"
                "请运行 'pip install openai'"
            )
            openai = None # 确保 openai 为 None


    def _solve_with_ddddocr(self, captcha_image_data):
        """使用 ddddocr 识别验证码"""
        if not self.ddddocr_enabled_internal or not self.ocr:
            self.logger.warning("Ddddocr 未启用或未成功初始化，跳过识别。")
            return None

        max_attempts = self.captcha_config.get("ddddocr_max_attempts", 3)
        self.logger.info(f"尝试使用 ddddocr 识别验证码 (最多 {max_attempts} 次)...")

        for attempt in range(max_attempts):
            try:
                self.logger.info(f"Ddddocr: 尝试 {attempt + 1}/{max_attempts}...")
                result = self.ocr.classification(captcha_image_data)
                # ddddocr 识别结果通常比较干净，但也可能需要基本清理
                cleaned_result = ''.join(filter(str.isalnum, result)).lower() # 转小写并去除非字母数字
                if cleaned_result: # 确保结果不为空
                    self.logger.info(f"Ddddocr 识别成功: {cleaned_result} (原始: {result})")
                    return cleaned_result
                else:
                    self.logger.warning(f"Ddddocr 识别结果为空或无效 (尝试 {attempt + 1}/{max_attempts})。原始: {result}")

            except Exception as e:
                self.logger.error(f"Ddddocr 识别时发生错误 (尝试 {attempt + 1}/{max_attempts}): {e}")
                # ddddocr 通常不需要重试间隔，如果一次失败很可能一直失败

            # 如果需要，可以在这里添加短暂的延时，但通常 ddddocr 很快
            # time.sleep(0.1)

        self.logger.error(f"Ddddocr 在 {max_attempts} 次尝试后未能识别验证码。")
        return None


    def _solve_with_ai(self, captcha_image_data):
        """使用配置的 AI API 解决验证码，按渠道顺序尝试。"""
        if not self.channels:
            self.logger.warning("未配置任何 AI 渠道，跳过 AI 识别。")
            return None

        # 将图片数据编码为 base64 (一些 API 可能需要)
        base64_image = base64.b64encode(captcha_image_data).decode("utf-8")

        for channel_index, channel_config in enumerate(self.channels):
            api_type = channel_config.get("api_type", "none").strip().lower()
            api_key = channel_config.get("api_key", None)
            model_name = channel_config.get("model_name", None)
            base_url = channel_config.get("base_url", None)

            channel_name = f"AI Channel {channel_index + 1} ({api_type.upper()})"
            if model_name:
                 channel_name += f" - {model_name}"
            if base_url:
                 channel_name += f" @ {base_url}"

            self.logger.info(f"尝试使用 {channel_name} 识别验证码...")

            if api_type == "none":
                self.logger.info(f"{channel_name} 配置为 'None'，跳过此渠道。")
                continue

            if not api_key and api_type != "none":
                 self.logger.warning(f"{channel_name} 未配置 API Key，跳过此渠道。")
                 continue

            # --- 检查库是否导入 ---
            if api_type == "gemini" and genai is None:
                 self.logger.warning(f"{channel_name} 需要 google-generativeai 库，但未导入。跳过此渠道。")
                 continue
            elif api_type in ["openai", "grok"] and openai is None:
                 self.logger.warning(f"{channel_name} 需要 openai 库，但未导入。跳过此渠道。")
                 continue
            elif api_type not in ["gemini", "openai", "grok", "none"]:
                 self.logger.warning(f"{channel_name} 使用不支持的 AI 服务类型 '{api_type}'。跳过此渠道。")
                 continue

            # --- 尝试当前渠道，带重试 ---
            ai_retry_attempts = self.ai_settings.get("retry_attempts", 3)
            for attempt in range(ai_retry_attempts):
                try:
                    self.logger.info(f"{channel_name}: 尝试 {attempt + 1}/{ai_retry_attempts}...")
                    captcha_solution = None

                    if api_type == "gemini":
                        try:
                            genai.configure(api_key=api_key)
                            model = genai.GenerativeModel(model_name or "gemini-pro-vision")
                            image_part = {"mime_type": "image/png", "data": base64_image}
                            prompt = "识别这张图片中的验证码文本，只返回验证码文本，不要包含其他任何内容。"
                            response = model.generate_content([prompt, image_part])
                            captcha_solution = self._parse_ai_response(response)
                        except Exception as api_e:
                            self.logger.error(f"{channel_name}: 调用 Gemini API 时发生错误: {api_e}")
                            raise api_e

                    elif api_type in ["openai", "grok"]:
                        try:
                            client_params = {"api_key": api_key}
                            if base_url:
                                client_params["base_url"] = base_url
                                self.logger.info(f"{channel_name}: 使用 Base URL: {base_url}")
                            client = openai.OpenAI(**client_params)
                            response = client.chat.completions.create(
                                model=model_name or "gpt-4o",
                                messages=[
                                    {
                                        "role": "user",
                                        "content": [
                                            {"type": "text", "text": "识别这张图片中的验证码文本，只返回验证码文本，不要包含其他任何内容。"},
                                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}},
                                        ],
                                    }
                                ],
                                max_tokens=50,
                            )
                            captcha_solution = self._parse_ai_response(response)
                        except openai.RateLimitError as rate_limit_e:
                            self.logger.warning(f"{channel_name}: 检测到频率限制错误 (429): {rate_limit_e}")
                            wait_delay = self.ai_settings.get('rate_limit_delay', 30)
                            self.logger.info(f"{channel_name}: 等待 {wait_delay:.2f} 秒后重试...")
                            time.sleep(wait_delay)
                            raise rate_limit_e
                        except Exception as api_e:
                            self.logger.error(f"{channel_name}: 调用 {api_type.upper()} API 时发生错误: {api_e}")
                            error_message = str(api_e).lower()
                            if "unsupported input type" in error_message or (model_name and "vision" not in model_name.lower() and "image" in error_message):
                                self.logger.error(f"{channel_name}: 配置的模型 '{model_name}' 可能不支持图像输入。请检查 config.ini 并更换支持视觉的模型。")
                                break # 尝试下一个渠道
                            raise api_e

                    if captcha_solution:
                        self.logger.info(f"{channel_name}: AI 识别成功: {captcha_solution}")
                        return captcha_solution

                except Exception as e:
                    self.logger.error(f"{channel_name}: AI 识别验证码时发生错误 (尝试 {attempt + 1}/{ai_retry_attempts}): {e}")
                    if attempt < ai_retry_attempts - 1:
                        wait_time = self.ai_settings.get("retry_delay", 5) * (2**attempt) + random.uniform(0, 1)
                        self.logger.info(f"{channel_name}: 等待 {wait_time:.2f} 秒后重试...")
                        time.sleep(wait_time)
                    else:
                        self.logger.error(f"{channel_name}: 达到最大重试次数，此渠道识别失败。")
                        # 继续尝试下一个 AI 渠道

        self.logger.error("所有配置的 AI 渠道都未能成功识别验证码。")
        return None


    def solve_captcha(self, captcha_image_data):
        """
        根据配置策略识别验证码 (ddddocr 或 AI)。
        """
        primary_solver_type = self.captcha_config.get("primary_solver", "ddddocr")
        enable_ddddocr = self.captcha_config.get("enable_ddddocr", False) and self.ddddocr_enabled_internal
        enable_ai = self.captcha_config.get("enable_ai", False)

        primary_solver_func = None
        secondary_solver_func = None
        primary_solver_name = ""
        secondary_solver_name = ""

        if primary_solver_type == "ddddocr":
            primary_solver_func = self._solve_with_ddddocr
            primary_solver_name = "Ddddocr"
            secondary_solver_func = self._solve_with_ai
            secondary_solver_name = "AI"
            primary_enabled = enable_ddddocr
            secondary_enabled = enable_ai
        elif primary_solver_type == "ai":
            primary_solver_func = self._solve_with_ai
            primary_solver_name = "AI"
            secondary_solver_func = self._solve_with_ddddocr
            secondary_solver_name = "Ddddocr"
            primary_enabled = enable_ai
            secondary_enabled = enable_ddddocr
        else:
            self.logger.error(f"配置错误：未知的 captcha_primary_solver 类型 '{primary_solver_type}'。请配置为 'ddddocr' 或 'ai'。")
            # 默认尝试 ddddocr -> AI
            primary_solver_func = self._solve_with_ddddocr
            primary_solver_name = "Ddddocr (默认)"
            secondary_solver_func = self._solve_with_ai
            secondary_solver_name = "AI (默认)"
            primary_enabled = enable_ddddocr
            secondary_enabled = enable_ai


        # --- 尝试主要识别器 ---
        if primary_enabled:
            self.logger.info(f"尝试使用主要识别器: {primary_solver_name}")
            result = primary_solver_func(captcha_image_data)
            if result:
                return result
            else:
                self.logger.warning(f"主要识别器 {primary_solver_name} 未能识别验证码。")
        else:
            self.logger.info(f"主要识别器 {primary_solver_name} 未启用或初始化失败，跳过。")

        # --- 尝试次要识别器 ---
        if secondary_enabled:
            self.logger.info(f"尝试使用次要识别器: {secondary_solver_name}")
            result = secondary_solver_func(captcha_image_data)
            if result:
                return result
            else:
                self.logger.warning(f"次要识别器 {secondary_solver_name} 未能识别验证码。")
        else:
             self.logger.info(f"次要识别器 {secondary_solver_name} 未启用或初始化失败，跳过。")

        # --- 如果都失败 ---
        self.logger.error("所有启用的验证码识别器都未能成功识别验证码。")
        return None


    def test_channels_availability(self):
        """
        测试配置的 AI 渠道是否可用，并返回可用的渠道列表。
        (此方法仅测试 AI 渠道)
        """
        self.logger.info("\n--- 开始测试 AI 渠道可用性 ---")
        available_channels = []

        if not self.channels:
            self.logger.warning("config.ini 中未配置任何 AI 渠道进行测试。")
            return []

        for channel_index, channel_config in enumerate(self.channels):
            api_type = channel_config.get("api_type", "none").strip().lower()
            api_key = channel_config.get("api_key", None)
            model_name = channel_config.get("model_name", None)
            base_url = channel_config.get("base_url", None)

            channel_name = f"Channel {channel_index + 1} ({api_type.upper()})"
            if model_name:
                 channel_name += f" - {model_name}"
            if base_url:
                 channel_name += f" @ {base_url}"

            self.logger.info(f"测试 {channel_name}...")

            if api_type == "none":
                self.logger.info(f"{channel_name} 配置为 'None'，跳过测试。")
                continue

            if not api_key and api_type != "none":
                 self.logger.warning(f"{channel_name} 未配置 API Key，测试失败。")
                 continue

            # --- 检查库是否导入 ---
            if api_type == "gemini" and genai is None:
                 self.logger.warning(f"{channel_name} 需要 google-generativeai 库，但未导入。测试失败。")
                 continue
            elif api_type in ["openai", "grok"] and openai is None:
                 self.logger.warning(f"{channel_name} 需要 openai 库，但未导入。测试失败。")
                 continue
            elif api_type not in ["gemini", "openai", "grok", "none"]:
                 self.logger.warning(f"{channel_name} 使用不支持的 AI 服务类型 '{api_type}'。测试失败。")
                 continue

            # --- 尝试进行一个简单的 API 调用进行测试 ---
            try:
                if api_type == "gemini":
                    if genai:
                        genai.configure(api_key=api_key)
                        # 尝试一个简单的文本生成，验证API和模型可用性
                        # 优先使用渠道配置的模型，如果未配置则使用通用模型测试
                        test_model_name = model_name if model_name else "gemini-pro"
                        try:
                            model = genai.GenerativeModel(test_model_name)
                            response = model.generate_content("Hello", stream=False)
                            # 检查是否有有效的响应部分
                            if response and hasattr(response, 'text') and response.text:
                                 self.logger.info(f"{channel_name}: 测试成功。")
                                 available_channels.append(channel_config)
                            else:
                                 # 尝试检查是否有候选内容（某些API可能返回candidates）
                                 if response and hasattr(response, 'candidates') and response.candidates:
                                     self.logger.info(f"{channel_name}: 测试成功 (通过候选内容检查)。")
                                     available_channels.append(channel_config)
                                 else:
                                     self.logger.warning(f"{channel_name}: 测试失败 - 无法获取有效响应。响应: {response}")
                        except Exception as test_e:
                             self.logger.warning(f"{channel_name}: 使用模型 '{test_model_name}' 测试失败: {test_e}")

                elif api_type in ["openai", "grok"]:
                    if openai:
                        # 获取 AI 渠道测试超时时间，如果未配置则使用默认值 60 秒
                        test_timeout = self.ai_settings.get("ai_test_timeout", 60)
                        client_params = {"api_key": api_key, "timeout": test_timeout} # 使用可配置的超时设置
                        if base_url:
                            client_params["base_url"] = base_url
                        client = openai.OpenAI(**client_params)
                        # 尝试一个简单的文本生成请求
                        # 优先使用渠道配置的模型，如果未配置则使用通用模型测试
                        test_model_name = model_name if model_name else "gpt-3.5-turbo"
                        try:
                            response = client.chat.completions.create(
                                model=test_model_name,
                                messages=[{"role": "user", "content": "Hello"}],
                                max_tokens=10
                            )
                            if response and response.choices and response.choices[0].message.content:
                                 self.logger.info(f"{channel_name}: 测试成功。")
                                 available_channels.append(channel_config)
                            else:
                                 self.logger.warning(f"{channel_name}: 测试失败 - 无法获取有效响应。响应: {response}")
                        except Exception as test_e:
                             self.logger.warning(f"{channel_name}: 使用模型 '{test_model_name}' 测试失败: {test_e}")

            except Exception as e:
                self.logger.warning(f"{channel_name}: 测试失败 - {e}")
                # 不打印完整堆栈，只记录错误信息

        self.logger.info(f"\n--- AI 渠道可用性测试完成。{len(available_channels)} 个渠道可用。 ---")
        # 更新实例的 channels 列表为可用的渠道
        self.channels = available_channels
        return available_channels

    def _parse_ai_response(self, api_response):
        """
        解析通用 AI API 的响应，提取验证码文本。
        """
        self.logger.debug("正在解析 AI API 响应...")
        try:
            # 示例 (适用于 OpenAI/Grok 兼容 API):
            if hasattr(api_response, "choices") and api_response.choices:
                first_choice = api_response.choices[0]
                if hasattr(first_choice, "message") and hasattr(
                    first_choice.message, "content"
                ):
                    raw_text = first_choice.message.content.strip()
                    self.logger.debug(f"从 AI 响应中解析到原始文本: '{raw_text}'")
                    # 清理文本：移除空格并只保留字母和数字
                    cleaned_text = ''.join(filter(str.isalnum, raw_text))
                    self.logger.info(f"清理后的验证码文本: '{cleaned_text}'")
                    return cleaned_text
            # 示例 (适用于 Gemini API):
            elif hasattr(api_response, "text"):
                raw_text = api_response.text.strip()
                self.logger.debug(f"从 AI 响应中解析到原始文本: '{raw_text}'")
                # 清理文本：移除空格并只保留字母和数字
                cleaned_text = ''.join(filter(str.isalnum, raw_text))
                self.logger.info(f"清理后的验证码文本: '{cleaned_text}'")
                return cleaned_text

            self.logger.warning(
                "无法从 AI 响应中解析出验证码文本。响应结构可能不符合预期。"
            )
            self.logger.debug(
                f"原始响应类型: {type(api_response)}"
            )  # 打印响应类型以便调试
            self.logger.debug(f"原始响应: {api_response}")  # 打印原始响应以便调试
            return None

        except Exception as e:
            self.logger.error(f"解析 AI 响应时发生错误: {e}", exc_info=True) # 解析错误保留堆栈，方便调试
            self.logger.debug(
                f"原始响应类型: {type(api_response)}"
            )  # 打印响应类型以便调试
            self.logger.debug(f"原始响应: {api_response}")  # 打印原始响应以便调试
            return None
