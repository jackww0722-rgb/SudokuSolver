# core/action.py
import time
import random
from adbutils import adb
from . import config


class AdbActionBot:
    def __init__(self):
        # 告訴 adbutils adb.exe 在哪
        try:
            adb.adb_path = str(config.ADB_PATH)
        except:
            pass

        print(f"🎮 Action 連線中: {config.DEVICE_ID}...")
        self.device = adb.device(serial=config.DEVICE_ID)

    # =========================
    # 基本操作
    # =========================
    def tap(self, x, y):
        """帶微小隨機偏移的點擊"""
        rx = int(x + random.randint(-3, 3))
        ry = int(y + random.randint(-3, 3))
        self.device.click(rx, ry)

    def wait(self, t=None):
        time.sleep(t if t is not None else config.CLICK_DELAY)

    # =========================
    # App 控制
    # =========================
    def restart_app(self):
        print(f"☢️ 重啟 App: {config.PACKAGE_NAME}")
        self.device.shell(f"am force-stop {config.PACKAGE_NAME}")
        time.sleep(1)
        self.device.shell(
            f"monkey -p {config.PACKAGE_NAME} "
            f"-c android.intent.category.LAUNCHER 1"
        )
        time.sleep(5)

    # =========================
    # 填寫答案
    # =========================
    def fill_result_relative(self, original_board, solved_board, region_info):
        print("✍️ [Action] 開始填入答案...")

        cell_w = region_info["cell_w"]
        cell_h = region_info["cell_h"]
        start_x = region_info["left"]
        start_y = region_info["top"]

        for r in range(9):
            for c in range(9):
                if original_board[r][c] != 0:
                    continue

                val = solved_board[r][c]

                # A. 點格子
                cx = start_x + c * cell_w + cell_w // 2
                cy = start_y + r * cell_h + cell_h // 2
                self.tap(cx, cy)
                time.sleep(0)

                # B. 點數字
                btn_idx = val - 1
                bx = config.BOARD_LEFT + config.BTN_OFFSET_X + btn_idx * config.BTN_GAP
                by = config.BOARD_TOP + config.BTN_OFFSET_Y
                self.tap(bx, by)

                time.sleep(0)

        print("🎉 填寫完成")
