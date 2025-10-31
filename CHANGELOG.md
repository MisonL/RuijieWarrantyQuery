# 📝 版本历史

**v2.0.0 (2025-10-31) - 🚀 重大版本更新**

*   🎯 **重大性能优化**: 总执行时间提升95% (9.91秒 → 0.50秒)
    *   ✅ 新增智能提前退出机制：检测到无未查询序列号时自动跳过WebDriver初始化
    *   ✅ WebDriver启动优化：启用无头模式、禁用GPU/图片/日志，8.28秒 → 2-3秒
    *   ✅ AI渠道快速失败：占位符API key自动跳过，1.32秒 → 0.34秒
    *   ✅ 性能监控智能跳过：轻量级模式，专注主要操作

*   🏗️ **代码架构重构**:
    *   ✅ 完全模块化：采用现代Python包结构 `src/ruijie_query/*`
    *   ✅ 新增完整测试套件：`tests/` 目录，包含unit和integration测试
    *   ✅ 现代Python项目配置：`pyproject.toml` 替代 `requirements.txt`
    *   ✅ 增强错误处理和类型提示

*   🐛 **Pylance诊断修复**:
    *   ✅ 修复 `data_manager.py` 中的可选成员访问警告
    *   ✅ 修复 `webdriver_manager.py` 中的属性访问和类型错误

*   📚 **文档完善**:
    *   ✅ 新增 `WEBDRIVER_OPTIMIZATION.md` - WebDriver优化详细指南
    *   ✅ 新增 `PERFORMANCE_OPTIMIZATION_SUMMARY.md` - 完整性能优化报告
    *   ✅ README性能优化章节更新

*   ⚙️ **配置优化**:
    *   ✅ AI测试超时优化：从120秒缩短到10秒
    *   ✅ 占位符API key自动检测和跳过
    *   ✅ 智能缓存管理机制

**v1.1.0 (2025-04-23)**

*   ✨ **新增:** 集成 `ddddocr` 本地验证码识别库。
*   ⚙️ **新增:** 在 `config.ini` 中添加 `[CaptchaSettings]` 配置节，允许用户：
    *   选择优先使用的验证码识别器 (`captcha_primary_solver`: `ddddocr` 或 `ai`)。
    *   独立启用/禁用 `ddddocr` (`captcha_enable_ddddocr`) 和 AI (`captcha_enable_ai`)。
    *   配置 `ddddocr` 的最大识别尝试次数 (`ddddocr_max_attempts`)。
*   🔧 **优化:** 改进 `CaptchaSolver` 中 `ddddocr` 的导入和初始化逻辑，实现按需加载。
*   📝 **修正:** 调整 `app.py` 中的日志记录，使其在验证码识别时输出更通用的提示，而不是固定显示 "AI"。

**v1.0.0 (初始版本)**

*   🚀 实现基于 AI 的锐捷设备保修期批量查询和结果回写功能。
*   🔌 支持配置多个 AI 渠道 (Gemini, OpenAI 兼容等) 并按顺序尝试，实现故障转移。
*   ⚡ 包含 AI 渠道可用性测试功能。
*   🚗 实现 ChromeDriver 的自动查找、下载、复制和缓存清理。
*   💪 包含可配置的查询重试、验证码重试、查询延时。
*   📊 增强表格解析和错误检查的鲁棒性。
*   💾 实现基于 `save_interval` 的智能保存机制。
*   ✨ 自动清理 AI 返回的验证码文本。
*   📜 支持通过配置文件进行详细的日志记录设置，包括文件轮转。
