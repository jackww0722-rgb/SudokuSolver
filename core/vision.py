# vision.py
import cv2
import os
import pyautogui
import numpy as np
import time
from . import config
from pathlib import Path
_TEMPLATE_CACHE = {}

# Grand Order
def scan_board():
    """
    一條龍服務：自動找到盤面位置，並辨識出裡面的數字
    回傳: 
        - 成功: (9x9的二維陣列, 盤面座標區域)
        - 失敗: (None, None)
    """
    # 1. 先找位置 (內部呼叫)
    region = get_board_position()
    
    if not region:
        print("❌ 找不到盤面！")
        return None, None

    # 2. 載入範本 (如果還沒載入的話)
    # 建議把 load_templates() 也藏在 vision 裡面
    templates = load_templates()

    # 3. 辨識數字
    board_numbers = recognize_board(region, templates)
    
    return board_numbers, region

# 👁️ 視覺識別
# ==========================================

def _get_template_image(image_path: Path):
    """
    (內部函數) 讀取圖片並快取。
    如果記憶體有了，就直接給；沒有才去硬碟讀。
    """
    path_str = str(image_path)
    
    # 檢查快取
    if path_str in _TEMPLATE_CACHE:
        return _TEMPLATE_CACHE[path_str]
    
    # 讀取圖片
    if not image_path.exists():
        print(f"❌ 錯誤：找不到圖片 {image_path}")
        return None
        
    img = cv2.imread(path_str, 0) # 灰階讀取
    if img is None:
        print(f"❌ 錯誤：無法讀取圖片格式 {image_path}")
        return None
        
    # 存入快取
    _TEMPLATE_CACHE[path_str] = img
    return img



def load_templates():
    templates = {}
    print(f"📂 正在載入數字範本...")
    if not config.TEMPLATE_FOLDER.exists():
        print("❌ 錯誤：找不到 templates 資料夾！")
        return {}
    for i in range(1, 10):
        templates[i] = [] 
        path = os.path.join(config.TEMPLATE_FOLDER, f'{i}.png')
        if os.path.exists(path): templates[i].append(cv2.imread(path, 0))
        for v in range(2, 6):
            path_v = os.path.join(config.TEMPLATE_FOLDER, f'{i}_v{v}.png')
            if os.path.exists(path_v): templates[i].append(cv2.imread(path_v, 0))
    return templates

