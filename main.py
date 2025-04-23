# --- 主程序入口 ---
if __name__ == "__main__":
    import ruijie_query # 导入包以获取版本号
    from ruijie_query.config import ConfigManager
    from ruijie_query.app import RuijieQueryApp

    print(f"--- 锐捷网络设备保修期批量查询工具 v{ruijie_query.__version__} ---") # 打印版本号

    config_manager = ConfigManager()
    app = RuijieQueryApp(config_manager)
    app.run()
