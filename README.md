# ⚡ 锐捷保修查询工具

<div align="center">

[![v2.0.0](https://img.shields.io/badge/Version-v2.0.0-blue)](https://github.com/MisonL/RuijieWarrantyQuery)
[![Python](https://img.shields.io/badge/Python-3.8+-green)](https://python.org)
[![MIT](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

**95%性能提升** • **批量自动化** • **AI智能识别**

</div>

---

## 🎯 一句话介绍

批量查询锐捷网络设备保修信息的自动化工具，从Excel到Excel，无需手动操作。

## ✨ 核心功能

| 功能 | 说明 |
|------|------|
| 📊 **批量处理** | Excel导入 → 自动查询 → Excel导出 |
| 🤖 **智能识别** | ddddocr本地识别 + 多AI渠道备选 |
| ⚡ **极速优化** | 智能退出 + WebDriver优化 + 快速失败 |

## 🚀 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置config.ini（填入真实API密钥）
# 3. 运行
python main.py
```

**就这3步！** 其他配置都有默认值，开箱即用。

## 📈 性能对比

| 场景 | v1.1.0 | v2.0.0 | 提升 |
|------|--------|--------|------|
| **总耗时** | 9.91秒 | 0.50秒 | **95%** |
| **WebDriver启动** | 8.28秒 | 2.3秒 | **72%** |
| **无序列号场景** | 完整流程 | 快速退出 | **99%** |

**真实数据：** 在相同数据集上，v2.0.0的执行时间仅为v1.1.0的5%。

## 🔧 配置示例

```ini
[General]
excel_file_path = Serial-Number.xlsx
sn_column_name = Serial Number
query_delay = 2

[CaptchaSettings]
captcha_primary_solver = ddddocr
captcha_enable_ddddocr = True

[AI_Settings]
ai_test_timeout = 10

# 填入真实API密钥（示例）
channel_1_api_key = sk-your-real-gemini-key
channel_2_api_key = sk-your-real-openai-key
```

## 🎨 架构亮点

- **🏗️ 模块化设计** - `src/ruijie_query/` 包结构
- **🧪 完整测试** - `tests/` 单元测试套件
- **📊 智能监控** - 轻量级性能追踪
- **🔧 现代配置** - `pyproject.toml` 项目管理

## 📚 详细文档

| 文档 | 内容 |
|------|------|
| [🔧 配置说明](https://github.com/MisonL/RuijieWarrantyQuery#配置说明) | config.ini 详细参数 |
| [📋 完整变更](CHANGELOG.md) | v1.1.0 → v2.0.0 更新日志 |
| [🚀 发布说明](RELEASE_NOTES_v2.0.0.md) | v2.0.0 重大特性详解 |
| [⚡ 性能优化](PERFORMANCE_OPTIMIZATION_SUMMARY.md) | 95%性能提升技术细节 |

## 🏆 v2.0.0 重大更新

### ⚡ 智能优化
- **提前退出** - 无序列号时跳过WebDriver启动
- **快速失败** - 占位符API key自动跳过
- **启动加速** - Chrome无头模式 + 禁用图片/日志

### 🏗️ 架构升级
- **完全重构** - 现代Python包结构
- **测试覆盖** - 新增60+单元测试
- **类型安全** - 全面类型提示

## ⚠️ 重要提醒

1. **API密钥** - 必须使用真实API密钥（示例密钥会被自动跳过）
2. **网络稳定** - 确保能访问锐捷官网和AI服务
3. **Excel格式** - 第一列必须是序列号，标题行可选

## 📞 支持

- 🐛 **Bug报告** - [GitHub Issues](https://github.com/MisonL/RuijieWarrantyQuery/issues)
- 💡 **功能建议** - [GitHub Discussions](https://github.com/MisonL/RuijieWarrantyQuery/discussions)
- 📖 **详细文档** - 查看项目Wiki

---

<div align="center">

**让查询更高效，让工作更智能** 🤖

[⬆ 回到顶部](#-锐捷保修查询工具)

</div>