import configparser
import os
import re
import json
import shutil
from typing import Dict, List, Optional, Tuple, Any, Union
from pathlib import Path
import logging


# --- 配置验证器 ---
class ConfigValidator:
    """
    配置验证器 - 负责验证配置文件的完整性和正确性
    """

    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        self.validation_errors = []
        self.validation_warnings = []

    def validate_config(self, config: configparser.ConfigParser) -> Tuple[bool, List[str], List[str]]:
        """
        验证配置文件的完整性和正确性
        返回: (是否验证通过, 错误列表, 警告列表)
        """
        self.validation_errors = []
        self.validation_warnings = []

        # 验证必要的配置节
        self._validate_sections(config)

        # 验证General配置
        if "General" in config:
            self._validate_general_config(config["General"])

        # 验证AI配置
        if "AI_Settings" in config:
            self._validate_ai_config(config["AI_Settings"])

        # 验证ResultColumns配置
        if "ResultColumns" in config:
            self._validate_result_columns(config["ResultColumns"])

        # 验证Logging配置
        if "Logging" in config:
            self._validate_logging_config(config["Logging"])

        # 验证CaptchaSettings配置
        if "CaptchaSettings" in config:
            self._validate_captcha_config(config["CaptchaSettings"])

        is_valid = len(self.validation_errors) == 0
        return is_valid, self.validation_errors, self.validation_warnings

    def _validate_sections(self, config: configparser.ConfigParser):
        """验证配置节是否存在"""
        required_sections = ["General", "AI_Settings", "ResultColumns"]
        optional_sections = ["Logging", "CaptchaSettings"]

        for section in required_sections:
            if section not in config:
                self.validation_errors.append(f"缺少必要的配置节: [{section}]")

        for section in optional_sections:
            if section not in config:
                self.validation_warnings.append(f"缺少可选配置节: [{section}]")

    def _validate_general_config(self, section: configparser.SectionProxy):
        """验证General配置节"""
        # 检查必要的字段
        required_fields = ["excel_file_path", "sheet_name", "sn_column_name"]
        for field in required_fields:
            if field not in section:
                self.validation_errors.append(f"General配置缺少必要字段: {field}")

        # 验证文件路径
        excel_path = section.get("excel_file_path")
        if excel_path and not self._validate_file_path(excel_path):
            self.validation_errors.append(f"Excel文件路径无效: {excel_path}")

        # 验证数值字段 - 使用常量替代magic number
        from .constants import ConfigLimits
        numeric_fields = {
            "query_delay": (0, ConfigLimits.QUERY_DELAY_MAX),      # 查询延时最大值
            "save_interval": (0, ConfigLimits.SAVE_INTERVAL_MAX),   # 保存间隔最大值
            "max_query_attempts": (1, ConfigLimits.MAX_QUERY_ATTEMPTS), # 最大查询尝试次数
            "max_captcha_retries": (0, ConfigLimits.MAX_CAPTCHA_RETRIES)  # 最大验证码重试次数
        }

        for field, (min_val, max_val) in numeric_fields.items():
            if field in section:
                try:
                    value = section.getint(field)
                    # 添加完整的None检查，并将比较操作移至None检查之后
                    if (value is not None and min_val is not None and max_val is not None):
                        if not (min_val <= value <= max_val):
                            self.validation_errors.append(
                                f"General.{field} 值 {value} 超出允许范围 [{min_val}, {max_val}]"
                            )
                except (ValueError, TypeError):
                    self.validation_errors.append(f"General.{field} 不是有效的整数值")

        # 验证ChromeDriver路径（如果指定）
        driver_path = section.get("chrome_driver_path")
        if driver_path and not self._validate_driver_path(driver_path):
            self.validation_errors.append(f"ChromeDriver路径无效: {driver_path}")

    def _validate_ai_config(self, section: configparser.SectionProxy):
        """验证AI配置节"""
        # 检查通用设置
        numeric_fields = {
            "retry_attempts": (1, 10),
            "retry_delay": (1, 60),
            "rate_limit_delay": (1, 300),
            "ai_test_timeout": (10, 300)
        }

        for field, (min_val, max_val) in numeric_fields.items():
            if field in section:
                try:
                    value = section.getint(field)
                    # 添加完整的None检查，并将比较操作移至None检查之后
                    if (min_val is not None and max_val is not None and value is not None):
                        if not (min_val <= value <= max_val):
                            self.validation_errors.append(
                                f"AI_Settings.{field} 值 {value} 超出允许范围 [{min_val}, {max_val}]"
                            )
                except ValueError:
                    self.validation_errors.append(f"AI_Settings.{field} 不是有效的整数值")

        # 验证AI渠道配置
        self._validate_ai_channels(section)

    def _validate_ai_channels(self, section: configparser.SectionProxy):
        """验证AI渠道配置"""
        # 查找所有渠道配置
        channel_configs = {}
        for key in section.keys():
            if key.startswith("channel_") and key.endswith("_api_type"):
                try:
                    channel_num = int(key.split('_')[1])
                    channel_configs[channel_num] = {
                        "api_type": section.get(key),
                        "api_key": section.get(f"channel_{channel_num}_api_key"),
                        "model_name": section.get(f"channel_{channel_num}_model_name"),
                        "base_url": section.get(f"channel_{channel_num}_base_url")
                    }
                except (ValueError, IndexError):
                    self.validation_warnings.append(f"AI渠道配置格式错误: {key}")

        # 验证每个渠道
        for channel_num, config in channel_configs.items():
            self._validate_single_ai_channel(channel_num, config)

        # 检查是否有至少一个有效渠道
        valid_channels = [num for num, config in channel_configs.items()
                         if config["api_type"] and config["api_type"].lower() != "none"]
        if not valid_channels:
            self.validation_errors.append("AI_Settings中没有配置有效的AI渠道")

    def _validate_single_ai_channel(self, channel_num: int, config: Dict[str, str]):
        """验证单个AI渠道配置"""
        # 检查api_type
        api_type = config.get("api_type", "").lower()
        valid_api_types = ["gemini", "openai", "grok", "none"]
        if api_type not in valid_api_types:
            self.validation_errors.append(
                f"AI渠道{channel_num}的api_type '{api_type}' 无效，"
                f"应该是: {', '.join(valid_api_types)}"
            )

        # 检查API密钥（除非是none类型）
        if api_type != "none":
            api_key = config.get("api_key")
            if not api_key or api_key.strip() == "":
                self.validation_errors.append(f"AI渠道{channel_num}缺少api_key")
            elif api_key == "YOUR_API_KEY_HERE" or "YOUR_" in api_key:
                self.validation_warnings.append(
                    f"AI渠道{channel_num}使用了示例API密钥，请配置真实的密钥"
                )

        # 检查模型名称
        model_name = config.get("model_name")
        if not model_name or model_name.strip() == "":
            self.validation_errors.append(f"AI渠道{channel_num}缺少model_name")

        # 检查Base URL（如果提供）
        base_url = config.get("base_url")
        if base_url and not self._validate_url(base_url):
            self.validation_errors.append(f"AI渠道{channel_num}的base_url格式无效: {base_url}")

    def _validate_result_columns(self, section: configparser.SectionProxy):
        """验证ResultColumns配置"""
        # 检查是否有至少一个列配置
        if not section:
            self.validation_errors.append("ResultColumns配置为空")

        # 检查映射是否合理
        excel_columns = set(section.keys())
        web_fields = set(section.values())

        # 检查是否包含查询状态列
        if "查询状态" not in excel_columns and "查询状态" not in web_fields:
            self.validation_warnings.append("ResultColumns中缺少查询状态字段映射")

        # 检查重复的Excel列名
        if len(excel_columns) != len(set(excel_columns)):
            self.validation_errors.append("ResultColumns中存在重复的Excel列名")

        # 检查重复的网页字段
        if len(web_fields) != len(set(web_fields)):
            self.validation_errors.append("ResultColumns中存在重复的网页字段")

    def _validate_logging_config(self, section: configparser.SectionProxy):
        """验证Logging配置"""
        # 验证日志级别
        log_level = section.get("log_level", "INFO").upper()
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if log_level not in valid_levels:
            self.validation_errors.append(f"Logging.log_level 无效: {log_level}，应该是: {', '.join(valid_levels)}")

        # 验证log_to_console
        log_to_console = section.get("log_to_console", "True")
        if log_to_console.lower() not in ["true", "false"]:
            self.validation_errors.append("Logging.log_to_console 应该是 True 或 False")

        # 验证日志文件路径（如果指定）
        log_file = section.get("log_file")
        if log_file and not self._validate_file_path(log_file, check_exists=False):
            self.validation_warnings.append(f"日志文件路径可能无效: {log_file}")

        # 验证log_max_bytes格式
        log_max_bytes = section.get("log_max_bytes", "1024KB")
        if not self._validate_file_size(log_max_bytes):
            self.validation_errors.append(f"Logging.log_max_bytes 格式无效: {log_max_bytes}")

        # 验证log_backup_count
        try:
            backup_count = section.getint("log_backup_count", 5)
            if backup_count is not None and not (0 <= backup_count <= 20):
                self.validation_errors.append("Logging.log_backup_count 应该在 0-20 范围内")
        except (ValueError, TypeError):
            self.validation_errors.append("Logging.log_backup_count 不是有效的整数值")

    def _validate_captcha_config(self, section: configparser.SectionProxy):
        """验证CaptchaSettings配置"""
        # 验证primary_solver
        primary_solver = section.get("captcha_primary_solver", "ddddocr").lower()
        valid_solvers = ["ddddocr", "ai"]
        if primary_solver not in valid_solvers:
            self.validation_errors.append(
                f"CaptchaSettings.captcha_primary_solver 无效: {primary_solver}，"
                f"应该是: {', '.join(valid_solvers)}"
            )

        # 验证布尔配置项
        bool_fields = ["captcha_enable_ddddocr", "captcha_enable_ai"]
        for field in bool_fields:
            value = section.get(field, "True")
            if value.lower() not in ["true", "false"]:
                self.validation_errors.append(f"CaptchaSettings.{field} 应该是 True 或 False")

        # 验证ddddocr_max_attempts
        try:
            max_attempts = section.getint("ddddocr_max_attempts", 3)
            # 添加None检查以避免类型错误
            if max_attempts is not None and not (1 <= max_attempts <= 10):
                self.validation_errors.append("CaptchaSettings.ddddocr_max_attempts 应该在 1-10 范围内")
        except ValueError:
            self.validation_errors.append("CaptchaSettings.ddddocr_max_attempts 不是有效的整数值")

    def _validate_file_path(self, file_path: str, check_exists: bool = True) -> bool:
        """验证文件路径"""
        try:
            path = Path(file_path)
            if check_exists:
                return path.exists()
            else:
                # 检查路径格式是否有效
                return path.is_absolute() or not file_path.strip() == ""
        except Exception:
            return False

    def _validate_driver_path(self, driver_path: str) -> bool:
        """验证ChromeDriver路径"""
        try:
            path = Path(driver_path)
            if path.exists():
                return path.is_file()
            else:
                # 检查路径格式
                return path.is_absolute() or path.name in ["chromedriver", "chromedriver.exe"]
        except Exception:
            return False

    def _validate_url(self, url: str) -> bool:
        """验证URL格式"""
        try:
            from urllib.parse import urlparse
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False

    def _validate_file_size(self, size_str: str) -> bool:
        """验证文件大小格式"""
        try:
            size_str = size_str.strip().upper()
            if size_str.endswith("KB"):
                float(size_str[:-2])
                return True
            elif size_str.endswith("MB"):
                float(size_str[:-2])
                return True
            elif size_str.endswith("B"):
                float(size_str[:-1])
                return True
            else:
                # 尝试直接解析为字节数
                float(size_str)
                return True
        except Exception:
            return False

    def get_validation_summary(self) -> Dict[str, Any]:
        """获取验证摘要信息"""
        return {
            "total_errors": len(self.validation_errors),
            "total_warnings": len(self.validation_warnings),
            "errors": self.validation_errors.copy(),
            "warnings": self.validation_warnings.copy(),
            "is_valid": len(self.validation_errors) == 0
        }

    def generate_fix_suggestions(self) -> List[str]:
        """生成修复建议"""
        suggestions = []

        # 基于错误类型生成建议
        error_summary = "\n".join(self.validation_errors)

        if "缺少必要的配置节" in error_summary:
            suggestions.append("请参考 config.example.ini 文件，确保包含所有必要的配置节")

        if "缺少必要字段" in error_summary:
            suggestions.append("请检查并填写所有标有#必填的配置项")

        if "API密钥" in error_summary:
            suggestions.append("请在 config.ini 中配置真实的AI API密钥，替换示例密钥")

        if "Excel文件路径无效" in error_summary:
            suggestions.append("请确保 Excel 文件存在于指定路径，或使用相对路径")

        if "ChromeDriver路径无效" in error_summary:
            suggestions.append("请检查 ChromeDriver 路径是否正确，或留空让程序自动下载")

        return suggestions


