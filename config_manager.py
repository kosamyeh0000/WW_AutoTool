import json
import os
import shutil

CONFIG_FILE = "config.json"
EXAMPLE_FILE = "config.example.json"

DEFAULT_CONFIG = {
    "launcher_path": "",
    "webhook_url": "",
    "card_rect": {
        "left": 0.032,
        "top": 0.688,
        "right": 0.283,
        "bottom": 0.944,
    },
    "refresh_btn": {"x": 0.266, "y": 0.725},
    "scheduled_tasks": [],
}


class ConfigManager:

    @staticmethod
    def load():
        """讀取本地 config.json，若不存在則從範本生成"""
        if not os.path.exists(CONFIG_FILE):
            if os.path.exists(EXAMPLE_FILE):
                shutil.copy(EXAMPLE_FILE, CONFIG_FILE)
            else:
                ConfigManager.save(DEFAULT_CONFIG)
            return ConfigManager.load()

        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for k, v in DEFAULT_CONFIG.items():
                    if k not in data:
                        data[k] = v
                return data
        except Exception:
            return DEFAULT_CONFIG.copy()

    @staticmethod
    def save(config_data):
        """將設定儲存至本地 config.json"""
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=4, ensure_ascii=False)