# config.py
from pathlib import Path



# ==========================================
# 🛑 安全速度與裝置名稱設定
# ==========================================

CLICK_DELAY = 0.5        
ACTION_WAIT = 1

DEVICE_ID = "R5CW915J6XV"
ADB_PATH = r"D:\\Program Files\\Netease\\MuMuPlayer\\nx_main\\adb.exe"

PACKAGE_NAME = "com.easybrain.sudoku.android"

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


# 1. 棋盤參數 (之前測過的)
BOARD_LEFT = 35
BOARD_TOP = 505
BOARD_WIDTH = 1011
BOARD_HEIGHT = 1011

# 自動計算單格大小 (無須手動修改)
CELL_WIDTH = BOARD_WIDTH // 9
CELL_HEIGHT = BOARD_HEIGHT // 9

# 2. 識別參數
CROP_RADIUS = 35                 
CONFIDENCE_THRESHOLD = 0.80      
ANCHOR_CONFIDENCE = 0.3          


# ==========================================
# 🔢 按鈕座標設定
# ==========================================
# 這些 Offset 是相對於 BOARD_LEFT 和 BOARD_TOP 的距離
BTN_OFFSET_X = 49    # 數字 1 按鈕中心 相對於 Board Left
BTN_OFFSET_Y = 1516  # 數字按鈕中心 Y 相對於 Board Top
BTN_GAP = 114        # 按鈕之間的間距