# --- 配置管理类 ---
class ConfigManager:
    def __init__(self, config_file="config.ini", validate_config=True):
        self.config = configparser.ConfigParser()
        self.config_file = config_file
        self.validator = ConfigValidator()
        self.validation_enabled = validate_config
        self.validation_summary = None
        self.logger = logging.getLogger(__name__)  # 添加logger属性
        self._load_config()

    def _load_config(self):
        if not os.path.exists(self.config_file):
            self._handle_config_error(
                f"配置文件 '{self.config_file}' 未找到。请确保该文件存在于脚本所在目录。"
            )

        try:
            self.config.read(self.config_file, encoding="utf-8")
            print(f"配置文件 '{self.config_file}' 读取成功。")

            # 验证配置文件（如果启用）
            if self.validation_enabled:
                self._validate_and_handle_errors()

        except configparser.Error as e:
            self._handle_config_error(f"配置文件格式错误: {e}")
        except Exception as e:
            self._handle_config_error(f"读取配置文件 '{self.config_file}' 时发生错误: {e}")

    def _validate_and_handle_errors(self):
        """验证配置文件并处理错误"""
        try:
            is_valid, errors, warnings = self.validator.validate_config(self.config)
            self.validation_summary = self.validator.get_validation_summary()

            # 记录验证结果
            if errors:
                print(f"⚠️  发现 {len(errors)} 个配置错误:")
                for i, error in enumerate(errors, 1):
                    print(f"  {i}. {error}")

            if warnings:
                print(f"💡 发现 {len(warnings)} 个配置警告:")
                for i, warning in enumerate(warnings, 1):
                    print(f"  {i}. {warning}")

            # 如果有错误，询问用户是否继续
            if errors:
                suggestions = self.validator.generate_fix_suggestions()
                if suggestions:
                    print("\n🔧 修复建议:")
                    for i, suggestion in enumerate(suggestions, 1):
                        print(f"  {i}. {suggestion}")

                # 根据错误严重程度决定处理方式
                critical_errors = [e for e in errors if not any(warning_type in e for warning_type in ["示例", "建议"])]
                if critical_errors:
                    print(f"\n❌ 发现 {len(critical_errors)} 个严重错误，程序可能无法正常运行。")
                    response = input("是否继续运行? (y/N): ").strip().lower()
                    if response not in ['y', 'yes']:
                        print("程序已退出。请修复配置文件错误后重试。")
                        exit(1)
                else:
                    print("⚠️  继续运行，但可能会遇到问题。")

            elif warnings:
                print("✅ 配置验证通过，但有一些建议。")

            else:
                print("✅ 配置验证完全通过！")

        except Exception as e:
            self.logger.warning(f"配置验证过程中发生错误: {e}")
            # 验证失败时记录警告但不阻止程序运行

    def _handle_config_error(self, error_message):
        """处理配置文件错误"""
        print(f"❌ 错误: {error_message}")

        # 提供详细的故障排除信息
        print("\n🔧 故障排除:")
        print("1. 检查 config.ini 文件是否存在")
        print("2. 确保文件编码为 UTF-8")
        print("3. 检查 INI 文件格式是否正确")
        print("4. 参考 config.example.ini 文件")

        # 询问用户是否要使用示例配置
        example_file = "config.example.ini"
        if os.path.exists(example_file):
            print(f"\n💡 您可以复制 {example_file} 并重命名为 config.ini 作为起点:")
            print(f"cp {example_file} config.ini")

        exit(1)

    def validate_config(self) -> Dict[str, Any]:
        """手动触发配置验证"""
        if not self.validation_enabled:
            # 如果之前禁用了验证，现在临时启用
            is_valid, errors, warnings = self.validator.validate_config(self.config)
            self.validation_summary = self.validator.get_validation_summary()
            return self.validation_summary
        else:
            return self.validation_summary or {"is_valid": True, "errors": [], "warnings": []}

    def fix_common_issues(self) -> bool:
        """尝试修复常见的配置问题"""
        fixed_count = 0

        try:
            # 1. 自动添加缺失的可选配置节
            self._ensure_optional_sections()

            # 2. 修复布尔值格式
            fixed_count += self._fix_boolean_values()

            # 3. 修复数值范围
            fixed_count += self._fix_numeric_ranges()

            # 4. 清理注释和空行
            self._clean_config()

            if fixed_count > 0:
                # 保存修复后的配置
                self.save_config()
                print(f"✅ 已自动修复 {fixed_count} 个配置问题")
                return True
            else:
                print("✅ 配置没有需要修复的问题")
                return False

        except Exception as e:
            self.logger.error(f"自动修复配置问题时出错: {e}")
            return False

    def _ensure_optional_sections(self):
        """确保可选配置节存在"""
        sections_to_add = {
            "Logging": {
                "log_file": "app.log",
                "log_level": "INFO",
                "log_to_console": "True",
                "log_max_bytes": "1024KB",
                "log_backup_count": "5"
            },
            "CaptchaSettings": {
                "captcha_primary_solver": "ddddocr",
                "captcha_enable_ddddocr": "True",
                "captcha_enable_ai": "True",
                "ddddocr_max_attempts": "3"
            }
        }

        for section_name, default_values in sections_to_add.items():
            if section_name not in self.config:
                self.config.add_section(section_name)
                for key, value in default_values.items():
                    self.config.set(section_name, key, value)
                self.logger.info(f"添加了缺失的配置节: [{section_name}]")

    def _fix_boolean_values(self) -> int:
        """修复布尔值格式"""
        fixed_count = 0

        # 检查Logging配置
        if "Logging" in self.config:
            log_to_console = self.config.get("Logging", "log_to_console", fallback="True")
            if log_to_console.lower() not in ["true", "false"]:
                # 尝试智能修复
                if log_to_console.lower() in ["1", "yes", "on", "enable"]:
                    self.config.set("Logging", "log_to_console", "True")
                else:
                    self.config.set("Logging", "log_to_console", "False")
                fixed_count += 1

        # 检查CaptchaSettings配置
        if "CaptchaSettings" in self.config:
            bool_fields = ["captcha_enable_ddddocr", "captcha_enable_ai"]
            for field in bool_fields:
                if field in self.config:
                    value = self.config.get("CaptchaSettings", field).lower()
                    if value not in ["true", "false"]:
                        # 智能修复
                        if value in ["1", "yes", "on", "enable"]:
                            self.config.set("CaptchaSettings", field, "True")
                        else:
                            self.config.set("CaptchaSettings", field, "False")
                        fixed_count += 1

        return fixed_count

    def _fix_numeric_ranges(self) -> int:
        """修复数值范围"""
        fixed_count = 0

        # General配置范围修复
        if "General" in self.config:
            general_ranges = {
                "query_delay": (0, 300),
                "save_interval": (0, 1000),
                "max_query_attempts": (1, 10),
                "max_captcha_retries": (0, 5)
            }

            for field, (min_val, max_val) in general_ranges.items():
                if field in self.config:
                    try:
                        value = self.config.getint("General", field)
                        # 添加None检查以避免类型错误
                        if (value is not None and min_val is not None and max_val is not None):
                            if value < min_val:
                                self.config.set("General", field, str(min_val))
                                fixed_count += 1
                            elif value > max_val:
                                self.config.set("General", field, str(max_val))
                                fixed_count += 1
                    except ValueError:
                        # 设置默认值
                        default_values = {
                            "query_delay": 10,
                            "save_interval": 10,
                            "max_query_attempts": 3,
                            "max_captcha_retries": 2
                        }
                        self.config.set("General", field, str(default_values[field]))
                        fixed_count += 1

        return fixed_count

    def _clean_config(self):
        """清理配置文件的注释和空行"""
        # 这里可以实现更复杂的清理逻辑
        # 目前主要是确保格式正确
        pass

    def save_config(self, backup=True):
        """保存配置文件"""
        try:
            if backup:
                backup_path = f"{self.config_file}.backup"
                shutil.copy2(self.config_file, backup_path)
                self.logger.info(f"已创建配置文件备份: {backup_path}")

            with open(self.config_file, 'w', encoding='utf-8') as f:
                self.config.write(f)
            self.logger.info(f"配置文件已保存: {self.config_file}")

        except Exception as e:
            self.logger.error(f"保存配置文件失败: {e}")
            raise

    def export_config_template(self, output_file="config_template.ini"):
        """导出配置模板"""
        try:
            template_config = configparser.ConfigParser()

            # 添加所有必要的节和字段
            template_config.add_section("General")
            template_config.set("General", "excel_file_path", "Serial-Number.xlsx")
            template_config.set("General", "sheet_name", "Sheet1")
            template_config.set("General", "sn_column_name", "Serial Number")
            template_config.set("General", "query_delay", "10")
            template_config.set("General", "save_interval", "10")
            template_config.set("General", "chrome_driver_path", "")
            template_config.set("General", "max_query_attempts", "3")
            template_config.set("General", "max_captcha_retries", "2")

            template_config.add_section("AI_Settings")
            template_config.set("AI_Settings", "retry_attempts", "3")
            template_config.set("AI_Settings", "retry_delay", "5")
            template_config.set("AI_Settings", "rate_limit_delay", "30")
            template_config.set("AI_Settings", "ai_test_timeout", "120")

            # 添加示例渠道
            template_config.set("AI_Settings", "channel_1_api_type", "gemini")
            template_config.set("AI_Settings", "channel_1_api_key", "YOUR_GEMINI_API_KEY_HERE")
            template_config.set("AI_Settings", "channel_1_model_name", "gemini-pro-vision")

            template_config.add_section("ResultColumns")
            template_config.set("ResultColumns", "型号", "型号")
            template_config.set("ResultColumns", "服务名称", "服务名称")
            template_config.set("ResultColumns", "设备类型", "设备类型")
            template_config.set("ResultColumns", "保修开始时间", "保修开始时间")
            template_config.set("ResultColumns", "保修结束时间", "保修结束时间")
            template_config.set("ResultColumns", "保修剩余天数", "保修剩余天数")
            template_config.set("ResultColumns", "保修状态", "保修状态")
            template_config.set("ResultColumns", "查询状态", "查询状态")

            template_config.add_section("Logging")
            template_config.set("Logging", "log_file", "app.log")
            template_config.set("Logging", "log_level", "INFO")
            template_config.set("Logging", "log_to_console", "True")
            template_config.set("Logging", "log_max_bytes", "1024KB")
            template_config.set("Logging", "log_backup_count", "5")

            template_config.add_section("CaptchaSettings")
            template_config.set("CaptchaSettings", "captcha_primary_solver", "ddddocr")
            template_config.set("CaptchaSettings", "captcha_enable_ddddocr", "True")
            template_config.set("CaptchaSettings", "captcha_enable_ai", "True")
            template_config.set("CaptchaSettings", "ddddocr_max_attempts", "3")

            with open(output_file, 'w', encoding='utf-8') as f:
                template_config.write(f)

            print(f"配置模板已导出到: {output_file}")

        except Exception as e:
            self.logger.error(f"导出配置模板失败: {e}")
            raise

    def get_general_config(self):
        general_config = self.config["General"]
        return {
            "excel_file_path": general_config.get(
                "excel_file_path", "Serial-Number.xlsx"
            ),
            "sheet_name": general_config.get("sheet_name", "Sheet1"),
            "sn_column_name": general_config.get("sn_column_name", "Serial Number"),
            "query_delay": general_config.getint("query_delay", 10),
            "save_interval": general_config.getint("save_interval", 10),
            "chrome_driver_path": general_config.get("chrome_driver_path", None) or None,  # 处理空字符串
            "max_query_attempts": general_config.getint("max_query_attempts", 3), # 新增
            "max_captcha_retries": general_config.getint("max_captcha_retries", 2), # 新增
        }

    def get_ai_config(self):
        ai_settings = self.config["AI_Settings"]
        channels = []
        # 动态查找所有以 'channel_N_' 开头的配置项
        channel_options = [opt for opt in ai_settings.keys() if opt.startswith("channel_") and opt.endswith("_api_type")]

        # 提取渠道编号并排序
        channel_indices = sorted(list(set([int(opt.split('_')[1]) for opt in channel_options if opt.split('_')[1].isdigit()])))

        for i in channel_indices:
            channel_prefix = f"channel_{i}_"
            channel_config = {
                "api_type": ai_settings.get(f"{channel_prefix}api_type", "None").strip().lower(),
                "api_key": ai_settings.get(f"{channel_prefix}api_key", None),
                "model_name": ai_settings.get(f"{channel_prefix}model_name", None),
                "base_url": ai_settings.get(f"{channel_prefix}base_url", None),
            }
            # 只有当 api_type 不是 'none' 时才添加渠道
            if channel_config["api_type"] != "none":
                 channels.append(channel_config)
            else:
                 print(f"警告：config.ini 中 {channel_prefix}api_type 配置为 'None' 或未配置，跳过此渠道。")


        return {
            "channels": channels,
            "retry_attempts": ai_settings.getint("retry_attempts", 3),
            "retry_delay": ai_settings.getint("retry_delay", 5),
            "rate_limit_delay": ai_settings.getint("rate_limit_delay", 30),
        }

    def get_result_columns(self):
        # 将 ResultColumns section 读入字典，保留原始大小写
        result_columns = {k: v for k, v in self.config["ResultColumns"].items()}
        # 确保 '查询状态' 列存在
        if "查询状态" not in result_columns:
            result_columns["查询状态"] = "查询状态"
        return result_columns

    def get_logging_config(self):
        """获取日志配置"""
        logging_config = {}
        if "Logging" in self.config:
            logging_section = self.config["Logging"]
            logging_config["log_file"] = logging_section.get("log_file", None)
            logging_config["log_level"] = logging_section.get(
                "log_level", "INFO"
            ).upper()
            logging_config["log_to_console"] = logging_section.getboolean(
                "log_to_console", True
            )

            # 解析 log_max_bytes，支持 KB/MB 单位
            log_max_bytes_str = logging_section.get("log_max_bytes", "1024KB") # 默认 1024KB
            match = re.match(r"^(\d+)\s*(KB|MB)?$", log_max_bytes_str, re.IGNORECASE)
            if match:
                value = int(match.group(1))
                unit = match.group(2)
                if unit and unit.upper() == "MB":
                    logging_config["max_bytes"] = value * 1024 * 1024
                else: # 默认为 KB 或未指定单位
                    logging_config["max_bytes"] = value * 1024
            else:
                print(f"警告：无法解析 log_max_bytes 值 '{log_max_bytes_str}'，使用默认值 1MB。")
                logging_config["max_bytes"] = 1024 * 1024 # 解析失败时的默认值

            logging_config["backup_count"] = logging_section.getint("log_backup_count", 5) # 默认保留 5 个备份文件
        else:
            # 提供默认日志配置
            logging_config["log_file"] = None
            logging_config["log_level"] = "INFO"
            logging_config["log_to_console"] = True
            # 添加默认的日志文件大小和备份数量
            logging_config["max_bytes"] = 1024 * 1024 # 默认 1MB
            logging_config["backup_count"] = 5 # 默认保留 5 个备份文件
            print("警告：config.ini 中未找到 [Logging] section，使用默认日志配置。")
        return logging_config

    def get_config(self):
        """返回完整的 configparser 对象"""
        return self.config

    def get_captcha_config(self):
        """获取验证码识别相关配置"""
        captcha_config = {}
        if "CaptchaSettings" in self.config:
            captcha_section = self.config["CaptchaSettings"]
            captcha_config["primary_solver"] = captcha_section.get(
                "captcha_primary_solver", "ddddocr" # 默认 ddddocr
            ).lower()
            captcha_config["enable_ddddocr"] = captcha_section.getboolean(
                "captcha_enable_ddddocr", True # 默认启用
            )
            captcha_config["enable_ai"] = captcha_section.getboolean(
                "captcha_enable_ai", True # 默认启用
            )
            captcha_config["ddddocr_max_attempts"] = captcha_section.getint(
                "ddddocr_max_attempts", 3 # 默认 3 次
            )
        else:
            # 提供默认验证码配置
            captcha_config["primary_solver"] = "ddddocr"
            captcha_config["enable_ddddocr"] = True
            captcha_config["enable_ai"] = True
            captcha_config["ddddocr_max_attempts"] = 3
            print("警告：config.ini 中未找到 [CaptchaSettings] section，使用默认验证码配置。")
        return captcha_config
