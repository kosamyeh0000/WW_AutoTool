import os
import requests


class DiscordNotifier:

    def __init__(self, webhook_url):
        self.webhook_url = webhook_url

    def send_text(self, message):
        """僅推送純文字訊息至 Discord"""
        if not self.webhook_url.startswith(
            "https://discord.com/api/webhooks/"
        ):
            raise ValueError("無效的 Webhook URL")

        payload = {"content": message}
        res = requests.post(self.webhook_url, json=payload, timeout=10)
        return res.status_code in (200, 204)

    def send_image(self, file_path, message="📊 **鳴潮體力狀態回報**"):
        """推送圖片與文字訊息至 Discord"""
        if not self.webhook_url.startswith(
            "https://discord.com/api/webhooks/"
        ):
            raise ValueError("無效的 Webhook URL")

        try:
            with open(file_path, "rb") as f:
                files = {"file": (file_path, f, "image/png")}
                res = requests.post(
                    self.webhook_url,
                    data={"content": message},
                    files=files,
                    timeout=10,
                )
                return res.status_code in (200, 204)
        finally:
            if os.path.exists(file_path):
                os.remove(file_path)