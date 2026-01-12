# bot.py
import copy
from . import config
import time

# 引入寫好的類別
from .vision import SudokuVision
from .action import AdbActionBot
from .solver import SolverBot 

class SudokuBot:
    def __init__(self):
        print("初始化核心模組 (ADB Utils 版)...")
        
        # 1. 實例化各個機器人
        # 這裡會自動執行它們的 __init__ (包含檢查路徑、連線ADB等)
        self.vision = SudokuVision()
        self.action = AdbActionBot()
        self.solver = SolverBot()

        # 2. 準備座標資訊 (因為座標已經固定在 config，直接包裝好給 Action 用)
        self.region_info = {
            'left': config.BOARD_LEFT,
            'top': config.BOARD_TOP,
            'width': config.BOARD_WIDTH,
            'height': config.BOARD_HEIGHT,
            'cell_w': config.CELL_WIDTH,
            'cell_h': config.CELL_HEIGHT
        }

    def run_one_round(self):
        """ 執行一回合：掃描 -> 計算 -> 填寫 """
        print("\n" + "="*30)
        print("👀 階段一：掃描盤面")
        
        # 呼叫 Vision 模組掃描 (回傳 9x9 數字陣列)
        board_numbers = self.vision.scan_board()
        
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
            self.action.fill_result_relative(original_board, solved_board, self.region_info)
            
            print("🎉 本回合結束！")
            return True
        else:
            print("❌ 無解！請檢查 Vision 識別是否錯誤 (例如把 8 看成 3)。")
            return False
            
    def handle_ad_interruption(self):
        """ (選用) 處理廣告的邏輯可以放在這裡 """
        print("⚠️ 偵測到疑似廣告或異常狀態...")
        self.action.restart_app()
        # 等待重啟後，可能需要一些邏輯回到遊戲畫面
        time.sleep(5)