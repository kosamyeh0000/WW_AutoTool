import asyncio
import os
import discord
from discord import app_commands
from discord.ext import commands

from config_manager import ConfigManager
from launcher_controller import LauncherController
from ocr_parser import StatusOCR

# 讀取設定檔
import json

# 讀取設定檔
config_mgr = ConfigManager()
if hasattr(config_mgr, "config"):
    config = config_mgr.config
elif hasattr(config_mgr, "get_config"):
    config = config_mgr.get_config()
else:
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)

BOT_TOKEN = config.get("bot_token", "")
ALLOWED_USER_ID = config.get("allowed_user_id", 0)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# 初始化控制器與辨識器
ocr = StatusOCR()
launcher_path = config.get("launcher_path", "")
controller = LauncherController(launcher_path)

@bot.event
async def on_ready():
    print(f"[Bot] 機器人登入成功：{bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"[Bot] 已同步 {len(synced)} 個斜線指令！")
    except Exception as e:
        print(f"[Bot] 指令同步失敗: {e}")


@bot.tree.command(name="status", description="即時查詢鳴潮體力與帳號狀態")
async def status_cmd(interaction: discord.Interaction):
    # 身分驗證 (防止其他人亂戳)
    if ALLOWED_USER_ID and interaction.user.id != int(ALLOWED_USER_ID):
        await interaction.response.send_message(
            "❌ 你沒有操作此機器人的權限！", ephemeral=True
        )
        return

    # 延遲回應 (避免超過 3 秒超時)
    await interaction.response.defer(thinking=True)

    try:
        loop = asyncio.get_running_loop()

        # 1. 於後台執行卡片截圖
        card_rect = config.get("card_rect", {})
        img_path = await loop.run_in_executor(
            None, controller.capture_card, card_rect
        )
        if not img_path or not os.path.exists(img_path):
            await interaction.followup.send(
                "❌ 截圖失敗，請確認鳴潮啟動器是否在前景或未最小化！"
            )
            return

        # 2. 進行 OCR 辨識
        data = await loop.run_in_executor(None, ocr.extract_status, img_path)

        stamina = data.get("stamina", 0)
        max_stamina = data.get("max_stamina", 240)
        reserve = data.get("reserve_stamina", 0)
        activity = data.get("activity", 0)

        # 3. 構建 Embed 回覆
        color = 0x00FF88 if stamina < 200 else 0xFF4444
        embed = discord.Embed(title="🎮 鳴潮 - 即時狀態回報", color=color)
        embed.add_field(
            name="日常體力", value=f"**{stamina}** / {max_stamina}", inline=True
        )
        embed.add_field(
            name="後備體力", value=f"**{reserve}** / 480", inline=True
        )
        embed.add_field(
            name="每日活躍度", value=f"**{activity}** / 100", inline=True
        )

        file = discord.File(img_path, filename="status.png")
        embed.set_image(url="attachment://status.png")

        await interaction.followup.send(file=file, embed=embed)

    except Exception as e:
        await interaction.followup.send(f"❌ 執行發生錯誤: {e}")


def main():
    if not BOT_TOKEN:
        print("[錯誤] 未填寫 bot_token！")
        return
    bot.run(BOT_TOKEN)


if __name__ == "__main__":
    main()