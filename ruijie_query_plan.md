# 锐捷网络设备保修期批量查询工具开发计划

## 目标

开发一个Python程序，实现批量从锐捷官网（https://www.ruijie.com.cn/fw/bx/）查询锐捷网络设备序列号，并将查询结果自动回写到Excel文件中。程序应实现完全自动化，无需人工干预验证码输入，并使用配置的多个通用 AI API 渠道处理验证码。程序支持在启动时进行 AI 渠道可用性测试，以优先使用可用的接口，提高效率。

**重要提示：** 使用通用 AI API 处理验证码可能存在准确率和稳定性问题，且通常需要付费。请在使用前仔细阅读您选择的 AI 服务提供商的条款和定价，并自行承担潜在的风险。

## 软件架构思路

程序已进行模块化重构，代码分布在 `ruijie_query` 目录下，主要包含以下模块：

1.  **`config.py` (ConfigManager 类):** 负责读取和管理 `config.ini` 文件中的配置参数。**支持动态发现所有以 `[AI_Channel_]` 开头的配置节作为 AI 渠道实例。**
2.  **`data.py` (DataManager 类):** 负责使用 `pandas` 读取Excel文件中的序列号，准备存储结果的列，更新查询结果，以及将最终数据写回Excel文件。
3.  **`webdriver_manager.py` (WebDriverManager 类):** 负责初始化和管理 Selenium WebDriver。实现 ChromeDriver 的查找、自动下载、复制到项目目录、使用项目内驱动以及尝试删除缓存的完整管理流程。
4.  **`page_objects.py` (RuijieQueryPage 类):** 封装了与锐捷查询页面的交互逻辑。**结果解析逻辑 (`parse_query_result`) 已增强为动态解析表头。错误检查逻辑 (`_check_error_message`) 已增强。注意：此模块中的网页元素定位器仍需根据实际页面结构进行手动完善。**
5.  **`captcha_solver.py` (CaptchaSolver 类):** 负责处理验证码识别。**包含 AI 渠道可用性测试、AI 响应文本清理、重试和错误处理逻辑。**
6.  **`app.py` (RuijieQueryApp 类):** 主应用程序类，协调各模块。**包含可配置的查询/验证码重试、基于 `save_interval` 的智能保存逻辑、AI 渠道可用性测试调用、补漏机制等。**
7.  **`main.py`:** 程序的入口点。
8.  **日志记录:** 使用 Python 的 `logging` 模块。**支持通过 `config.ini` 配置日志级别、文件路径、控制台输出、文件大小轮转 (`log_max_bytes`) 和备份数量 (`log_backup_count`)。**

## 架构图

```mermaid
graph TD
    A[开始 main.py] --> B(创建 ConfigManager);
    B --> C(创建 RuijieQueryApp);
    C --> D(运行 app.run());
    D --> E(设置日志);
    E --> F(加载 Excel 数据 - DataManager);
    F -- 数据 --> G;
    F -- 失败 --> Z[结束];
    G(初始化 WebDriver - WebDriverManager) --> H;
    G -- 失败 --> Z;
    H(初始化 PageObjects - RuijieQueryPage) --> I(测试 AI 渠道可用性);
    I -- 可用渠道 --> J{遍历序列号};
    I -- 无可用渠道 --> Z; % 没有可用渠道，程序结束
    J -- 有序列号 --> K(处理单个查询 _process_single_query);
    J -- 无序列号/完成 --> T(检查未查询项);

    subgraph 单个查询流程 _process_single_query
        direction LR
        K1(打开页面) --> K2(输入SN);
        K2 --> K3(获取验证码图片);
        K3 --> K4(识别验证码 - CaptchaSolver);
        K4 -- 成功 --> K5;
        K4 -- 失败 --> K9(记录验证码失败);
        K5(输入验证码) --> K6(提交查询);
        K6 --> K7(等待结果);
        K7 -- 成功 --> K8(解析结果 - RuijieQueryPage);
        K7 -- 超时/失败 --> K10(记录超时/错误);
        K8 -- 成功 --> K11(返回结果);
        K8 -- 解析失败/错误 --> K10;
        K9 --> K11;
        K10 --> K11;
    end

    K --> L(更新结果 - DataManager);
    L --> M(保存数据 - DataManager);
    M --> N(查询延时);
    N --> J;

    T -- 有未查询项 --> O(创建未查询DataFrame);
    T -- 无未查询项 --> Y(保存最终数据);
    O --> P(_process_queries 补漏);
    P --> Y;

    Y(保存最终数据 - DataManager) --> X(关闭 WebDriver - WebDriverManager);
    X --> Z;

```

