import cv2
import numpy as np
import subprocess
import sys
import ctypes
import os  # 新增 os 模組用來檢查檔案

# --- Windows DPI 設定 ---
try:
    ctypes.windll.user32.SetProcessDPIAware()
except:
    pass

# ==========================================
# 🛑 設定區 (修正重點)
# ==========================================
DEVICE_ID = "R5CW915J6XV"  

# ⚠️ 修正 1: 前面加上 r，變成 raw string，避免 \n 被當成換行
ADB_PATH = r"D:\Program Files\Netease\MuMuPlayer\nx_main\adb.exe"

# ==========================================

import os
import time

def get_screenshot():
    print("-" * 30)
    print("📸 正在截取畫面 (使用檔案傳輸模式)...")
    
    # 檢查 ADB 執行檔
    if not os.path.exists(ADB_PATH):
        print(f"❌ 找不到 ADB: {ADB_PATH}")
        return None

    # 定義手機端和電腦端的暫存路徑
    remote_path = "/sdcard/adb_temp_screen.png"
    local_path = "adb_temp_screen.png" # 存放在目前資料夾

    try:
        # 步驟 1: 在手機上截圖並存檔
        # cmd: adb -s DEVICE shell screencap -p /sdcard/xxx.png
        cmd_cap = [ADB_PATH]
        if DEVICE_ID:
            cmd_cap.extend(["-s", DEVICE_ID])
        cmd_cap.extend(["shell", "screencap", "-p", remote_path])
        
        subprocess.run(cmd_cap, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

        # 步驟 2: 把檔案拉回電腦
        # cmd: adb -s DEVICE pull /sdcard/xxx.png local.png
        cmd_pull = [ADB_PATH]
        if DEVICE_ID:
            cmd_pull.extend(["-s", DEVICE_ID])
        cmd_pull.extend(["pull", remote_path, local_path])
        
        subprocess.run(cmd_pull, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

        # 步驟 3: OpenCV 讀取圖片
        if os.path.exists(local_path):
            # 使用 cv2.imdecode 搭配 np.fromfile 讀取 (支援中文路徑且避免鎖死)
            img = cv2.imdecode(np.fromfile(local_path, dtype=np.uint8), cv2.IMREAD_COLOR)
            print(f"✅ 截圖成功！尺寸: {img.shape[1]}x{img.shape[0]}")
            
            # (選用) 清理電腦上的暫存檔，如果你想留著檢查可以註解掉這行
            try:
                os.remove(local_path)
            except:
                pass
                
            return img
        else:
            print("❌ 錯誤：拉取檔案失敗，電腦上找不到圖片。")
            return None

    except subprocess.CalledProcessError:
        print("❌ 錯誤：ADB 指令執行失敗 (手機可能斷線或未授權)。")
        return None
    except Exception as e:
        print(f"❌ 未知錯誤: {e}")
        return None

    except Exception as e:
        print(f"❌ 未知例外錯誤: {e}")
        return None

def nothing(x):
    pass

def main():
    # 1. 取得截圖 (詳細除錯版)
    img_original = get_screenshot()
    
    if img_original is None: 
        print("-" * 30)
        print("🚫 程式因截圖失敗而終止。請參考上方錯誤訊息。")
        # 這裡加個 input 暫停，確保你有看到訊息
        input("按 Enter 鍵離開...") 
        return
    
    # --- 以下為原本的 Tuner 邏輯 ---
    h_screen, w_screen = img_original.shape[:2]
    
    # 預設參數
    INIT_BOARD_X = 50
    INIT_BOARD_Y = 300
    INIT_BOARD_W = 900
    INIT_BOARD_H = 900
    INIT_BTN_OFFSET_X = 50
    INIT_BTN_OFFSET_Y = 1000
    INIT_BTN_GAP = 100

    WINDOW_NAME = "Config Tuner (Debug Mode)"
    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WINDOW_NAME, 540, 960)

    cv2.createTrackbar("Board X", WINDOW_NAME, INIT_BOARD_X, w_screen, nothing)
    cv2.createTrackbar("Board Y", WINDOW_NAME, INIT_BOARD_Y, h_screen, nothing)
    cv2.createTrackbar("Board W", WINDOW_NAME, INIT_BOARD_W, w_screen, nothing)
    cv2.createTrackbar("Board H", WINDOW_NAME, INIT_BOARD_H, h_screen, nothing)
    cv2.createTrackbar("Btn Off X", WINDOW_NAME, INIT_BTN_OFFSET_X, w_screen, nothing)
    cv2.createTrackbar("Btn Off Y", WINDOW_NAME, INIT_BTN_OFFSET_Y, int(h_screen * 1.5), nothing)
    cv2.createTrackbar("Btn Gap", WINDOW_NAME, INIT_BTN_GAP, 300, nothing)

    print("=== 調校模式啟動 ===")
    print("按 [Q] 離開, [P] 輸出參數")

    while True:
        display = img_original.copy()
        
        b_x = cv2.getTrackbarPos("Board X", WINDOW_NAME)
        b_y = cv2.getTrackbarPos("Board Y", WINDOW_NAME)
        b_w = cv2.getTrackbarPos("Board W", WINDOW_NAME)
        b_h = cv2.getTrackbarPos("Board H", WINDOW_NAME)
        btn_off_x = cv2.getTrackbarPos("Btn Off X", WINDOW_NAME)
        btn_off_y = cv2.getTrackbarPos("Btn Off Y", WINDOW_NAME)
        btn_gap = cv2.getTrackbarPos("Btn Gap", WINDOW_NAME)

        # 畫棋盤
        cv2.rectangle(display, (b_x, b_y), (b_x + b_w, b_y + b_h), (0, 255, 0), 2)
        cell_w = b_w // 9
        cell_h = b_h // 9
        for r in range(9):
            for c in range(9):
                cx = b_x + c * cell_w + cell_w // 2
                cy = b_y + r * cell_h + cell_h // 2
                cv2.line(display, (cx-5, cy), (cx+5, cy), (0, 255, 0), 1)
                cv2.line(display, (cx, cy-5), (cx, cy+5), (0, 255, 0), 1)

        # 畫按鈕
        for i in range(9):
            bx = b_x + btn_off_x + (i * btn_gap)
            by = b_y + btn_off_y
            cv2.circle(display, (bx, by), 15, (0, 0, 255), 2)
            cv2.putText(display, str(i+1), (bx-10, by+5), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

        cv2.imshow(WINDOW_NAME, display)
        
        key = cv2.waitKey(20) & 0xFF
        if key == ord('q') or key == 27:
            break
        elif key == ord('p'):
            print(f"\nBOARD_LEFT={b_x}\nBOARD_TOP={b_y}\nBOARD_WIDTH={b_w}\nBOARD_HEIGHT={b_h}")
            print(f"BTN_OFFSET_X={btn_off_x}\nBTN_OFFSET_Y={btn_off_y}\nBTN_GAP={btn_gap}")

    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()