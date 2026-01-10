# config.py
import pyautogui
from pathlib import Path



# ==========================================
# 🛑 安全與速度設定
# ==========================================
pyautogui.FAILSAFE = True 
CLICK_DELAY = 0        
ACTION_WAIT = 0
MOUSE_PAUSE_TIME = 0.06

# ==========================================
# ⚙️ 參數設定區 (請填入數值)
# ==========================================
# 取得當前檔案的路徑，並解析成絕對路徑
# .parent = 上一層 (core)
# .parent.parent = 上兩層 (專案根目錄)
BASE_DIR = Path(__file__).resolve().parent.parent

# 拼路徑不用再寫 os.path.join 了！
# 直接用「除號 /」就可以把路徑接起來，超直覺
TEMPLATE_FOLDER = BASE_DIR / "templates"
ANCHOR_IMAGE = TEMPLATE_FOLDER / "anchor.png"
SCREENSHOT_FOLDER = BASE_DIR / "Screenshots"
START_BUTTON_IMAGE = TEMPLATE_FOLDER / "start_btn.png"
normal_diff_image = TEMPLATE_FOLDER / "normal_diff.png"
clear_image = TEMPLATE_FOLDER / "clear.png"

# 遊戲編號
package_name = "com.linecorp.LGSNPTW"
# 裝置編號
device_serial = "R5CW915J6XV"

# 1. 棋盤參數 (之前測過的)
ESTIMATED_BOARD_WIDTH = 400     
ESTIMATED_BOARD_HEIGHT = 400     
OFFSET_X = 7                     
OFFSET_Y = 36                     

# 2. 識別參數
CROP_RADIUS = 15                 
CONFIDENCE_THRESHOLD = 0.60      
ANCHOR_CONFIDENCE = 0.8          

# 3. 🎛️ 按鈕參數 (請填入剛剛在 debug_buttons.py 測出的數值)
BTN_OFFSET_X = 21    # 第一個按鈕的 X
BTN_OFFSET_Y = 600   # 按鈕的 Y (垂直高度)
BTN_GAP = 44         # 按鈕間距

# 4. 截圖參數
# --- 📐 定義要向外擴張多少像素 (你可以根據實際情況調整這裡) ---
# 數獨棋盤通常在畫面中間偏下，所以上方要留多一點空間給標題欄
MARGIN_TOP = 200    # 上方擴張像素 (例如：狀態列、App標題)
MARGIN_BOTTOM = 250 # 下方擴張像素 (例如：按鈕區、廣告)
MARGIN_SIDE = 10    # 左右兩側擴張像素