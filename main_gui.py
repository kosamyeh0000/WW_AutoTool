import ctypes
from datetime import datetime, timedelta
import os
import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk
from config_manager import ConfigManager
from discord_notifier import DiscordNotifier
from launcher_controller import LauncherController
from ocr_parser import StatusOCR

try:
    ctypes.windll.user32.SetProcessDPIAware()
except Exception:
    pass

GUI_TITLE = "WW_AutoTool_Modular"


class CreateTaskDialog(tk.Toplevel):

    def __init__(self, parent, callback):
        super().__init__(parent)
        self.title("創建計劃任務")
        self.geometry("380x300")
        self.resizable(False, False)
        self.callback = callback

        self.transient(parent)
        self.grab_set()

        self._build_ui()

    def _build_ui(self):
        pad = {"padx": 15, "pady": 8}

        ttk.Label(self, text="選擇任務:").grid(
            row=0, column=0, sticky="w", **pad
        )
        self.cb_task = ttk.Combobox(
            self,
            values=[
                "💬 僅辨識數據發送 (無截圖)",
                "🔍 辨識數值並推送 (含截圖)",
                "🔄 刷新並截圖發送",
                "🔄 僅刷新卡片",
                "📸 僅截圖發送",
            ],
            state="readonly",
            width=24,
        )
        self.cb_task.current(0)
        self.cb_task.grid(row=0, column=1, sticky="w", **pad)

        ttk.Label(self, text="觸發類型:").grid(
            row=1, column=0, sticky="w", **pad
        )
        self.cb_type = ttk.Combobox(
            self,
            values=["每天 (指定時間)", "間隔 (每隔數分鐘)"],
            state="readonly",
            width=24,
        )
        self.cb_type.current(0)
        self.cb_type.grid(row=1, column=1, sticky="w", **pad)
        self.cb_type.bind("<<ComboboxSelected>>", self._on_type_changed)

        self.lbl_time = ttk.Label(self, text="開始時間:")
        self.lbl_time.grid(row=2, column=0, sticky="w", **pad)

        self.time_frame = ttk.Frame(self)
        self.time_frame.grid(row=2, column=1, sticky="w", **pad)

        self.sp_hour = ttk.Spinbox(
            self.time_frame, from_=0, to=23, width=4, format="%02.0f"
        )
        self.sp_hour.set(time.strftime("%H"))
        self.sp_hour.pack(side="left")
        self.lbl_colon = ttk.Label(self.time_frame, text=" : ")
        self.lbl_colon.pack(side="left")
        self.sp_min = ttk.Spinbox(
            self.time_frame, from_=0, to=59, width=4, format="%02.0f"
        )
        self.sp_min.set(time.strftime("%M"))
        self.sp_min.pack(side="left")

        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=20)

        ttk.Button(btn_frame, text="創建", command=self._confirm, width=12).pack(
            side="left", padx=10
        )
        ttk.Button(btn_frame, text="取消", command=self.destroy, width=12).pack(
            side="left", padx=10
        )

    def _on_type_changed(self, e):
        if self.cb_type.get() == "間隔 (每隔數分鐘)":
            self.lbl_time.config(text="間隔時間:")
            self.lbl_colon.pack_forget()
            self.sp_min.pack_forget()
            self.sp_hour.config(from_=1, to=1440)
            self.sp_hour.set(60)
        else:
            self.lbl_time.config(text="開始時間:")
            self.sp_hour.config(from_=0, to=23)
            self.sp_hour.set(time.strftime("%H"))
            self.lbl_colon.pack(side="left")
            self.sp_min.pack(side="left")

    def _confirm(self):
        task_name = self.cb_task.get()
        trigger_type = self.cb_type.get()
        now = datetime.now()

        if trigger_type == "每天 (指定時間)":
            h = int(self.sp_hour.get())
            m = int(self.sp_min.get())
            next_run = now.replace(hour=h, minute=m, second=0, microsecond=0)
            if next_run <= now:
                next_run += timedelta(days=1)
            meta = {"hour": h, "minute": m}
        else:
            mins = int(self.sp_hour.get())
            next_run = now + timedelta(minutes=mins)
            meta = {"interval_mins": mins}

        task_data = {
            "name": task_name,
            "trigger_type": trigger_type,
            "next_run": next_run.strftime("%Y-%m-%d %H:%M:%S"),
            "enabled": True,
            "meta": meta,
        }
        self.callback(task_data)
        self.destroy()


