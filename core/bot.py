# bot.py
import copy
import time

# 引入寫好的類別
from .config import GameConfig
from .vision import SudokuVision
from .action import AdbActionBot
from .solver import SolverBot 
from .adb_controller import AdbController


class SudokuBot:
    def __init__(self):
        print("初始化核心模組 (ADB Utils 版)...")
        
        # 1. 實例化各個機器人
        # 這裡會自動執行它們的 __init__ (包含檢查路徑、連線ADB等)
        self.config = GameConfig()
        self.adb = AdbController(self.config.adb_config)
        self.solver = SolverBot()
        


        self.vision = SudokuVision(self.config, self.adb)
        self.action = AdbActionBot(self.config.region_info, self.config.btn_info, self.adb, self.vision)

    #grand order
    def scan_board(self):
        # 設定模板路徑  
        print("🚀 開始識別 (開啟除錯存圖模式)...")
        
        # 這裡設為 True，就會把格子存下來
        result = self.vision.recognize_board(save_debug=True)
        
        print("\n--- 識別結果 ---")
        for row in result:
            print(row)
        return result

    def run_one_round(self):
        """ 執行一回合：掃描 -> 計算 -> 填寫 """
        print("\n" + "="*30)
        print("👀 階段一：掃描盤面")
        
        # 呼叫 Vision 模組掃描 (回傳 9x9 數字陣列)
        board_numbers = self.scan_board()
        
        if not board_numbers:
            print("❌ 掃描失敗：無法辨識盤面")
            return False

        # 備份一份原始盤面 (因為 Action 需要知道哪些格子原本是空的)
        original_board = copy.deepcopy(board_numbers)

        print("\n🧠 階段二：計算解答")
        # 呼叫 Solver 模組解題
        # 注意：假設你的 solver.py 裡面的方法叫 solve() 或 solve_algo()
        solved_board = self.solver.solve(board_numbers) 

        if solved_board:
            print("✅ 計算成功！準備填入答案...")
            
            print("\n✍️ 階段三：執行填寫")
            # 呼叫 Action 模組填寫
            # 傳入：原始盤面(判斷空格)、解答盤面(填數字)、座標資訊(知道點哪)
            self.action.fill_result_relative(original_board, solved_board)
            
            print("🎉 本回合結束！")
            return True
        else:
            print("❌ 無解！請檢查 Vision 識別是否錯誤 (例如把 8 看成 3)。")
            return False
            
    def _reset_state(self):
        """ [內部] 重置遊戲狀態 (例如重啟 App 以跳過廣告) """
        print("🔄 準備進行下一局，重啟 App 以跳過廣告...")
        self.adb.restart_app()
        time.sleep(5) # 等待重啟
        self.action.click_target("start_btn.png", wait_time=3)
        time.sleep(1)
        self.action.click_target("normal_diff.png")
        time.sleep(2)

    def run_round_with_retry(self, current_round=0, total_rounds=0):
        # 1. 改用 for 迴圈，自動處理次數 (0, 1, 2, 3)
        for attempt in range(4):
            self.run_one_round()

            # 2. 等待過關畫面 (直接把等待邏輯寫清楚，或封裝成 wait_for_image)
            start_time = time.time()
            while time.time() - start_time < 15:
                screen = self.adb.get_screenshot()
                
                # 只要檢查這一次就好
                if self.vision.find_and_get_pos(screen, "clear.png"):
                    
                    # 3. 判斷是否需要重置 (不是最後一局才做)
                    if current_round < total_rounds - 1:
                        self._reset_state()
                    
                    return True # 成功

                time.sleep(0.5)
            
            print(f"⚠️ 第 {attempt + 1} 次嘗試失敗，重試中...")

        return False