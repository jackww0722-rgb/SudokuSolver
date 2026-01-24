# main.py
# 改變引用路徑：從 core.bot 引入 SudokuBot
from core.bot import SudokuBot 
import time

def main():
    print("🚀 程式啟動 (單次執行模式)")

    try:
        # 初始化
        bot = SudokuBot()
        
        # 執行
        success = bot.run_one_round()

        if success:
            print("🏁 任務圓滿達成！程式將在 3 秒後關閉...")
        else:
            print("❌ 任務失敗，請檢查錯誤訊息。")

    except Exception as e:
        print(f"❌ 發生錯誤: {e}")
        import traceback
        traceback.print_exc() # 印出詳細錯誤位置，方便除錯
    
    time.sleep(3)

if __name__ == "__main__":
    main()