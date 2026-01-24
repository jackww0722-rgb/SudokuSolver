# bot.py
import copy
import time
import sys
from pathlib import Path


root_path = str(Path(__file__).parent.parent)
if root_path not in sys.path:
    sys.path.append(root_path)

# 引入寫好的類別
from core.config import GameConfig
from core.vision import SudokuVision
from core.action import AdbActionBot
from core.solver import SolverBot 
from core.adb_controller import AdbController


class SudokuBot(AdbActionBot):
    def __init__(self):
        print("初始化核心模組 (ADB Utils 版)...")
        
        # 1. 實例化各個機器人
        # 這裡會自動執行它們的 __init__ (包含檢查路徑、連線ADB等)
        self.config = GameConfig()
        self.adb = AdbController(self.config.adb_config)
        self.solver = SolverBot()
        


        self.vision = SudokuVision(self.config, self.adb)
        super().__init__(self.config.region_info, self.config.btn_info, self.adb, self.vision)

    def _is_board_invalid(self, board):
        """
        [內部工具] 檢查盤面是否有效
        """
        # 1. 先把 2D 陣列攤平，方便計算
        flat_board = [num for row in board for num in row]
        
        # 2. 計算非 0 的數字有幾個
        count = sum(1 for num in flat_board if num > 0)
        
        # 判斷標準 A: 完全是空的 (全是 0) -> 絕對有問題
        if count == 0:
            return True 
            
        # 判斷標準 B (進階): 數字太少 -> 數獨規則至少要有 17 個數字才有唯一解
        # 如果掃出來只有 5 個數字，通常也是 OCR 爛掉或是畫面不對
        if count < 10:  # 可以設寬鬆一點，例如 10
            print(f"⚠️ 警告：偵測到的數字只有 {count} 個，判定為無效")
            return True

        return False # 通過檢查

    def run_one_round(self):
        """ 執行一回合：掃描 -> 計算 -> 填寫 """
        print("\n" + "="*30)
        print("👀 階段一：掃描盤面")
        
        # 呼叫 Vision 模組掃描 (回傳 9x9 數字陣列)
        board_numbers = self.vision.recognize_board(save_debug=False)
        for row in board_numbers:
            print(row)
        
        if not board_numbers:
            print("❌ 掃描失敗：無法辨識盤面")
            return False

        if self._is_board_invalid(board_numbers):
            print("❌ 異常：掃描結果全為 0 (或數字過少)")
            return False  # 回傳失敗，讓 Main 決定要不要重試

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
            self.fill_result_relative(original_board, solved_board)
            
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
        self.click_target("start_btn.png", wait_time=3)
        time.sleep(1)
        self.click_target("normal_diff.png")
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

        raise Exception
    
if __name__ == "__main__":
    bot = SudokuBot()
    bot.run_one_round()