## 详细计划步骤 (已根据当前实现更新)

1.  **环境准备：**
    *   安装 Python 3.6+。
    *   安装 Chrome 浏览器。
    *   运行 `pip install -r requirements.txt` 安装所有依赖。
    *   根据需要手动安装 AI 库 (如 `google-generativeai` 或 `openai`)。
2.  **准备Excel文件 (`Serial-Number.xlsx`)：**
    *   项目根目录下已包含一个名为 `Serial-Number.xlsx` 的模板文件。
    *   打开此文件，找到 `config.ini` 中 `sn_column_name` 指定的列（默认为 "Serial Number"）。
    *   **将您需要查询的锐捷设备序列号填入该列，每个序列号占一行。**
    *   确保 `config.ini` 中的 `excel_file_path` 指向此文件（或您修改后的文件），并且 `sheet_name` 配置正确。
3.  **配置 `config.ini`：**
    *   **重要：** 从 `config.example.ini` 复制创建 `config.ini` 并填入您自己的 API 密钥。
    *   检查并配置 `[General]` 部分（`excel_file_path`, `sheet_name`, `sn_column_name`, `query_delay`, `save_interval`, **`max_query_attempts`**, **`max_captcha_retries`**）。`chrome_driver_path` 可选。驱动查找顺序：`config.ini` -> `drivers/` -> 自动下载/复制/清理。
    *   配置 `[AI_Settings]` 部分（`retry_attempts`, `retry_delay`, `rate_limit_delay`, `ai_test_timeout`）。
    *   **为每个 AI 渠道实例创建 `channel_N_` 配置项** (例如 `channel_1_api_type`, `channel_1_api_key` 等)。程序将自动发现并按数字顺序尝试这些渠道。
    *   检查 `[ResultColumns]` 部分的映射关系。
    *   配置 `[Logging]` 部分（`log_file`, `log_level`, `log_to_console`, **`log_max_bytes`**, **`log_backup_count`**）。
4.  **运行程序：**
    *   执行 `python main.py`。
    *   **程序将在启动时自动测试配置的 AI 渠道可用性，并只使用可用的渠道进行验证码识别。**
5.  **手动完善 (重要)：**
    *   **检查并调整 `ruijie_query/page_objects.py` 中的网页元素定位器**，确保它们与锐捷官网当前的 HTML 结构匹配。
    *   **检查并调整 `ruijie_query/page_objects.py` 中的 `parse_query_result` 方法**，确认动态表头解析逻辑与实际表格匹配。
    *   **检查并调整 `ruijie_query/page_objects.py` 中的 `_check_error_message` 方法**，确认能准确捕获页面上的错误提示。
6.  **测试与调试：**
    *   使用少量序列号进行测试。
    *   根据日志输出和 Excel 结果排查问题。

## 代码模块说明 (已实现)

*   **`config.py`:** `ConfigManager` 类。**支持动态发现 AI 渠道，解析日志轮转配置。**
*   **`data.py`:** `DataManager` 类。
*   **`webdriver_manager.py`:** `WebDriverManager` 类。**实现完整的驱动管理流程。**
*   **`page_objects.py`:** `RuijieQueryPage` 类。**结果解析动态化，错误检查增强。**
*   **`captcha_solver.py`:** `CaptchaSolver` 类。**包含 AI 渠道可用性测试、响应清理。**
*   **`app.py`:** `RuijieQueryApp` 类。**包含可配置重试、智能保存、AI 测试调用。**
*   **`main.py`:** 程序入口。
*   **日志:** 使用 `logging` 模块，**支持文件轮转配置**。

## 错误处理与重试 (已实现)

*   使用 `try...except` 捕获关键步骤的异常。
*   错误信息记录到日志和 Excel 的 `查询状态` 列。
*   `CaptchaSolver` 中包含针对 AI API 调用的重试和指数退避逻辑。**AI 响应文本会被自动清理。**
*   `RuijieQueryApp` 中包含**可配置的查询重试 (`max_query_attempts`) 和验证码重试 (`max_captcha_retries`)**。包含补漏机制。
*   **AI 渠道可用性测试**会在程序启动时识别并跳过不可用的渠道。
*   **WebDriverManager** 实现完整的驱动管理。
*   **PageObjects** 中增强了表格解析和错误检查的鲁棒性。
*   **日志支持文件轮转**，防止文件过大。
*   **保存逻辑优化**，根据 `save_interval` 执行，避免频繁写入。

