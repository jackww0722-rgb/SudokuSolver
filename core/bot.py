# bot.py
import copy
import time
import sys
import threading
from pathlib import Path
from enum import Enum

root_path = str(Path(__file__).parent.parent)
if root_path not in sys.path:
    sys.path.append(root_path)


from .config import GameConfig
from .vision import SudokuVision
from .action import AdbActionBot, StopTaskException
from .solver import SolverBot 
from .adb_controller import AdbController
from .navigator import SudokuNavigator
from .logger import logger

class TaskStatus(Enum):
    SUCCESS = "Success"
    FAIL = "fail"
    STOPPED = "stopped"
    ERROR = "error"

class SudokuBot:
    def __init__(self):
        logger.info("初始化核心模組 (ADB Utils 版)...")
        self.pause_event = threading.Event()
        self.pause_event.set() # 預設綠燈
        self.stop_event = threading.Event()
        self.stop_event.clear()

        self.is_calibrated = False
        
        # 1. 實例化各個機器人
        # 這裡會自動執行它們的 __init__ (包含檢查路徑、連線ADB等)
        self.config = GameConfig()
        self.adb = AdbController(self.config.adb_config)
        self.solver = SolverBot()
        self.nav = None
        self.global_positions: dict = {}
        self.vision = SudokuVision(self.config, self.adb, self.global_positions)
        self.action = AdbActionBot(self.adb, self.vision, self.pause_event, self.stop_event, self.global_positions)

    # ==========================================
    # 🎮 提供給 main.py 的遙控器按鈕
    # ==========================================
    def toggle_pause(self):
        """切換暫停/恢復"""
        if self.pause_event.is_set():
            self.pause_event.clear() # 變紅燈
            return True
        else:
            self.pause_event.set()   # 變綠燈
            return False

    def stop_task(self):
        """觸發停止任務"""
        self.stop_event.set()
        # ⚠️ 神級細節：如果程式現在正在暫停(wait中)，必須把暫停解開，Action 才能醒來並丟出 Exception！
        self.pause_event.set() 
        logger.info("🛑 已發送停止訊號！")



    def connect_and_calibrate(self, force: bool = False, auto_recover: bool = True) -> bool:
        """
        開局接力賽：ADB 截圖 -> 視覺部定錨 -> 大腦算座標 -> 部門分發地圖
        """
        if self.is_calibrated and not force:
            logger.info("⚡ 讀取座標快取，跳過 ADB 截圖與雷達掃描！")
            return True

        logger.info("\n🔗 正在進行開局校正與系統初始化...")
        
        # 1. 取得原汁原味的開局畫面
        raw_img = self.adb.get_screenshot()
        if raw_img is None:
            logger.error("❌ 截圖失敗，無法進行開局校正！")
            return False

        screen_h, screen_w = raw_img.shape[:2]

        # ==========================================
        # 🌟 完美接力賽開始
        # ==========================================
        
        # 步驟一：告訴視覺部現在的螢幕比例
        self.vision.set_screen_scale(screen_w)

        # 步驟二：請視覺部尋找燈塔 (錨點)
        if anchor_pos := self.vision.find_and_get_pos(raw_img, "anchor.png",threshold=0.8):
            _, anchor_y = anchor_pos
            board_top_y = int(anchor_y + (36 * self.vision.scale))

            # 步驟四：誕生純數學大腦，瞬間算完 81 格 + 9 個按鈕的物理座標
            self.nav = SudokuNavigator(screen_w, screen_h, board_top_y)

            # 步驟五：總裁把算好的座標地圖，發配給各個行動部門
            self.global_positions.update(self.nav.get_all_positions())
            # self.action.set_positions(positions)  # <-- 下一步 Action 的伏筆！

            # 步驟六：現在視覺部已經知道 scale 了，可以一次性把 1~9 數字範本縮放並載入快取！
            self.vision.load_templates()

            logger.info("✅ 開局校正完美結束！大腦與視覺部已就緒。\n")
            self.is_calibrated = True
            return True
        
        else:
            # ❌ 找不到錨點，觸發防呆救援
            if auto_recover:
                logger.warning("⚠️ 找不到遊戲盤面！正在呼叫既有的重啟導航機制...")
                
                # 🌟 直接無縫接入你原本寫好的絕招！
                self._restart_and_enter_game()
                
                # 重新校正第二回合，強制設定 auto_recover=False 防範無限重啟
                return self.connect_and_calibrate(force=True, auto_recover=False)
            else:
                logger.error("❌ 防呆機制觸發：經過一次自動重啟救援後依然無法定錨，放棄任務。")
                return False

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
            logger.warning(f"警告：偵測到的數字只有 {count} 個，判定為無效")
            return True

        return False # 通過檢查

    def _restart_and_enter_game(self, is_recovery=False):
        """
        [統一重置] 殺掉 App -> 重開 -> 點擊開始遊戲
        參數 is_recovery: 若為 True，代表是系統崩潰後的重啟，會多點擊「新遊戲(取消舊進度)」視窗。
        """
        if is_recovery:
            logger.warning("\n觸發異常恢復機制！正在重啟應用程式...")
        else:
            logger.info("\n準備進行下一局，重啟 App 以跳過廣告...")
            
        self.adb.restart_app()
        self.action.wait_if_paused()
        time.sleep(7)

        # 點擊開始遊戲按鈕
        self.action.wait_if_paused()
        if not self.action.click_target("start_btn.png", wait_time=3):
            self.action.click_target("87cheak.png")
            time.sleep(5)
        time.sleep(1)
        self.action.wait_if_paused()
        if is_recovery:
            logger.info("點擊「新遊戲」以清除崩潰進度")
            recovery_image, pos_1 = self._wait_for_image(["normal_diff.png", "error_new_game.png"], timeout=5)
            if pos_1:
                self.adb.tap(*pos_1)

            if recovery_image == "error_new_game.png":
                    logger.info("已清除殘局提示，準備補點「普通難度」...")     
                    # 再次等待普通難度按鈕浮現並點擊
                    _, pos_2 = self._wait_for_image(["normal_diff.png"], timeout=5)
                    if pos_2:
                        self.adb.tap(*pos_2)
                    else:
                        logger.warning("⚠️ 點擊錯誤提示後，未如預期出現普通難度按鈕")

        else: self.action.click_target("normal_diff.png")
        time.sleep(2)
        self.action.wait_if_paused()
        logger.info("重啟就緒，可以開始！")

    def _run_one_round(self):

        self.action.wait_if_paused()
        """ 執行一回合：掃描 -> 計算 -> 填寫 """
        logger.info("\n" + "="*30)
        logger.info("階段一：掃描盤面")
        
        # 呼叫 Vision 模組掃描 (回傳 9x9 數字陣列)
        board_numbers = self.vision.recognize_board(save_debug=False)
        for row in board_numbers:
            logger.info(row)
        
        if not board_numbers:
            logger.warning("掃描失敗：無法辨識盤面")
            return False

        if self._is_board_invalid(board_numbers):
            logger.warning("異常：掃描結果全為 0 (或數字過少)")
            return False  # 回傳失敗，讓 Main 決定要不要重試

        # 備份一份原始盤面 (因為 Action 需要知道哪些格子原本是空的)
        original_board = copy.deepcopy(board_numbers)

        logger.info("\n階段二：計算解答")
        # 呼叫 Solver 模組解題
        # 注意：假設你的 solver.py 裡面的方法叫 solve() 或 solve_algo()
        solved_board = self.solver.solve(board_numbers) 

        if solved_board:
            
            logger.info("\n 階段三：執行填寫")
            # 呼叫 Action 模組填寫
            # 傳入：原始盤面(判斷空格)、解答盤面(填數字)、座標資訊(知道點哪)
            self.action.fill_result_relative(original_board, solved_board)
            
            logger.info("本回合結束！")
            return True
        
        logger.warning("無解！請檢查 Vision 識別是否錯誤 (例如把 8 看成 3)。")
        return False

    def _wait_for_image(self, target_images, threshold = 0.85, timeout: int = 15):
        """
        參數 target_images: 可以傳入單一字串 "a.png" 或列表 ["a.png", "b.png"]
        回傳: 找到的那張圖片名稱 (字串)。如果超時沒找到，回傳 False。
        """
        # 如果傳進來的是單一字串，幫它包裝成列表，統一口徑
        if isinstance(target_images, str):
            target_images = [target_images]

        logger.debug(f"開始等待畫面出現: {target_images} (最多 {timeout} 秒)...")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            self.action.wait_if_paused()
            screen = self.adb.get_screenshot()
            
            # 輪流拿清單裡的目標去問 Vision
            for img_name in target_images:
                if pos := self.vision.find_and_get_pos(screen, img_name, threshold=threshold):
                    logger.debug(f"🎯 成功捕捉到目標畫面: {img_name}")
                    return img_name, pos  # 回傳找到的圖片名字！
                    
            time.sleep(0.5)
            
        logger.warning(f"⚠️ 等待超時：未發現任何目標 {target_images}")
        return None, None

    def run_round_with_retry(self, current_round=0, total_rounds=0, closed_game=False):
        """ [大主管] 統籌執行關卡，包含重試與異常恢復邏輯 """
        try:
            for attempt in range(4):
                logger.info(f"\n▶️ 開始嘗試第 {attempt + 1}/4 次")
                
                # 1. 下令執行填寫
                if not self._run_one_round():
                    logger.warning("⚠️ 填寫過程發生錯誤，準備重試...")
                    time.sleep(1)
                    continue  # 🌟 直接進入下一次迴圈，不要去傻等過關畫面！

                # 2. 下令檢驗過關 (只有填寫成功，才會走到這裡)
                is_cleared = self._wait_for_image("clear.png", timeout=17)
                
                if is_cleared:
                    # 🌟 順利過關！判斷是否需要一般重置 (非最後一局)
                    if current_round < total_rounds:
                        self._restart_and_enter_game(is_recovery=False)
                    elif closed_game == True:
                        self.adb.stop_app()
                    return TaskStatus.SUCCESS  # 提早下班，回報成功給 main.py

                else:
                    logger.warning("⚠️ 填寫完畢但未過關(可能漏填或卡住)，準備重試...")
                    continue  # 進入下一次迴圈
                    
            # ==========================================
            # 🚨 4次迴圈都用光了，還是沒能 return FINISHED
            # ==========================================
            logger.warning("\n❌ 多次嘗試失敗，判斷為環境異常，啟動核彈級重置！")
            
            # 啟動帶有「點擊新遊戲」的異常恢復重啟
            self._restart_and_enter_game(is_recovery=True)
            
            # 回傳 ERROR，讓 main.py 知道這局徹底死掉了
            return TaskStatus.FAIL
            
        except StopTaskException as e:
            logger.error(f"🛑 {e}")
            return TaskStatus.STOPPED   
            
        except Exception as e:
            logger.error(f"⚠️ 未知錯誤: {e}")
            return TaskStatus.ERROR


if __name__ == "__main__":
    bot = SudokuBot()
    bot._run_one_round()