def find_image_center(image_path: Path, confidence=config.CONFIDENCE_THRESHOLD):
    """
    使用 OpenCV 進行螢幕圖形匹配 (灰階模式)
    
    Args:
        image_path (Path): 模板圖片路徑
        confidence (float): 相似度閾值 (0.0 ~ 1.0)
    
    Returns:
        tuple (x, y) 中心點座標 或 None
    """
    # 改用快取讀取函數，不再每次都 cv2.imread
    template = _get_template_image(image_path)
    if template is None: return None
    if template is None:
        print(f"❌ 錯誤：無法讀取圖片格式 {image_path}")
        return None

    template_h, template_w = template.shape[:2]

    # 2. 螢幕截圖 (Screenshot)
    # pyautogui 截圖預設是 RGB 格式
    screenshot = pyautogui.screenshot()
    screenshot_np = np.array(screenshot)
    
    # 3. 轉為灰階 (Convert to Grayscale)
    # OpenCV 處理顏色通常是 BGR，但 pyautogui 轉 numpy 是 RGB
    # 為了比對，我們統一轉成灰階即可，比較簡單且快速
    screen_gray = cv2.cvtColor(screenshot_np, cv2.COLOR_RGB2GRAY)

    # 4. 進行模板匹配 (Template Matching)
    result = cv2.matchTemplate(screen_gray, template, cv2.TM_CCOEFF_NORMED)
    
    # 5. 取得最佳匹配位置
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

    # 6. 判斷是否符合信心度
    if max_val >= confidence:
        top_left_x, top_left_y = max_loc
        
        # 計算中心點
        center_x = top_left_x + (template_w // 2)
        center_y = top_left_y + (template_h // 2)
        
        # print(f"✅ 找到目標 (信心度: {max_val:.2f})")
        return (center_x, center_y)
    
    return None


def get_board_position():
    print("🔍 正在尋找數獨錨點...")
    if not config.ANCHOR_IMAGE.exists(): return None
    try:
        loc = pyautogui.locateOnScreen(str(config.ANCHOR_IMAGE), confidence=config.ANCHOR_CONFIDENCE)
        if loc:
            return {
                'left': int(loc.left) + config.OFFSET_X,
                'top': int(loc.top) + config.OFFSET_Y,
                'width': config.ESTIMATED_BOARD_WIDTH,
                'height': config.ESTIMATED_BOARD_HEIGHT,
                'cell_w': config.ESTIMATED_BOARD_WIDTH // 9,
                'cell_h': config.ESTIMATED_BOARD_HEIGHT // 9
            }
    except: pass
    return None

def recognize_board(region_info, templates):
    print("📸 截取畫面並開始識別...")

    
    screenshot = pyautogui.screenshot(region=(region_info['left'], region_info['top'], region_info['width'], region_info['height']))
    board_img = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2GRAY)
    detected_board = [[0]*9 for _ in range(9)]
    cell_w, cell_h = region_info['cell_w'], region_info['cell_h']

    for row in range(9):
        for col in range(9):
            x, y = col * cell_w, row * cell_h
            center_x, center_y = x + cell_w // 2, y + cell_h // 2
            y1, y2 = center_y - config.CROP_RADIUS, center_y + config.CROP_RADIUS
            x1, x2 = center_x - config.CROP_RADIUS, center_x + config.CROP_RADIUS
            
            h, w = board_img.shape
            if x1 < 0: x1 = 0
            if y1 < 0: y1 = 0
            if x2 > w: x2 = w
            if y2 > h: y2 = h

            cell_img = board_img[y1:y2, x1:x2]

            best_score = 0
            best_num = 0
            for num, img_list in templates.items():
                for temp_img in img_list:
                    if temp_img.shape[0] > cell_img.shape[0] or temp_img.shape[1] > cell_img.shape[1]: continue
                    res = cv2.matchTemplate(cell_img, temp_img, cv2.TM_CCOEFF_NORMED)
                    score = np.max(res)
                    if score > best_score: best_score, best_num = score, num
            
            if best_score > config.CONFIDENCE_THRESHOLD: detected_board[row][col] = best_num
            else: detected_board[row][col] = 0

    print("\n👀 電腦看到的題目：")
    for r in detected_board: print(r)

    return detected_board


def wait_for_image(target_img, timeout=30):
    time.sleep(1.0)
    """
    [工具] 單純等待某張圖片出現 (不做任何點擊)
    :param timeout: 最多等幾秒，預設 10 秒
    :return: True (有等到) / False (超時沒等到)
    """
    _get_template_image(target_img)

    print(f"   ⏳ [Ops] 等待圖片出現: {target_img} ...")

    start_time = time.time()
    
    while time.time() - start_time < timeout:
        
        # 截圖並找圖

        
        if find_image_center(target_img):
            print(f"   ✅ 看到 {target_img} 了！")
            return True
        
        
    print(f"   ⚠️ 等待 {target_img} 超時 ({timeout}s)")
    return False


# 截圖
# ===========================================
def save_screenshot():
    print("📸 正在擷取最終畫面...")
    
    # 產生檔名    
    if not os.path.exists(config.SCREENSHOT_FOLDER):
        os.makedirs(config.SCREENSHOT_FOLDER)
        print(f"📁 已建立新資料夾: {'Screenshots'}")
    save_path = os.path.join(config.SCREENSHOT_FOLDER, '今天答案.png')
    # 程式會在上一個動作(點擊最後一個數字)做完的瞬間，立刻截圖。




    # --- 🧮 計算新的截圖區域 ---
    region = get_board_position()
    # 1. 新的左邊界 = 原本棋盤左邊 - 左側邊距 (利用 max(0, ...) 確保不會變成負數跑出螢幕外)
    new_left = max(0, region['left'] - config.MARGIN_SIDE)
    # 2. 新的上邊界 = 原本棋盤上邊 - 上方邊距
    new_top = max(0, region['top'] - config.MARGIN_TOP)
    # 3. 新的寬度 = 左邊距 + 原本棋盤寬 + 右邊距
    new_width = config.MARGIN_SIDE + region['width'] + config.MARGIN_SIDE
    # 4. 新的高度 = 上邊距 + 原本棋盤高 + 下邊距
    new_height = config.MARGIN_TOP + region['height'] + config.MARGIN_BOTTOM

    result_shot = pyautogui.screenshot(region=(int(new_left), int(new_top), int(new_width), int(new_height)))
    
    result_shot.save(save_path)
    print(f"✅ 截圖已儲存：{save_path}")

    return None
