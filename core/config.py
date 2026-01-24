# config.py
from pathlib import Path
from dataclasses import dataclass

@dataclass
class GameConfig:

    # 取得當前檔案的路徑，並解析成絕對路徑
    # .parent = 上一層 (core)
    # .parent.parent = 上兩層 (專案根目錄)
    BASE_DIR = Path(__file__).resolve().parent.parent
    TEMPLATE_FOLDER = BASE_DIR / "templates"

    # ADB設定
    adb_config = {
        "ADB_PATH" : Path("D:\\Program Files\\Netease\\MuMuPlayer\\nx_main\\adb.exe"),
        "target_app_package" : "com.linecorp.LGSNPTW",
        "device_serial" : "R5CW915J6XV",
        "design_width" : 1080,
        "design_height" : 2340
    }

    # 棋盤參數 (之前測過的)
    region_info = {
        'left': 35,  
        'top': 505,
        'cell_w': 1011 // 9,
        'cell_h': 1011 // 9
    }

    # 識別參數
    vision_info = {
    "CROP_RADIUS" : 35,                 
    "CONFIDENCE_THRESHOLD" : 0.80,      
    "ANCHOR_CONFIDENCE" : 0.3
    }   

    #  按鈕座標
    # 這些 Offset 是相對於 BOARD_LEFT 和 BOARD_TOP 的距離
    btn_info = {
    "BTN_OFFSET_X" : 49,
    "BTN_OFFSET_Y" : 1516,  
    "BTN_GAP" : 114,        
    }
