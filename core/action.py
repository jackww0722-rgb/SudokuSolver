# action.py
import pyautogui
import time
from pathlib import Path
from .config import CLICK_DELAY, ACTION_WAIT, BTN_OFFSET_X, BTN_OFFSET_Y, BTN_GAP, MOUSE_PAUSE_TIME
pyautogui.PAUSE = MOUSE_PAUSE_TIME
from . import vision


# 🖱️ 第三部分：自動操作 (相對座標版)
# ==========================================

def click_position(image_path: Path):
    """
    通用的點擊函數
    position: 可以是 pyautogui.Point 物件 或 tuple (x, y)
    """

    location = vision.find_image_center(image_path)
    if location:
        x, y = location
        print(f"🖱️ 點擊座標: {x}, {y}")
        pyautogui.click(x, y)
        time.sleep(0.5) # 點擊後的緩衝，避免操作過快
        return True
    else:
        print("⚠️ 無法點擊：座標為 None")
        return False


def fill_result_relative(original_board, solved_board, region_info):
    print("✍️ 開始填入答案 (相對座標模式)...")
    print("🛑 緊急停止：滑鼠甩至左上角")
    
    cell_w = region_info['cell_w']
    cell_h = region_info['cell_h']
    start_x = region_info['left']
    start_y = region_info['top']

    for row in range(9):
        for col in range(9):
            if original_board[row][col] == 0:
                num_to_fill = solved_board[row][col]
                
                # 1. 點擊「格子」
                cell_center_x = start_x + (col * cell_w) + (cell_w // 2)
                cell_center_y = start_y + (row * cell_h) + (cell_h // 2)
                
                pyautogui.moveTo(cell_center_x, cell_center_y, duration=0.1)
                pyautogui.click()
                time.sleep(CLICK_DELAY)
                
                # 2. 計算「按鈕」的相對位置 (數學公式)
                # 邏輯：棋盤左邊 + 按鈕起始偏移 + (數字幾 * 間距)
                # 注意：num_to_fill 是 1~9，所以要減 1 才能變成 0~8 的索引
                btn_index = num_to_fill - 1
                
                btn_x = start_x + BTN_OFFSET_X + (btn_index * BTN_GAP)
                btn_y = start_y + BTN_OFFSET_Y
                
                # 3. 點擊「按鈕」
                pyautogui.moveTo(btn_x, btn_y, duration=0.1)
                pyautogui.click()
                time.sleep(CLICK_DELAY)
                
                # 休息一下
                time.sleep(ACTION_WAIT)
    
    print("🎉 完成！")