## 集成 ddddocr 计划

**目标：**

1.  引入 `ddddocr` 作为本地验证码识别选项。
2.  允许用户在 `config.ini` 中配置优先使用 `ddddocr` 还是 AI。
3.  允许用户在 `config.ini` 中独立启用或禁用 `ddddocr` 和 AI。
4.  实现识别逻辑：优先尝试配置的首选方法，如果失败或禁用，则尝试备用方法（如果启用）。

**实施步骤：**

1.  **更新依赖 (`requirements.txt`)**:
    *   添加 `ddddocr` 到 `requirements.txt` 文件中。

2.  **修改配置文件 (`config.example.ini` 和 `config.ini`)**:
    *   创建一个新的 `[CaptchaSettings]` 配置节。
    *   添加以下配置项：
        *   `captcha_primary_solver = ddddocr`  (选项: 'ddddocr', 'ai'; 默认 'ddddocr')
        *   `captcha_enable_ddddocr = True`   (选项: True, False; 默认 True)
        *   `captcha_enable_ai = True`        (选项: True, False; 默认 True)
        *   `ddddocr_max_attempts = 3`        (ddddocr 识别的最大尝试次数)
    *   更新 `config.example.ini` 以包含这些新选项和注释。用户需要相应地更新 `config.ini`。

3.  **修改配置管理器 (`ruijie_query/config.py`)**:
    *   在 `ConfigManager` 类中添加一个新的方法 `get_captcha_config()` 来读取 `[CaptchaSettings]` 配置节中的新选项，并进行适当的类型转换和默认值处理。

4.  **修改验证码求解器 (`ruijie_query/captcha_solver.py`)**:
    *   **导入**: 导入 `ddddocr` 库。
    *   **初始化 (`__init__`)**:
        *   接收新的 `captcha_config` 参数。
        *   根据 `captcha_enable_ddddocr` 配置，尝试初始化 `ddddocr.DdddOcr()` 实例。如果失败（例如，缺少模型文件），记录警告并内部禁用 ddddocr。
        *   存储 `captcha_config` 以供后续使用。
    *   **核心逻辑 (`solve_captcha`)**:
        *   重构此方法以实现新的识别策略。
        *   根据 `captcha_primary_solver` 决定首先调用哪个识别器 (`_solve_with_ddddocr` 或 `_solve_with_ai`)。
        *   在调用任何识别器之前，检查其对应的 `enable` 配置 (`captcha_enable_ddddocr` 或 `captcha_enable_ai`) 以及是否已成功初始化 (对于 ddddocr)。
        *   如果首选识别器启用并成功识别，返回结果。
        *   如果首选识别器失败、被禁用或未初始化，则检查备用识别器是否启用。
        *   如果备用识别器启用，则尝试使用它进行识别。
        *   如果两个识别器都失败或都被禁用/未初始化，则返回 `None`。
    *   **新方法 (`_solve_with_ddddocr`)**:
        *   创建一个私有方法来封装调用 `ddddocr` 实例进行识别的逻辑。
        *   包含基于 `ddddocr_max_attempts` 的重试逻辑和错误处理。
    *   **重构 AI 逻辑 (`_solve_with_ai`)**:
        *   将现有的 AI 识别逻辑（包括渠道遍历和重试）移到一个新的私有方法 `_solve_with_ai` 中。
    *   **日志**: 更新日志记录，清晰地显示正在使用哪个识别器、尝试次数以及结果。

5.  **更新主应用逻辑 (例如 `main.py` 或 `ruijie_query/app.py`)**:
    *   修改创建 `CaptchaSolver` 实例的代码，从 `ConfigManager` 获取 `captcha_config` 并传递给 `CaptchaSolver` 的构造函数。

**预期结果：**

*   项目将能够使用 `ddddocr` 进行本地验证码识别。
*   用户可以通过 `config.ini` 灵活控制验证码识别策略（优先顺序、启用/禁用）。
*   代码结构将更清晰，将不同的识别逻辑分离开。