class AppGUI:

    def __init__(self, root):
        self.root = root
        self.root.title(GUI_TITLE)
        self.root.geometry("860x720")
        self.root.resizable(False, False)

        self.cfg = ConfigManager.load()
        self.tasks = self.cfg.get("scheduled_tasks", [])

        card = self.cfg.get(
            "card_rect",
            {"left": 0.032, "top": 0.688, "right": 0.283, "bottom": 0.944},
        )
        btn = self.cfg.get("refresh_btn", {"x": 0.266, "y": 0.725})

        self.var_card_l = tk.DoubleVar(value=card["left"])
        self.var_card_t = tk.DoubleVar(value=card["top"])
        self.var_card_r = tk.DoubleVar(value=card["right"])
        self.var_card_b = tk.DoubleVar(value=card["bottom"])

        self.var_btn_x = tk.DoubleVar(value=btn["x"])
        self.var_btn_y = tk.DoubleVar(value=btn["y"])

        self.controller = LauncherController(
            launcher_path=self.cfg.get("launcher_path", ""), exclude_title=GUI_TITLE
        )
        self.notifier = DiscordNotifier(webhook_url=self.cfg.get("webhook_url", ""))
        self.ocr = StatusOCR()

        self._build_ui()

        self.is_running = True
        self.worker_thread = threading.Thread(
            target=self._scheduler_loop, daemon=True
        )
        self.worker_thread.start()

    def _build_ui(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=5)

        self.tab_schedule = ttk.Frame(self.notebook, padding=5)
        self.notebook.add(self.tab_schedule, text=" 📅 計劃任務 ")
        self._build_schedule_tab()

        self.tab_settings = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.tab_settings, text=" ⚙️ 設定與座標校準 ")
        self._build_settings_tab()

        frame_log = ttk.LabelFrame(self.root, text="執行日誌", padding=10)
        frame_log.pack(fill="x", padx=10, pady=5)
        self.txt_log = tk.Text(frame_log, height=6, state="disabled")
        self.txt_log.pack(fill="both", expand=True)

    def _build_schedule_tab(self):
        toolbar = ttk.Frame(self.tab_schedule)
        toolbar.pack(fill="x", pady=5)

        ttk.Button(
            toolbar, text="➕ 創建任務", command=self.open_create_dialog
        ).pack(side="left", padx=3)
        # 新增：純文字數據發送按鈕
        ttk.Button(
            toolbar,
            text="💬 僅辨識數據發送",
            command=lambda: self._async(self.on_ocr_text_only),
        ).pack(side="left", padx=3)
        ttk.Button(
            toolbar,
            text="🔍 辨識+截圖發送",
            command=lambda: self._async(self.on_ocr_and_send),
        ).pack(side="left", padx=3)
        ttk.Button(
            toolbar, text="🔄 手動刷新", command=lambda: self._async(self.on_refresh)
        ).pack(side="left", padx=3)
        ttk.Button(
            toolbar, text="📸 手動截圖", command=lambda: self._async(self.on_capture)
        ).pack(side="left", padx=3)

        cols = ("idx", "name", "status", "type", "next_run")
        self.tree = ttk.Treeview(
            self.tab_schedule, columns=cols, show="headings", height=14
        )
        self.tree.heading("idx", text="#")
        self.tree.heading("name", text="任務名稱")
        self.tree.heading("status", text="狀態")
        self.tree.heading("type", text="觸發類型")
        self.tree.heading("next_run", text="下次運行時間")

        self.tree.column("idx", width=40, anchor="center")
        self.tree.column("name", width=250, anchor="w")
        self.tree.column("status", width=80, anchor="center")
        self.tree.column("type", width=160, anchor="center")
        self.tree.column("next_run", width=180, anchor="center")
        self.tree.pack(fill="both", expand=True, pady=5)

        self.table_menu = tk.Menu(self.root, tearoff=0)
        self.table_menu.add_command(
            label="啟用 / 禁用 切換", command=self.toggle_task_status
        )
        self.table_menu.add_command(label="刪除任務", command=self.delete_task)
        self.tree.bind("<Button-3>", self._show_context_menu)

        self._refresh_treeview()

    def _build_settings_tab(self):
        frame_cfg = ttk.LabelFrame(self.tab_settings, text="基本設定", padding=10)
        frame_cfg.pack(fill="x", pady=5)

        ttk.Label(frame_cfg, text="啟動器路徑:").grid(
            row=0, column=0, sticky="w", pady=4
        )
        self.ent_path = ttk.Entry(frame_cfg, width=65)
        self.ent_path.insert(0, self.cfg.get("launcher_path", ""))
        self.ent_path.grid(row=0, column=1, padx=5, pady=4)

        ttk.Label(frame_cfg, text="DC Webhook:").grid(
            row=1, column=0, sticky="w", pady=4
        )
        self.ent_webhook = ttk.Entry(frame_cfg, width=65)
        self.ent_webhook.insert(0, self.cfg.get("webhook_url", ""))
        self.ent_webhook.grid(row=1, column=1, padx=5, pady=4)

        frame_coord = ttk.LabelFrame(
            self.tab_settings, text="截圖與按鈕座標校準", padding=10
        )
        frame_coord.pack(fill="x", pady=10)

        frame_crop = ttk.Frame(frame_coord)
        frame_crop.pack(fill="x", pady=5)
        ttk.Label(frame_crop, text="卡片截圖比例 (L / T / R / B):").pack(
            side="left"
        )
        ttk.Entry(frame_crop, textvariable=self.var_card_l, width=6).pack(
            side="left", padx=2
        )
        ttk.Entry(frame_crop, textvariable=self.var_card_t, width=6).pack(
            side="left", padx=2
        )
        ttk.Entry(frame_crop, textvariable=self.var_card_r, width=6).pack(
            side="left", padx=2
        )
        ttk.Entry(frame_crop, textvariable=self.var_card_b, width=6).pack(
            side="left", padx=2
        )

        ttk.Button(
            frame_coord,
            text="📐 視覺化拖曳框選截圖範圍",
            command=self.start_visual_snip,
        ).pack(fill="x", pady=4)

        frame_btn_coord = ttk.Frame(frame_coord)
        frame_btn_coord.pack(fill="x", pady=5)
        ttk.Label(frame_btn_coord, text="刷新按鈕比例 (X / Y):").pack(side="left")
        ttk.Entry(frame_btn_coord, textvariable=self.var_btn_x, width=8).pack(
            side="left", padx=2
        )
        ttk.Entry(frame_btn_coord, textvariable=self.var_btn_y, width=8).pack(
            side="left", padx=2
        )

        ttk.Button(
            frame_coord,
            text="🎯 點擊鎖定按鈕位置",
            command=self.start_point_picker,
        ).pack(fill="x", pady=4)
        ttk.Button(
            self.tab_settings,
            text="💾 儲存所有設定與座標",
            command=self._save_settings_btn,
        ).pack(pady=10)

    def log(self, msg):
        self.txt_log.config(state="normal")
        self.txt_log.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {msg}\n")
        self.txt_log.see(tk.END)
        self.txt_log.config(state="disabled")

    def _async(self, fn):
        threading.Thread(target=fn, daemon=True).start()

    def _save_settings_btn(self):
        self._save_current_config()
        self.log("✔ 設定與座標已儲存至 config.json")

    def _save_current_config(self):
        self.cfg["launcher_path"] = self.ent_path.get().strip()
        self.cfg["webhook_url"] = self.ent_webhook.get().strip()
        self.cfg["card_rect"] = {
            "left": self.var_card_l.get(),
            "top": self.var_card_t.get(),
            "right": self.var_card_r.get(),
            "bottom": self.var_card_b.get(),
        }
        self.cfg["refresh_btn"] = {
            "x": self.var_btn_x.get(),
            "y": self.var_btn_y.get(),
        }
        self.cfg["scheduled_tasks"] = self.tasks
        ConfigManager.save(self.cfg)
        self.controller.launcher_path = self.cfg["launcher_path"]
        self.notifier.webhook_url = self.cfg["webhook_url"]

    # ---------- 視覺化校準 ----------

    def start_visual_snip(self):
        try:
            win = self.controller.get_window()
        except Exception as e:
            self.log(f"❌ 找不到視窗: {e}")
            return

        self.log("請按住滑鼠左鍵拖曳想要截圖的區域...")
        overlay = tk.Toplevel(self.root)
        overlay.attributes("-alpha", 0.3)
        overlay.attributes("-fullscreen", True)
        overlay.attributes("-topmost", True)
        overlay.config(cursor="cross")

        canvas = tk.Canvas(overlay, cursor="cross", bg="gray")
        canvas.pack(fill="both", expand=True)
        snip_data = {"start_x": 0, "start_y": 0, "rect": None}

        def on_down(e):
            snip_data["start_x"] = e.x_root
            snip_data["start_y"] = e.y_root
            snip_data["rect"] = canvas.create_rectangle(
                e.x, e.y, e.x, e.y, outline="red", width=2, fill="yellow"
            )

        def on_move(e):
            if snip_data["rect"]:
                canvas.coords(
                    snip_data["rect"],
                    snip_data["start_x"],
                    snip_data["start_y"],
                    e.x_root,
                    e.y_root,
                )

        def on_up(e):
            end_x, end_y = e.x_root, e.y_root
            overlay.destroy()
            abs_l = min(snip_data["start_x"], end_x)
            abs_t = min(snip_data["start_y"], end_y)
            abs_r = max(snip_data["start_x"], end_x)
            abs_b = max(snip_data["start_y"], end_y)

            rel_l = round((abs_l - win.left) / win.width, 3)
            rel_t = round((abs_t - win.top) / win.height, 3)
            rel_r = round((abs_r - win.left) / win.width, 3)
            rel_b = round((abs_b - win.top) / win.height, 3)

            self.var_card_l.set(rel_l)
            self.var_card_t.set(rel_t)
            self.var_card_r.set(rel_r)
            self.var_card_b.set(rel_b)
            self._save_current_config()
            self.log("✔ 截圖範圍已更新並儲存")

        canvas.bind("<ButtonPress-1>", on_down)
        canvas.bind("<B1-Motion>", on_move)
        canvas.bind("<ButtonRelease-1>", on_up)

    def start_point_picker(self):
        try:
            win = self.controller.get_window()
        except Exception as e:
            self.log(f"❌ 找不到視窗: {e}")
            return

        self.log("請點擊【特徵碼右邊的刷新按鈕】...")
        overlay = tk.Toplevel(self.root)
        overlay.attributes("-alpha", 0.2)
        overlay.attributes("-fullscreen", True)
        overlay.attributes("-topmost", True)
        overlay.config(cursor="target")

        def on_click(e):
            clk_x, clk_y = e.x_root, e.y_root
            overlay.destroy()
            rel_x = round((clk_x - win.left) / win.width, 3)
            rel_y = round((clk_y - win.top) / win.height, 3)

            self.var_btn_x.set(rel_x)
            self.var_btn_y.set(rel_y)
            self._save_current_config()
            self.log("✔ 按鈕座標已更新並儲存")

        overlay.bind("<Button-1>", on_click)

    # ---------- 表格任務管理 ----------

    def _refresh_treeview(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        for i, t in enumerate(self.tasks, 1):
            st = "已啟用" if t["enabled"] else "已禁用"
            self.tree.insert(
                "",
                "end",
                iid=str(i - 1),
                values=(i, t["name"], st, t["trigger_type"], t["next_run"]),
            )

    def _show_context_menu(self, e):
        row_id = self.tree.identify_row(e.y)
        if row_id:
            self.tree.selection_set(row_id)
            self.table_menu.post(e.x_root, e.y_root)

    def open_create_dialog(self):
        CreateTaskDialog(self.root, self.add_task)

    def add_task(self, task_data):
        self.tasks.append(task_data)
        self._save_current_config()
        self._refresh_treeview()
        self.log(f"✔ 新增計劃任務：{task_data['name']}")

    def toggle_task_status(self):
        sel = self.tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        self.tasks[idx]["enabled"] = not self.tasks[idx]["enabled"]
        self._save_current_config()
        self._refresh_treeview()

    def delete_task(self):
        sel = self.tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        del self.tasks[idx]
        self._save_current_config()
        self._refresh_treeview()

    # ---------- 背景排程與執行核心 ----------

    def _scheduler_loop(self):
        while self.is_running:
            now = datetime.now()
            for t in self.tasks:
                if not t.get("enabled", True):
                    continue

                t_run = datetime.strptime(
                    t["next_run"], "%Y-%m-%d %H:%M:%S"
                )
                if now >= t_run:
                    self.log(f"⏰ [排程觸發] 執行: {t['name']}")
                    threading.Thread(
                        target=self._execute_task,
                        args=(t["name"],),
                        daemon=True,
                    ).start()

                    if t["trigger_type"] == "每天 (指定時間)":
                        t_next = t_run + timedelta(days=1)
                    else:
                        mins = t["meta"].get("interval_mins", 60)
                        t_next = now + timedelta(minutes=mins)

                    t["next_run"] = t_next.strftime("%Y-%m-%d %H:%M:%S")
                    self._save_current_config()
                    self.root.after(0, self._refresh_treeview)

            time.sleep(2)

    def _execute_task(self, task_name):
        if "無截圖" in task_name or "僅辨識" in task_name:
            self.on_ocr_text_only()
            return

        if "辨識" in task_name:
            self.on_ocr_and_send()
            return

        try:
            rx = self.var_btn_x.get()
            ry = self.var_btn_y.get()
            rect = {
                "left": self.var_card_l.get(),
                "top": self.var_card_t.get(),
                "right": self.var_card_r.get(),
                "bottom": self.var_card_b.get(),
            }

            if "刷新" in task_name:
                self.controller.click_refresh(rx, ry)
                time.sleep(3)

            if "截圖" in task_name:
                img_path = self.controller.capture_card(rect)
                self.notifier.send_image(
                    img_path, message=f"⏰ **[計劃任務] {task_name}**"
                )
            self.log(f"✔ 任務完成: {task_name}")
        except Exception as e:
            self.log(f"❌ 任務執行異常: {e}")

    # ---------- 功能按鈕 ----------

    def on_ocr_text_only(self):
        """刷新 -> 截圖 -> 辨識 -> 僅發送文字至 DC -> 刪除本地截圖"""
        img_path = None
        try:
            self.log("正在執行啟動器刷新...")
            rx = self.var_btn_x.get()
            ry = self.var_btn_y.get()
            self.controller.click_refresh(rx, ry)
            time.sleep(3)

            self.log("截取卡片暫存中...")
            rect = {
                "left": self.var_card_l.get(),
                "top": self.var_card_t.get(),
                "right": self.var_card_r.get(),
                "bottom": self.var_card_b.get(),
            }
            img_path = self.controller.capture_card(rect)

            self.log("正在使用 OCR 辨識數值...")
            data = self.ocr.extract_status(img_path)
            self.log(f"✔ 辨識結果 -> 體力: {data['stamina']}, 活躍度: {data['activity']}")

            # 組成純文字訊息
            msg = (
                f"📊 **【鳴潮】實時數據狀態**\n"
                f"🔹 **體力 (結晶波存量)**：`{data['stamina']}`\n"
                f"🔹 **每日活躍度**：`{data['activity']}`\n"
                f"⏰ 更新時間：`{time.strftime('%Y-%m-%d %H:%M:%S')}`"
            )

            self.log("正在發送純文字訊息至 Discord...")
            self.notifier.send_text(msg)
            self.log("✔ 已成功發送純文字數據！")
        except Exception as e:
            self.log(f"❌ 辨識或發送失敗: {e}")
        finally:
            # 清理暫存圖片
            if img_path and os.path.exists(img_path):
                os.remove(img_path)

    def on_ocr_and_send(self):
        """刷新 -> 截圖 -> 辨識 -> 發送文字與圖片至 DC"""
        try:
            self.log("正在執行啟動器刷新...")
            rx = self.var_btn_x.get()
            ry = self.var_btn_y.get()
            self.controller.click_refresh(rx, ry)
            time.sleep(3)

            self.log("截取卡片中...")
            rect = {
                "left": self.var_card_l.get(),
                "top": self.var_card_t.get(),
                "right": self.var_card_r.get(),
                "bottom": self.var_card_b.get(),
            }
            img_path = self.controller.capture_card(rect)

            self.log("正在使用 OCR 辨識數值...")
            data = self.ocr.extract_status(img_path)
            self.log(f"✔ 辨識結果 -> 體力: {data['stamina']}, 活躍度: {data['activity']}")

            msg = (
                f"📊 **【鳴潮】實時數據狀態回報**\n"
                f"🔹 **體力 (結晶波存量)**：`{data['stamina']}`\n"
                f"🔹 **每日活躍度**：`{data['activity']}`\n"
                f"⏰ 更新時間：`{time.strftime('%Y-%m-%d %H:%M:%S')}`"
            )

            self.log("正在發送圖文至 Discord...")
            self.notifier.send_image(img_path, message=msg)
            self.log("✔ 已成功發送 OCR 數據與截圖！")
        except Exception as e:
            self.log(f"❌ OCR 辨識發送失敗: {e}")

    def on_refresh(self):
        rx = self.var_btn_x.get()
        ry = self.var_btn_y.get()
        pt = self.controller.click_refresh(rx, ry)
        self.log(f"✔ 手動刷新完成 -> 座標 {pt}")

    def on_capture(self):
        rect = {
            "left": self.var_card_l.get(),
            "top": self.var_card_t.get(),
            "right": self.var_card_r.get(),
            "bottom": self.var_card_b.get(),
        }
        img_path = self.controller.capture_card(rect)
        self.notifier.send_image(img_path)
        self.log("✔ 手動截圖發送完成")


if __name__ == "__main__":
    root = tk.Tk()
    app = AppGUI(root)
    root.mainloop()