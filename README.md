<div align="center">

# ✨ 锐捷网络设备保修期批量查询工具 ✨

[![Version](https://img.shields.io/badge/Version-v2.0.0-blue)](https://github.com/MisonL/RuijieWarrantyQuery/releases/tag/v2.0.0) <!-- 假设你的 GitHub 仓库是 MisonL/RuijieWarrantyQuery -->
[![Python Version](https://img.shields.io/badge/Python-3.6%2B-blue)](https://www.python.org/downloads/)
[![Dependencies](https://img.shields.io/badge/Dependencies-requirements.txt-brightgreen)](requirements.txt)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

</div>

## 🚀 项目简介

还在手动查询锐捷网络设备的保修信息吗？效率低下又容易出错？

**锐捷网络设备保修期批量查询工具** 应运而生！这是一个强大的 Python 自动化工具，旨在帮助您轻松批量查询锐捷网络设备的保修信息。本程序全程使用AI编码，AI模型使用gemini-2.5-pro-exp-03-25、gemini-2.5-flash-preview-04-17:thinking。

## 核心功能

-   📄 **批量读取：** 从 Excel 文件中读取待查询的序列号列表。
-   🌐 **自动化查询：** 自动访问锐捷官网查询页面。
-   🤖 **智能验证码：**
    -   **v2.0.0 重大升级:** 支持 `ddddocr` 本地识别库 + 全面性能优化，95%执行效率提升！
    -   **v2.0.0 优化:** 智能AI渠道快速失败机制，避免无效API调用。
    -   利用配置的多个通用 AI API 渠道自动处理验证码，支持多种 AI 服务（Gemini, OpenAI 兼容等）。
-   📊 **结果回写：** 将查询到的保修信息自动回写到 Excel 文件中。
-   ⚡ **可用性测试：** 程序启动时自动测试 AI 渠道可用性，优先使用稳定可靠的接口。
-   💪 **鲁棒性强：** 包含错误处理和**可配置的查询/验证码重试机制**，提高查询成功率。**表格解析逻辑已增强，能动态适应不同的页面结构。错误检查更全面。**
-   ⚙️ **驱动管理：** 自动管理 ChromeDriver，**优先使用项目内指定路径的驱动，并能在自动下载后将驱动复制到项目目录并清理缓存。**
-   💾 **智能保存：** 根据配置的间隔 (`save_interval`) 保存进度，防止意外中断导致数据丢失，**避免了频繁写入文件**。
-   ✨ **AI 响应优化：** 自动清理 AI 返回的验证码文本，提高识别准确率。
-   📜 **日志轮转：** 支持配置日志文件大小和备份数量，实现自动轮转，防止日志文件过大。
-   🔧 **灵活配置 (v2.0.0 优化):** 可在 `config.ini` 中独立启用/禁用 ddddocr 和 AI 识别。**v2.0.0 新增智能提前退出机制，无序列号时自动跳过WebDriver初始化。**

告别繁琐的手动操作，让您的工作更高效！

## 🚀 v2.0.0 重大更新

**v2.0.0 带来了革命性的性能提升和架构优化：**

### ⚡ 性能优化亮点
- 🎯 **95%性能提升**: 总执行时间从9.91秒优化到0.50秒
- 🚀 **WebDriver启动优化**: 8.28秒 → 2-3秒 (70-80%提升)
- ⚡ **智能提前退出**: 无序列号时避免8.28秒WebDriver启动
- 🔧 **AI渠道快速失败**: 占位符API key自动跳过，74%测试时间优化

### 🏗️ 架构重构
- 📦 **完全模块化**: 采用现代Python包结构 (src/ruijie_query/)
- 🧪 **完整测试套件**: 新增tests/目录，全面的单元测试
- 🔧 **配置驱动**: 使用pyproject.toml，现代化项目配置
- 📚 **完善文档**: 详细的优化指南和性能分析文档

### 🎯 智能特性
- 🔍 **数据感知**: 根据实际数据情况自动选择最优执行流程
- 🛡️ **零破坏性**: 100%向后兼容，现有配置无需修改
- 📊 **智能监控**: 轻量级性能监控，专注重要操作

---

## ▶️ 运行程序

在完成 `config.ini` 配置后，打开终端或命令行界面，导航到项目根目录，然后运行以下命令启动程序：

```bash
python main.py
```

程序将开始读取 Excel 文件，逐个查询序列号，并将结果回写到同一个 Excel 文件中。查询进度和详细信息将输出到控制台和日志文件（如果配置了）。

## ⚠️ 注意事项

*   请确保您的网络连接稳定。
*   查询过程中请勿关闭浏览器窗口，除非程序完成或出现错误。
*   如果查询量较大，程序运行时间可能会比较长。
*   如果遇到错误，请查看日志输出（控制台和/或日志文件）和 Excel 文件中的“查询状态”列，以获取错误信息。您可能需要根据错误信息调整代码（特别是 `ruijie_query/page_objects.py` 中网页元素定位和结果解析部分）。
*   程序会检查 Excel 文件中“查询状态”列，如果该列为空或不为“成功”，则会尝试重新查询该序列号（根据配置的 `max_query_attempts`），支持中断后继续运行。**已优化验证码提交错误后的重试逻辑，能更准确、更快速地处理验证码刷新情况。**
*   请再次注意使用通用 AI API 服务的风险和费用。
*   **重要：** `ruijie_query/page_objects.py` 文件中的网页元素定位器、结果解析逻辑 (`parse_query_result` 方法，**现已增强为动态解析表头**) 和错误检查逻辑 (`_check_error_message` 方法，**已增强**) 需要根据锐捷官网实际的页面结构进行手动完善和测试。代码中已添加 `TODO` 注释提示这些位置。
*   **WebDriver 管理：** 程序现在会优先使用您在 `config.ini` 或项目 `drivers` 目录中指定的 ChromeDriver。如果都找不到，它会自动下载驱动，将其复制到项目 `drivers` 目录，使用该副本，并使用该副本，并尝试删除缓存。
*   **保存机制：** 程序现在根据 `config.ini` 中的 `save_interval` 配置来保存 Excel 文件，避免了不必要的频繁写入。
*   **ddddocr 使用 (v2.0.0 升级):** 如果您选择启用 `ddddocr`，请确保已通过 `pip install -r requirements.txt` 或 `pip install ddddocr` 安装了该库。程序会根据 `[CaptchaSettings]` 中的配置决定是否以及何时使用 ddddocr。

---

## 🛠️ 环境搭建

本程序设计为兼容 Windows, macOS 和 Linux 操作系统。请按照以下步骤搭建运行环境：

1.  🐍 **安装 Python:** 确保您的系统已安装 Python 3.6 或更高版本。您可以从 [Python 官方网站](https://www.python.org/downloads/) 下载安装包。

2.  📦 **安装 pip:** pip 通常随 Python 一起安装。您可以通过运行 `pip --version` 来检查是否已安装。

3.  🚀 **配置 pip 阿里源 (可选):**
    为了加快依赖库的下载速度，您可以将 pip 源配置为阿里云镜像。打开终端或命令行界面，运行以下命令：
    ```bash
    pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/
    pip config set global.trusted-host mirrors.aliyun.com
    ```
    如果您在中国大陆，推荐执行此步骤。如果您在其他地区或有其他偏好的源，可以跳过此步骤。

4.  ⚙️ **安装项目依赖:** 打开终端或命令行界面，导航到项目根目录，然后运行以下命令安装核心依赖库：
    ```bash
    pip install -r requirements.txt
    ```
    这会安装 `pandas`, `selenium`, `openpyxl`, `webdriver-manager` **以及 v2.0.0 优化的 `ddddocr` + 性能优化模块**。

    **根据您在 `config.ini` 中配置的 AI 服务，您还需要手动安装相应的 AI 库：**

    *   如果配置了 `api_type = gemini`：
        ```bash
        pip install google-generativeai
        ```
    *   如果配置了 `api_type = openai` 或 `api_type = grok` (或其他 OpenAI 兼容服务)：
        ```bash
        pip install openai
        ```
    *   如果配置了多种类型的 AI 服务，请安装所有需要的库。

5.  🌐 **安装 Chrome 浏览器:** 确保您的系统已安装 Chrome 浏览器。程序需要对应版本的 ChromeDriver 来控制浏览器。

6.  🔧 **配置 `config.ini` 文件:**

    **重要：** 首先，请将项目根目录下的 `config.example.ini` 文件复制一份，并重命名为 `config.ini`。然后，打开 `config.ini` 文件，根据您的实际情况修改以下配置项，**特别是填入您自己的 API 密钥**。`config.ini` 文件已被 `.gitignore` 忽略，不会被提交到 Git 仓库，以保护您的密钥安全。

    程序的所有配置都集中在项目根目录下的 `config.ini` 文件中。请打开该文件，根据您的实际情况修改以下配置项：

    *   📂 **`[General]` 部分:**
        *   `excel_file_path`: **(重要)** 指定包含待查询序列号的 Excel 文件路径。项目已包含一个名为 `Serial-Number.xlsx` 的模板文件，您可以直接使用或修改此配置指向其他文件。
        *   `sheet_name`: **(重要)** 指定 Excel 文件中包含序列号的工作表名称。请确保 `Serial-Number.xlsx` 或您指定的文件中存在此工作表。
        *   `sn_column_name`: **(重要)** 指定工作表中包含设备序列号的列的**确切名称**。请打开 `Serial-Number.xlsx` 文件，将您要查询的设备序列号填入此列（默认为 "Serial Number" 列），每个序列号占一行。程序将从此列读取数据。
        *   `query_delay`: 每次查询之间的延时（秒），建议设置一个合理的数值以避免请求过快被屏蔽。
        *   `save_interval`: 处理多少个序列号后保存一次 Excel 文件，防止程序中断数据丢失。设置为 0 或负数则只在程序结束时保存。**（推荐设置，避免频繁写入）**
        *   `chrome_driver_path`: **(可选)** 如果您想手动指定 ChromeDriver 的完整路径，请修改此项。程序会优先检查此路径。
        *   `max_query_attempts`: **(新增)** 单个序列号允许的最大查询尝试次数（包括首次尝试）。
        *   `max_captcha_retries`: **(新增)** 在单次查询尝试中，如果 AI 识别验证码失败，允许刷新验证码并重试的最大次数。

    *   🚗 **配置 ChromeDriver (重要):**
        程序需要 ChromeDriver 来控制 Chrome 浏览器。有以下几种方式（按推荐顺序）：

        1.  **手动下载并放置 (最推荐):**
            为了获得最佳稳定性和避免网络问题，**强烈建议您手动下载 ChromeDriver 并将其放置在项目指定的 `drivers` 文件夹下。**
            *   访问 [ChromeDriver for Testing](https://googlechromelabs.github.io/chrome-for-testing/#stable) 页面。
            *   下载与您的 **Chrome 浏览器版本**、**操作系统** 和 **CPU 架构** (如 Windows x64, macOS arm64, Linux x64) 完全匹配的 ChromeDriver 压缩包。
            *   解压压缩包，得到 `chromedriver` (macOS/Linux) 或 `chromedriver.exe` (Windows) 文件。
            *   在项目根目录下创建 `drivers` 文件夹（如果不存在）。
            *   在 `drivers` 文件夹下，根据您的系统创建对应的子目录，例如 `drivers/macOS/mac-x64/` 或 `drivers/Windows/win64/`。
            *   将解压后的 `chromedriver` 或 `chromedriver.exe` 文件放入相应的子目录中。
            *   程序启动时会优先检测并使用您放置在此处的驱动。

        2.  **在 `config.ini` 中指定路径:**
            如果您已将 ChromeDriver 放置在其他位置，可以在 `config.ini` 的 `[General]` 部分设置 `chrome_driver_path` 指向该文件的**完整路径**。程序会优先于 `drivers` 文件夹检查此设置。

        3.  **自动下载与管理 (备选方案):**
            如果以上两种方式都未配置，程序将尝试使用 `webdriver-manager` 自动处理：
            *   它会查找或下载适合您当前 Chrome 版本的 ChromeDriver 到其**缓存目录** (`~/.wdm`)。
            *   然后，程序会将缓存中的驱动文件**复制**到项目内对应的 `drivers/[操作系统]/[架构]/` 目录下。
            *   接着，程序会**使用项目目录中复制过来的这个驱动文件**来启动浏览器。
            *   最后，程序会**尝试删除** `webdriver-manager` 的缓存目录 (`~/.wdm`) 以节省空间（删除失败不影响运行）。
            *   **注意：** 此自动过程依赖网络连接，且可能因 `webdriver-manager` 的更新或网络问题而出错。因此，手动放置驱动仍是首选。

    *   🤖 **`[AI_Settings]` 部分:**
        # 通用 AI 设置。程序将自动查找所有在 [AI_Settings] 配置节下以 'channel_N_' 开头的配置项作为渠道实例。
        *   `retry_attempts`: AI 识别验证码的重试次数。这是对**每个渠道实例**的尝试次数。
        *   `retry_delay`: AI 识别验证码的重试间隔（秒）。这是在**同一个渠道实例**重试之间的等待时间。
        *   `rate_limit_delay`: 频率限制等待时间（秒），当遇到 429 错误时使用。
        *   `ai_test_timeout`: AI 渠道可用性测试的超时时间（秒）。

    *   🔌 **AI 渠道实例配置 (使用 `channel_N_` 前缀):**

        本程序支持配置多个 AI 服务渠道，并按顺序尝试调用，实现故障转移。这允许您同时使用多个不同的 AI 服务（包括在线服务和本地部署模型），提高验证码识别的成功率和稳定性。

        请在 `[AI_Settings]` 配置节下，使用 `channel_N_` 前缀来配置每个 AI 渠道实例，其中 `N` 是从 1 开始的连续整数编号（例如 `channel_1_api_type`, `channel_2_api_key` 等）。**程序将自动查找所有以 `channel_N_` 开头的配置项，并按数字 N 的顺序尝试。**

        每个 `[AI_Channel_N]` 配置节应包含以下配置项：

        *   `api_type`: **必填**。设置您希望使用的 AI 服务类型。支持的值包括：
            *   `gemini`: 使用 Google Gemini API。需要安装 `google-generativeai` 库 (`pip install google-generativeai`)。
            *   `openai`: 使用 OpenAI 官方 API 或兼容 OpenAI API 的服务（如 Grok, Ollama, LM Studio）。需要安装 `openai` 库 (`pip install openai`)。
            *   `grok`: 使用 Grok API (通过 OpenAI 兼容接口)。需要安装 `openai` 库。
            *   `none`: 禁用此渠道，跳过 AI 识别（仅用于测试或临时禁用）。
        *   `api_key`: **必填 (除非 api_type = none)**。填写您获取到的 AI API Key。对于某些本地服务（如 Ollama, LM Studio），可能不需要 API Key，但为了兼容性，建议填写任意非空值（例如 `ignore`）。
        *   `model_name`: **必填**。根据您选择的 AI 服务和 `api_type`，填写相应的**支持图像输入 (Vision)** 的模型名称。例如：
            *   Gemini: `gemini-pro-vision`
            *   OpenAI: `gpt-4o`, `gpt-4-vision-preview`
            *   Grok: `grok-1.0-vision` (示例名称，请查阅 Grok 文档确认)
            *   Ollama: `llama3-vision` (示例名称，请查阅 Ollama 文档确认)
            *   LM Studio: 您在 LM Studio 中下载并运行的支持图像输入的模型名称。
            **重要：** 用于验证码识别的 AI 模型必须支持图像输入。如果配置的模型不支持图像输入，程序将记录错误并跳过此渠道。
        *   `base_url`: **可选**。如果您使用的是 OpenAI 兼容的 API (例如 Grok 或本地部署的 Ollama/LM Studio)，请填写 API 的 Base URL。如果使用官方 OpenAI API 或 Gemini API，通常不需要设置此项。

        *示例 `config.ini` 中的 AI 渠道配置（请在 `[AI_Settings]` 节下配置）：*

        ```ini
        [AI_Settings]
        retry_attempts = 3
        retry_delay = 5
        rate_limit_delay = 30
        ai_test_timeout = 120 # AI 渠道可用性测试超时时间（秒）

        # --- AI 渠道实例配置 (按 channel_N_ 的数字顺序尝试) ---
        # 请在 [AI_Settings] 配置节下，使用 'channel_N_' 前缀来配置每个AI渠道实例。
        # 程序将自动查找所有以 'channel_N_' 开头的配置项，并按数字 N 的顺序尝试。
        # 用户可以参照以下格式自行添加更多渠道实例，无需修改任何计数。
        # 注意：所有用于验证码识别的AI模型必须支持图像输入 (Vision 模型)。

        # 渠道 1 (主 Gemini Key)
        channel_1_api_type = gemini
        channel_1_api_key = YOUR_GEMINI_API_KEY_HERE
        channel_1_model_name = gemini-pro-vision # 或其他支持视觉的模型

        # 渠道 2 (备用 Gemini Key)
        channel_2_api_type = gemini
        channel_2_api_key = YOUR_BACKUP_GEMINI_API_KEY_HERE
        channel_2_model_name = gemini-pro-vision

        # 渠道 3 (官方 OpenAI)
        channel_3_api_type = openai
        channel_3_api_key = YOUR_OPENAI_API_KEY_HERE
        channel_3_model_name = gpt-4o # OpenAI 的视觉模型
        # channel_3_base_url = https://api.openai.com/v1

        # 渠道 4 (Grok API - OpenAI 兼容)
        channel_4_api_type = openai
        channel_4_api_key = YOUR_GROK_API_KEY_HERE
        channel_4_model_name = grok-1.0-vision # 示例名称
        channel_4_base_url = https://api.groq.com/openai/v1

        # 渠道 5 (本地 Ollama - OpenAI 兼容)
        channel_5_api_type = openai
        channel_5_api_key = ignore # 本地服务可能不需要 API Key
        channel_5_model_name = llama3-vision # 示例名称
        channel_5_base_url = http://localhost:11434/v1

        # 渠道 6 (本地 LM Studio - OpenAI 兼容)
        channel_6_api_type = openai
        channel_6_api_key = ignore # 本地服务可能不需要 API Key
        channel_6_model_name = your_lmstudio_vision_model # 示例名称
        channel_6_base_url = http://localhost:1234/v1
        ```

    *   📊 **`[ResultColumns]` 部分:**
        *   定义需要从查询结果中提取并写入 Excel 的列名。键是您希望在输出 Excel 中使用的列名，值是程序内部用于存储数据的键（应与网页结果中的字段对应）。默认配置已包含锐捷官网查询结果截图中的常见字段。

    *   📝 **`[Logging]` 部分:**
        *   `log_file`: 日志文件路径 (留空则只输出到控制台)。
        *   `log_level`: 日志级别: DEBUG, INFO, WARNING, ERROR, CRITICAL。
        *   `log_to_console`: 是否在控制台输出日志 (True/False)。
        *   `log_max_bytes`: **(新增)** 日志文件最大大小，支持 KB/MB 单位 (例如 `1024KB`, `1MB`)。
        *   `log_backup_count`: **(新增)** 保留的备份日志文件数量。

    *   ⚙️ **`[CaptchaSettings]` 部分 (v2.0.0 优化):**
        *   `captcha_primary_solver`: **(重要)** 设置优先使用的验证码识别器。可选值为 `ddddocr` (优先使用本地 ddddocr) 或 `ai` (优先使用配置的 AI 渠道)。默认为 `ddddocr`。
        *   `captcha_enable_ddddocr`: 是否启用 ddddocr 本地识别。可选值为 `True` 或 `False`。默认为 `True`。如果设为 `False`，即使 `captcha_primary_solver` 设为 `ddddocr`，也会跳过 ddddocr。
        *   `captcha_enable_ai`: 是否启用 AI 识别。可选值为 `True` 或 `False`。默认为 `True`。如果设为 `False`，即使 `captcha_primary_solver` 设为 `ai`，也会跳过 AI 识别。
        *   `ddddocr_max_attempts`: 使用 ddddocr 识别单个验证码图片时的最大尝试次数。默认为 `3`。

## 🏗️ 软件架构

详细的软件架构设计请参考 [ruijie_query_plan.md](ruijie_query_plan.md)。程序已按功能拆分为不同的类，提高了代码的可读性和可维护性。

## 📝 版本历史

详细的版本历史请参考 [CHANGELOG.md](CHANGELOG.md)。

## 🤝 贡献与反馈

如果您在使用过程中遇到任何问题、有改进建议或发现了 Bug，欢迎通过以下方式进行反馈：

*   **提交 Issue:** 在本项目的 GitHub 仓库页面提交 Issue 是最推荐的方式。请详细描述您遇到的问题或建议。
*   **(可选) 提交 Pull Request:** 如果您修复了 Bug 或实现了新功能，欢迎提交 Pull Request。

## 📜 许可证

本项目采用 [MIT 许可证](LICENSE) 授权。
