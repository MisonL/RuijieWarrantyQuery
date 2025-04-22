# --- 主程序入口 ---
if __name__ == "__main__":
    from ruijie_query.config import ConfigManager
    from ruijie_query.app import RuijieQueryApp

    config_manager = ConfigManager()
    app = RuijieQueryApp(config_manager)
    app.run()
