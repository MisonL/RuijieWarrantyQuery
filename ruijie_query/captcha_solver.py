import logging
import time

import base64
import random

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
        ai_settings, # 通用 AI 设置 (retry_attempts, retry_delay, rate_limit_delay)
        channels, # 渠道配置列表
        logger=None,
    ):
        self.ai_settings = ai_settings
        self.channels = channels
        self.logger = logger or logging.getLogger(__name__)

        # 尝试导入 AI 库 (只需导入一次)
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


    def solve_captcha(self, captcha_image_data):
        """
        使用配置的 AI API 解决验证码，按渠道顺序尝试。
        """
        if not self.channels:
            self.logger.error("错误：config.ini 中未配置任何 AI 渠道。")
            return None

        # 将图片数据编码为 base64 (一些 API 可能需要)
        base64_image = base64.b64encode(captcha_image_data).decode("utf-8")

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

            self.logger.info(f"尝试使用 {channel_name} 识别验证码...")

            if api_type == "none":
                self.logger.info(f"{channel_name} 配置为 'None'，跳过此渠道。")
                continue # 跳过当前渠道

            if not api_key and api_type != "none": # 对于非 none 类型，api_key 通常是必需的
                 self.logger.warning(f"{channel_name} 未配置 API Key，跳过此渠道。")
                 continue # 跳过当前渠道

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
            for attempt in range(self.ai_settings.get("retry_attempts", 3)):
                try:
                    self.logger.info(f"{channel_name}: 尝试 {attempt + 1}/{self.ai_settings.get('retry_attempts', 3)}...")
                    captcha_solution = None

                    if api_type == "gemini":
                        # 实现 Gemini API 调用逻辑
                        try:
                            genai.configure(api_key=api_key)
                            model = genai.GenerativeModel(
                                model_name or "gemini-pro-vision" # 默认使用视觉模型
                            )
                            # TODO: 增加对 Gemini 模型是否支持视觉的检查
                            image_part = {
                                "mime_type": "image/png",
                                "data": base64_image,
                            }
                            prompt = (
                                "识别这张图片中的验证码文本，只返回验证码文本，"
                                "不要包含其他任何内容。"
                            )
                            response = model.generate_content([prompt, image_part])
                            captcha_solution = self._parse_ai_response(response)
                        except Exception as api_e:
                            # 记录简洁错误信息，不打印完整堆栈
                            self.logger.error(f"{channel_name}: 调用 Gemini API 时发生错误: {api_e}")
                            raise api_e # Re-raise exception to be caught by the outer retry loop

                    elif api_type in ["openai", "grok"]:
                        # 实现 OpenAI / Grok 兼容 API 调用逻辑
                        try:
                            client_params = {"api_key": api_key}
                            if base_url:
                                client_params["base_url"] = base_url
                                self.logger.info(f"{channel_name}: 使用 Base URL: {base_url}")
                            client = openai.OpenAI(**client_params)

                            # Use vision model for image recognition
                            # TODO: Add check if OpenAI compatible model supports vision
                            response = client.chat.completions.create(
                                model=model_name or "gpt-4o", # Default to a vision model
                                messages=[
                                    {
                                        "role": "user",
                                        "content": [
                                            {
                                                "type": "text",
                                                "text": (
                                                    "识别这张图片中的验证码文本，"
                                                    "只返回验证码文本，"
                                                    "不要包含其他任何内容。"
                                                ),
                                            },
                                            {
                                                "type": "image_url",
                                                "image_url": {
                                                    "url": f"data:image/png;base64,{base64_image}"
                                                },
                                            },
                                        ],
                                    }
                                ],
                                max_tokens=50,
                            )
                            captcha_solution = self._parse_ai_response(response)
                        except openai.RateLimitError as rate_limit_e:
                            self.logger.warning(f"{channel_name}: 检测到频率限制错误 (429): {rate_limit_e}")
                            self.logger.info(f"{channel_name}: 等待 {self.ai_settings.get('rate_limit_delay', 30):.2f} 秒后重试...")
                            time.sleep(self.ai_settings.get("rate_limit_delay", 30))
                            raise rate_limit_e # Re-raise to be caught by the outer retry loop
                        except Exception as api_e:
                            # 记录简洁错误信息，不打印完整堆栈
                            self.logger.error(f"{channel_name}: 调用 {api_type.upper()} API 时发生错误: {api_e}")
                            # TODO: Identify and handle errors where the model doesn't support image input
                            error_message = str(api_e).lower()
                            # More robust check might involve inspecting error codes or specific error messages
                            if "unsupported input type" in error_message or (model_name and "vision" not in model_name.lower() and "image" in error_message):
                                self.logger.error(f"{channel_name}: 配置的模型 '{model_name}' 可能不支持图像输入。请检查 config.ini 并更换支持视觉的模型。")
                                break # Exit the inner retry loop for the current channel, try the next channel
                            raise api_e # Re-raise other exceptions

                    # If captcha_solution is obtained
                    if captcha_solution:
                        self.logger.info(f"{channel_name}: AI 识别成功: {captcha_solution}")
                        return captcha_solution # Return immediately on success

                except Exception as e:
                    # Log concise attempt failure information, no full stack trace
                    self.logger.error(
                        f"{channel_name}: AI 识别验证码时发生错误 (尝试 {attempt + 1}/{self.ai_settings.get('retry_attempts', 3)}): {e}"
                    )
                    if attempt < self.ai_settings.get("retry_attempts", 3) - 1:
                        wait_time = self.ai_settings.get("retry_delay", 5) * (2**attempt) + random.uniform(0, 1)
                        self.logger.info(f"{channel_name}: 等待 {wait_time:.2f} 秒后重试...")
                        time.sleep(wait_time)
                    else:
                        self.logger.error(f"{channel_name}: 达到最大重试次数，此渠道识别失败。")
                        # Do not return None, continue outer loop to try next channel

        # If all channels failed
        self.logger.error("所有配置的 AI 渠道都未能成功识别验证码。")
        return None


    def test_channels_availability(self):
        """
        测试配置的 AI 渠道是否可用，并返回可用的渠道列表。
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
