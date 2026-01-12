import cv2
import numpy as np
import subprocess
import shutil
from pathlib import Path

# ==========================================
# ⚙️ 1. 您的參數設定區 (直接填入)
# ==========================================
BOARD_LEFT = 35
BOARD_TOP = 505
BOARD_WIDTH = 1011
BOARD_HEIGHT = 1011

# 自動計算單格大小
CELL_WIDTH = BOARD_WIDTH // 9
CELL_HEIGHT = BOARD_HEIGHT // 9

# 識別參數 (中心切割法)
CROP_RADIUS = 35  # 從中心點往外擴張 35px (即切出 70x70 的圖)

# 輸出的資料夾名稱
OUTPUT_DIR = Path("output_cells")

def capture_screen_adb():
    """透過 ADB 截取手機螢幕 (原始解析度)"""
    print("📸 正在透過 ADB 截取原始畫質圖片...")
    try:
        # 使用 exec-out 直接讀取，確保是原始解析度 (1080p/2k)
        pipe = subprocess.Popen(
            ["adb", "-s", "R5CW915J6XV", "exec-out", "screencap", "-p"],
            stdout=subprocess.PIPE,
            shell=True
        )
        image_bytes = pipe.stdout.read()
        
        if not image_bytes:
            print("❌ 截圖失敗")
            return None

        image_array = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
        
        print(f"✅ 截圖成功！解析度: {img.shape[1]}x{img.shape[0]}")
        return img
    except Exception as e:
        print(f"❌ 發生錯誤: {e}")
        return None

def slice_by_coordinates(image):
    if image is None: return

    # 1. 準備輸出資料夾
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True)

    # 2. 裁切出大盤面
    # 注意：y在前, x在後
    board_img = image[BOARD_TOP : BOARD_TOP + BOARD_HEIGHT, 
                      BOARD_LEFT : BOARD_LEFT + BOARD_WIDTH]
    
    # 建立預覽圖 (用來畫線檢查)
    debug_view = image.copy()
    # 畫出大盤面框 (藍色)
    cv2.rectangle(debug_view, 
                  (BOARD_LEFT, BOARD_TOP), 
                  (BOARD_LEFT + BOARD_WIDTH, BOARD_TOP + BOARD_HEIGHT), 
                  (255, 0, 0), 3)

    print(f"🚀 開始切割 81 個格子 (使用半徑 {CROP_RADIUS} 切割中心)...")

    for row in range(9):
        for col in range(9):
            # 計算該格「在原圖上」的左上角座標
            cell_x_origin = BOARD_LEFT + (col * CELL_WIDTH)
            cell_y_origin = BOARD_TOP + (row * CELL_HEIGHT)
            
            # 計算「中心點」
            center_x = cell_x_origin + (CELL_WIDTH // 2)
            center_y = cell_y_origin + (CELL_HEIGHT // 2)

            # --- 核心修改：使用 CROP_RADIUS 切割中心 ---
            # 這樣可以避開格子邊緣的黑線
            x1 = center_x - CROP_RADIUS
            x2 = center_x + CROP_RADIUS
            y1 = center_y - CROP_RADIUS
            y2 = center_y + CROP_RADIUS

            # 防呆：確保不超出邊界
            if y1 < 0 or x1 < 0: continue

            cell = image[y1:y2, x1:x2]
            
            # 存檔
            filename = OUTPUT_DIR / f"cell_{row}_{col}.png"
            is_success, im_buf = cv2.imencode(".png", cell)
            if is_success:
                im_buf.tofile(str(filename))

            # --- 在預覽圖上畫出切割範圍 (綠色小框) ---
            cv2.rectangle(debug_view, (x1, y1), (x2, y2), (0, 255, 0), 2)

    # 存檔預覽圖 (覆蓋整張螢幕截圖，方便您確認位置)
    preview_path = OUTPUT_DIR / "grid_preview_fixed.png"
    cv2.imencode(".png", debug_view)[1].tofile(str(preview_path))
    
    print(f"✨ 完成！")
    print(f"📁 81 張格子已存於: {OUTPUT_DIR.absolute()}")
    print(f"👀 請檢查: {preview_path.absolute()}")

if __name__ == "__main__":
    img = capture_screen_adb()
    # 簡單防呆：確認截圖寬度是否夠大
    if img is not None:
        h, w = img.shape[:2]
        if w < 1000:
            print(f"⚠️ 警告：您的截圖寬度只有 {w}，但參數設定的寬度是 1011。")
            print("這表示您的截圖可能被 Scrcpy 縮小了，或者您需要將手機直立/橫放。")
        else:
            slice_by_coordinates(img)