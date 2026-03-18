# core/action.py
import time
from .adb_controller import AdbController
from .vision import SudokuVision
import threading


class StopTaskException(Exception):
    pass

class AdbActionBot:
    def __init__(self, region_info : dict, btn_info : dict, adb : AdbController, vision : SudokuVision):
        self.region_info = region_info
        self.btn_info = btn_info
        self.adb = adb
        self.vision = vision

        # ==========================================
        # 🚦 新增暫停控制閥 (Event)
        # ==========================================
        self.pause_event = threading.Event()
        self.pause_event.set() # 預設是 Green Light (Set = 通行, Clear = 暫停)
        self.stop_event = threading.Event()
        self.stop_event.clear()
        
    def wait_if_paused(self):
        """ 
        [核心煞車] 所有動作前都會檢查
        不僅檢查暫停，也檢查是否被按下停止
        """
        # A. 如果還沒暫停就按了停止
        if self.stop_event.is_set():
            raise StopTaskException("手動停止任務")

        # B. 處理暫停邏輯
        if not self.pause_event.is_set():
            print("⏸️ 動作已暫停")
            
            # 【關鍵修改】不要用死等的 wait()，改用帶有 timeout 的迴圈
            # 這樣就算在暫停狀態下按「停止」，程式也能馬上反應並退出
            while not self.pause_event.is_set():
                if self.stop_event.is_set():
                    raise StopTaskException("在暫停狀態下被強制停止")
                self.pause_event.wait(0.5) # 每 0.5 秒醒來偷看一下有沒有被按停止
            
            print("動作恢復！")
    # =========================
    # 填寫答案
    # =========================
    def fill_result_relative(self, original_board, solved_board):
        print("開始填入答案...")

        cell_w = self.region_info["cell_w"]
        cell_h = self.region_info["cell_h"]
        start_x = self.region_info["left"]
        start_y = self.region_info["top"]

        for r in range(9):
            for c in range(9):
                self.wait_if_paused()
                if original_board[r][c] != 0:
                    continue

                val = solved_board[r][c]

                # A. 點格子
                cx = start_x + c * cell_w + cell_w // 2
                cy = start_y + r * cell_h + cell_h // 2
                self.adb.tap(cx, cy)
                time.sleep(0)

                # B. 點數字
                btn_idx = val - 1
                bx = start_x + self.btn_info["BTN_OFFSET_X"] + btn_idx * self.btn_info["BTN_GAP"]
                by = start_y + self.btn_info["BTN_OFFSET_Y"]
                self.adb.tap(bx, by)

                time.sleep(0)

        print("填寫完成")

    def click_target(self, img_name, timeout=30, threshold=0.8, wait_time = 0):  #等待並點擊
        """
        [升級版] 偵測圖片並點擊 (支援等待模式)
        :param img_name: 圖片檔名
        :param off_x, off_y: 偏移量
        :param timeout: 等待超時時間 (秒)。
        填 0 = 看一眼沒看到就走 (即時模式)。
        填 10 = 最多等 10 秒，期間一出現就點 (等待模式)。
        """
        print(f"尋找目標 {img_name}...")
        
        start_time = time.time() # 紀錄開始時間

        while True:
            # 1. 截圖
            screen = self.adb.get_screenshot()
            
            if screen is not None:
                # 2. 找圖
                pos = self.vision.find_and_get_pos(screen, img_name, threshold=threshold)
                
                if pos:
                    time.sleep(wait_time)
                    cx, cy = pos
                    print(f"   發現目標！")
                    self.adb.tap(cx, cy)
                    return True # 任務完成，跳出

            # 3. 檢查是否超時
            elapsed_time = time.time() - start_time
            if elapsed_time > timeout:
                # 時間到了還沒找到
                if timeout > 0:
                    print(f"   等待超時 ({timeout}s)，未發現 {img_name}")
                return False

            # 4. 還沒超時，休息一下再試
            time.sleep(1.0)

