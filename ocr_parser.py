# ocr_parser.py
import re
from PIL import Image
import easyocr

class StatusOCR:
    def __init__(self):
        # 使用 CPU 運算，穩定且免除顯卡衝突
        self.reader = easyocr.Reader(['ch_tra', 'en'], gpu=False)

    def extract_status(self, image_path):
        """
        傳入卡片截圖路徑，僅提取體力與每日活躍度
        """
        results = self.reader.readtext(image_path, detail=0)
        full_text = " ".join(results)

        # 匹配 XX/240 (體力)
        stamina_match = re.search(r'(\d{1,3})\s*/\s*240', full_text)
        # 匹配 XX/100 (每日活躍度)
        activity_match = re.search(r'(\d{1,3})\s*/\s*100', full_text)

        stamina = f"{stamina_match.group(1)}/240" if stamina_match else "未辨識到"
        activity = f"{activity_match.group(1)}/100" if activity_match else "未辨識到"

        return {
            "stamina": stamina,
            "activity": activity,
            "raw_text": full_text
        }