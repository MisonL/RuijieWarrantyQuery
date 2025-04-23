import configparser
import os
import re


# --- 配置管理类 ---
class ConfigManager:
    def __init__(self, config_file="config.ini"):
        self.config = configparser.ConfigParser()
        self.config_file = config_file
        self._load_config()

    def _load_config(self):
        if not os.path.exists(self.config_file):
            print(
                f"错误：配置文件 '{self.config_file}' 未找到。请确保该文件存在于脚本所在目录。"
            )
            exit()
        try:
            self.config.read(self.config_file, encoding="utf-8")
            print(f"配置文件 '{self.config_file}' 读取成功。")
        except Exception as e:
            print(f"读取配置文件 '{self.config_file}' 时发生错误: {e}")
            exit()

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
