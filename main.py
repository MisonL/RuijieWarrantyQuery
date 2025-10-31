# --- 主程序入口 ---
if __name__ == "__main__":
    import sys
    from pathlib import Path

    # 添加src目录到Python路径以支持新的模块结构
    current_dir = Path(__file__).parent
    src_dir = current_dir / "src"
    sys.path.insert(0, str(src_dir))

    import ruijie_query # 导入包以获取版本号
    from ruijie_query.config import ConfigManager
    from ruijie_query.core.app import RuijieQueryApp

    print(f"--- 锐捷网络设备保修期批量查询工具 v{ruijie_query.__version__} ---") # 打印版本号

    config_manager = ConfigManager()
    app = RuijieQueryApp(config_manager)

    # 在程序结束后输出性能报告
    try:
        app.run()
    finally:
        from ruijie_query.monitoring import get_monitor
        monitor = get_monitor()
        monitor.log_performance_report()
