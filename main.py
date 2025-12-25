# main.py
import pyautogui

from core import bot


# 🚀 主程式入口
# ==========================================
def main():

    try:
        bot.run_one_round()

    except pyautogui.FailSafeException:
        print("\n🛑 緊急停止觸發！程式已強制結束。")
    except KeyboardInterrupt:
        print("\n👋 使用者手動中斷。")

if __name__ == "__main__":
    main()
