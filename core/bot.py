# bot.py
import copy
import time
import sys
from pathlib import Path
from enum import Enum

root_path = str(Path(__file__).parent.parent)
if root_path not in sys.path:
    sys.path.append(root_path)


from core.config import GameConfig
from core.vision import SudokuVision
from core.action import AdbActionBot, StopTaskException
from core.solver import SolverBot 
from core.adb_controller import AdbController

class TaskStatus(Enum):
    SUCCESS = "Success"
    FAIL = "fail"
    STOPPED = "stopped"
    ERROR = "error"

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
            print(f"警告：偵測到的數字只有 {count} 個，判定為無效")
            return True

        return False # 通過檢查

    def _restart_and_enter_game(self, is_recovery=False):
        """
        [統一重置] 殺掉 App -> 重開 -> 點擊開始遊戲
        參數 is_recovery: 若為 True，代表是系統崩潰後的重啟，會多點擊「新遊戲(取消舊進度)」視窗。
        """
        if is_recovery:
            print("\n觸發異常恢復機制！正在重啟應用程式...")
        else:
            print("\n準備進行下一局，重啟 App 以跳過廣告...")
            
        self.adb.restart_app()
        self.wait_if_paused()
        print("⏳ 等待 App 重新載入...")
        time.sleep(7)

        # 點擊開始遊戲按鈕
        self.wait_if_paused()
        if not self.click_target("start_btn.png", wait_time=3):
            self.click_target("87cheak.png")
            time.sleep(5)
        time.sleep(1)
        self.wait_if_paused()
        if is_recovery:
            print("點擊「新遊戲」以清除崩潰進度")
            recovery_image = self._wait_for_image(["normal_diff.png", "error_new_game"], timeout=5)
            self.click_target(recovery_image, threshold=0.5)

        else: self.click_target("normal_diff.png")
        time.sleep(2)
        self.wait_if_paused()
        print("重啟就緒，可以開始！")

    def _run_one_round(self):

        self.wait_if_paused()
        """ 執行一回合：掃描 -> 計算 -> 填寫 """
        print("\n" + "="*30)
        print("階段一：掃描盤面")
        
        # 呼叫 Vision 模組掃描 (回傳 9x9 數字陣列)
        board_numbers = self.vision.recognize_board(save_debug=False)
        for row in board_numbers:
            print(row)
        
        if not board_numbers:
            print("掃描失敗：無法辨識盤面")
            return False

        if self._is_board_invalid(board_numbers):
            print("異常：掃描結果全為 0 (或數字過少)")
            return False  # 回傳失敗，讓 Main 決定要不要重試

        # 備份一份原始盤面 (因為 Action 需要知道哪些格子原本是空的)
        original_board = copy.deepcopy(board_numbers)

        print("\n階段二：計算解答")
        # 呼叫 Solver 模組解題
        # 注意：假設你的 solver.py 裡面的方法叫 solve() 或 solve_algo()
        solved_board = self.solver.solve(board_numbers) 

        if solved_board:
            print("計算成功！準備填入答案...")
            
            print("\n 階段三：執行填寫")
            # 呼叫 Action 模組填寫
            # 傳入：原始盤面(判斷空格)、解答盤面(填數字)、座標資訊(知道點哪)
            self.fill_result_relative(original_board, solved_board)
            
            print("本回合結束！")
            return True
        
        print("無解！請檢查 Vision 識別是否錯誤 (例如把 8 看成 3)。")
        return False

    def _wait_for_image(self, target_images, timeout: int = 15):
        """
        參數 target_images: 可以傳入單一字串 "a.png" 或列表 ["a.png", "b.png"]
        回傳: 找到的那張圖片名稱 (字串)。如果超時沒找到，回傳 False。
        """
        # 如果傳進來的是單一字串，幫它包裝成列表，統一口徑
        if isinstance(target_images, str):
            target_images = [target_images]

        print(f"開始等待畫面出現: {target_images} (最多 {timeout} 秒)...")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            self.wait_if_paused()
            screen = self.adb.get_screenshot()
            
            # 輪流拿清單裡的目標去問 Vision
            for img_name in target_images:
                if self.vision.find_and_get_pos(screen, img_name):
                    print(f"🎯 成功捕捉到目標畫面: {img_name}")
                    return img_name  # 回傳找到的圖片名字！
                    
            time.sleep(0.5)
            
        print(f"⚠️ 等待超時：未發現任何目標 {target_images}")
        return False

    def run_round_with_retry(self, current_round=0, total_rounds=0):
        """ [大主管] 統籌執行關卡，包含重試與異常恢復邏輯 """
        try:
            for attempt in range(4):
                print(f"\n▶️ 開始嘗試第 {attempt + 1}/4 次")
                
                # 1. 下令執行填寫
                if not self._run_one_round():
                    print("⚠️ 填寫過程發生錯誤，準備重試...")
                    time.sleep(1)
                    continue  # 🌟 直接進入下一次迴圈，不要去傻等過關畫面！

                # 2. 下令檢驗過關 (只有填寫成功，才會走到這裡)
                is_cleared = self._wait_for_image("clear.png", timeout=17)
                
                if is_cleared:
                    # 🌟 順利過關！判斷是否需要一般重置 (非最後一局)
                    if current_round < total_rounds:
                        self._restart_and_enter_game(is_recovery=False)
                        
                    return TaskStatus.SUCCESS  # 提早下班，回報成功給 main.py

                else:
                    print("⚠️ 填寫完畢但未過關(可能漏填或卡住)，準備重試...")
                    continue  # 進入下一次迴圈
                    
            # ==========================================
            # 🚨 4次迴圈都用光了，還是沒能 return FINISHED
            # ==========================================
            print("\n❌ 多次嘗試失敗，判斷為環境異常，啟動核彈級重置！")
            
            # 啟動帶有「點擊新遊戲」的異常恢復重啟
            self._restart_and_enter_game(is_recovery=True)
            
            # 回傳 ERROR，讓 main.py 知道這局徹底死掉了
            return TaskStatus.FAIL
            
        except StopTaskException as e:
            print(f"🛑 {e}")
            return TaskStatus.STOPPED   
            
        except Exception as e:
            print(f"⚠️ 未知錯誤: {e}")
            import traceback
            traceback.print_exc()
            return TaskStatus.ERROR


if __name__ == "__main__":
    bot = SudokuBot()
    bot._run_one_round()