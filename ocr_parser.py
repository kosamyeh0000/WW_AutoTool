import concurrent.futures
import os
import re


class OCRParser:

    def __init__(self):
        self._reader_gpu = None
        self._reader_cpu = None

    def _is_cuda_supported(self) -> bool:
        """檢查是否有支援的 CUDA 裝置 (過濾 sm_120 避免 5070 Ti 崩潰)"""
        try:
            import torch

            if not torch.cuda.is_available():
                return False
            major, minor = torch.cuda.get_device_capability(0)
            arch_score = major * 10 + minor
            if arch_score > 90:
                print("GPU太好，不支援的架構，降級使用 CPU", flush=True)
                return False
            return True
        except Exception:
            return False

    def _get_reader(self, use_gpu: bool):
        import easyocr

        if use_gpu:
            if self._reader_gpu is None:
                print(
                    "[OCR] 首次載入 GPU 模型 (EasyOCR)...", flush=True
                )
                self._reader_gpu = easyocr.Reader(['en'], gpu=True)
            return self._reader_gpu
        else:
            if self._reader_cpu is None:
                print(
                    "[OCR] 首次載入 CPU 模型 (EasyOCR)...", flush=True
                )
                self._reader_cpu = easyocr.Reader(['en'], gpu=False)
            return self._reader_cpu

    def _execute_read(self, img_path: str, use_gpu: bool):
        reader = self._get_reader(use_gpu=use_gpu)
        return reader.readtext(img_path)

    def extract_status(self, img_path: str, timeout_sec: int = 120) -> dict:
        """提供給 main_gui.py 呼叫的主進入點"""
        if not os.path.exists(img_path):
            print(f"[OCR] 錯誤：找不到截圖檔案 {img_path}", flush=True)
            return {}

        can_use_gpu = self._is_cuda_supported()
        results = None

        if can_use_gpu:
            print(
                f"[OCR] 使用 GPU 辨識 (超時: {timeout_sec}s)...",
                flush=True,
            )
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=1
            ) as executor:
                future = executor.submit(self._execute_read, img_path, True)
                try:
                    results = future.result(timeout=timeout_sec)
                except Exception as e:
                    print(f"[OCR 警告] GPU 執行失敗 ({e})，降級切換 CPU")
        else:
            print("[OCR] 使用 CPU 進行文字辨識...")

        if results is None:
            try:
                results = self._execute_read(img_path, use_gpu=False)
            except Exception as e:
                print(f"[OCR 錯誤] CPU 辨識異常: {e}")
                return {}

        # 完整對齊 main_gui 與 Discord payload 所需的 key
        status = {
            "level": "80",
            "stamina": 0,
            "max_stamina": 240,
            "reserve_stamina": 0,
            "activity": 0,  # 活躍度 (100/100)
            "max_activity": 100,
            "tower": 0,
            "data_bank": "",
            "raw_texts": [text for _, text, _ in results],
        }

        print("\n--- [OCR 原始辨識文字] ---")
        for bbox, text, prob in results:
            print(f"'{text}' (信心度: {prob:.2f})")
        print("--------------------------\n")

        for bbox, text, prob in results:
            clean = text.replace(" ", "")

            # 1. 主體力 (例如 46/240)
            if "/240" in clean:
                digits = re.findall(r"(\d+)/240", clean)
                if digits:
                    status["stamina"] = int(digits[0])

            # 2. 儲備體力 (例如 85 /480)
            elif "/480" in clean:
                digits = re.findall(r"(\d+)/480", clean)
                if digits:
                    status["reserve_stamina"] = int(digits[0])

            # 3. 每日活躍度 (例如 100/100)
            elif "/100" in clean:
                digits = re.findall(r"(\d+)/100", clean)
                if digits:
                    status["activity"] = int(digits[0])

            # 4. 數據塢經驗 (例如 7700/12000)
            elif "/12000" in clean:
                status["data_bank"] = clean

        # 若主體力沒抓到，備用方案
        if status["stamina"] == 0:
            for bbox, text, prob in results:
                clean = text.replace(" ", "")
                if "/" in clean and "/100" not in clean and "/480" not in clean:
                    parts = clean.split("/")
                    digits = re.findall(r"\d+", parts[0])
                    if digits:
                        val = int(digits[0])
                        if 0 <= val <= 240:
                            status["stamina"] = val
                            break

        print(f"[OCR 解析成功結果] {status}")
        return status

    # 相容舊版名稱
    def parse_stamina(self, img_path: str, timeout_sec: int = 120) -> int:
        data = self.extract_status(img_path, timeout_sec)
        return data.get("stamina", 0)


# 類別別名相容
StatusOCR = OCRParser