import cv2
import numpy as np
import subprocess
from pathlib import Path

# ==========================================
# ⚙️ 當前設定的參數 (我們要檢查這些對不對)
# ==========================================
# 請確認這跟您 config 裡的數字一模一樣
BOARD_LEFT = 35
BOARD_TOP = 505
BOARD_WIDTH = 1011
BOARD_HEIGHT = 1011
CROP_RADIUS = 35

def check_alignment():
    print("📸 正在截圖檢查對齊狀況...")
    
    # 1. 透過 ADB 截圖
    try:
        pipe = subprocess.Popen(
            ["adb","-s", "R5CW915J6XV", "exec-out", "screencap", "-p"],
            stdout=subprocess.PIPE,
            shell=True
        )
        image_bytes = pipe.stdout.read()
        if not image_bytes:
            print("❌ 截圖失敗")
            return
            
        img_array = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        
        h, w = img.shape[:2]
        print(f"📏 實際截圖解析度: {w} x {h}")
        
    except Exception as e:
        print(f"❌ 錯誤: {e}")
        return

    # 2. 準備畫圖
    debug_img = img.copy()
    
    # 計算單格大小
    CELL_WIDTH = BOARD_WIDTH // 9
    CELL_HEIGHT = BOARD_HEIGHT // 9
    
    # 3. 畫出每一個「準心」
    for row in range(9):
        for col in range(9):
            # 計算中心點
            cell_x_origin = BOARD_LEFT + (col * CELL_WIDTH)
            cell_y_origin = BOARD_TOP + (row * CELL_HEIGHT)
            
            center_x = cell_x_origin + (CELL_WIDTH // 2)
            center_y = cell_y_origin + (CELL_HEIGHT // 2)
            
            # 畫出切割範圍 (綠色框框)
            x1 = center_x - CROP_RADIUS
            x2 = center_x + CROP_RADIUS
            y1 = center_y - CROP_RADIUS
            y2 = center_y + CROP_RADIUS
            
            # 繪製綠框 (代表電腦切圖的範圍)
            cv2.rectangle(debug_img, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            # 繪製紅點 (代表中心點)
            cv2.circle(debug_img, (center_x, center_y), 3, (0, 0, 255), -1)

    # 4. 畫出整個大盤面的範圍 (藍色框)
    cv2.rectangle(debug_img, (BOARD_LEFT, BOARD_TOP), 
                  (BOARD_LEFT + BOARD_WIDTH, BOARD_TOP + BOARD_HEIGHT), (255, 0, 0), 3)

    # 5. 存檔並自動開啟
    output_path = "alignment_check.png"
    cv2.imwrite(output_path, debug_img)
    print(f"✅ 校正圖已儲存: {output_path}")
    print("🚀 請打開圖片，檢查綠色框框偏向哪一邊？")
    
    # 嘗試自動打開圖片 (Windows)
    try:
        subprocess.run(["start", output_path], shell=True)
    except:
        pass

if __name__ == "__main__":
    check_alignment()