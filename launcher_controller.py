import os
import subprocess
import time
from PIL import ImageGrab
import pyautogui
import pygetwindow as gw


class LauncherController:

    def __init__(self, launcher_path, window_keyword="鳴潮", exclude_title=""):
        self.launcher_path = launcher_path
        self.window_keyword = window_keyword
        self.exclude_title = exclude_title

    def get_window(self):
        """尋找啟動器視窗，若無則啟動"""
        candidates = [
            w
            for w in gw.getWindowsWithTitle(self.window_keyword)
            if w.visible and w.title != self.exclude_title
        ]
        if not candidates:
            if not os.path.exists(self.launcher_path):
                raise FileNotFoundError(f"找不到啟動器: {self.launcher_path}")
            subprocess.Popen(self.launcher_path)
            time.sleep(6)
            candidates = [
                w
                for w in gw.getWindowsWithTitle(self.window_keyword)
                if w.visible and w.title != self.exclude_title
            ]

        if not candidates:
            raise RuntimeError("無法定位鳴潮啟動器視窗")

        win = candidates[0]
        if win.isMinimized:
            win.restore()
        win.activate()
        time.sleep(0.5)
        return win

    def click_refresh(self, ratio_x, ratio_y):
        """點擊指定比例的按鈕"""
        win = self.get_window()
        target_x = win.left + int(win.width * ratio_x)
        target_y = win.top + int(win.height * ratio_y)
        pyautogui.click(target_x, target_y)
        return target_x, target_y

    def capture_card(self, rect_ratio, save_path="launcher_capture.png"):
        """依照比例截圖指定範圍"""
        win = self.get_window()
        bbox = (
            win.left + int(win.width * rect_ratio["left"]),
            win.top + int(win.height * rect_ratio["top"]),
            win.left + int(win.width * rect_ratio["right"]),
            win.top + int(win.height * rect_ratio["bottom"]),
        )
        img = ImageGrab.grab(bbox=bbox)
        img.save(save_path)
        return save_path