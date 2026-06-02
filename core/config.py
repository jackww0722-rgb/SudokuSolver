import sys
import configparser
from pathlib import Path
from dataclasses import dataclass

# 1. 取得執行檔所在路徑 (打包 exe 必備)
def get_base_path():
    if getattr(sys, 'frozen', False):
        # 如果是打包後的 exe，回傳 exe 所在的資料夾
        return Path(sys.executable).parent
    else:
        # 如果是開發模式 (py)，回傳專案根目錄 (根據你的檔案結構調整)
        return Path(__file__).resolve().parent.parent

@dataclass
class GameConfig:
    # ==========================
    # 📁 路徑與基礎設定
    # ==========================
    BASE_DIR = get_base_path()
    TEMPLATE_FOLDER = BASE_DIR / "templates"
    INI_PATH = BASE_DIR / "settings.ini"  # 外部設定檔路徑

    # ==========================
    # 📱 ADB 與 裝置設定 (預設值)
    # 這些值會被 settings.ini 覆寫
    # ==========================
    adb_config = {
        # 如果使用者沒設，就留空 (讓系統自己找)
        "ADB_PATH": str(BASE_DIR / "adb_tools" /  "adb.exe"), 
        "target_app_package": "com.linecorp.LGSNPTW",
        # 預設序號 (預設留空，反正會優先讀 ini)
        "device_serial": "", 
        "design_width": 1080,
        "design_height": 2340
    }

    # ==========================
    # 🎮 遊戲內參數 (通常不需變動)
    # ==========================
    # 識別參數
    vision_info = {
        "CROP_RADIUS": 35,                 
        "CONFIDENCE_THRESHOLD": 0.80,      
        "ANCHOR_CONFIDENCE": 0.3
    }   

    DEBUG_MODE = False
    
    # ==========================
    # ⚙️ 動態載入邏輯
    # ==========================
    @classmethod
    def load_settings(cls):
        """ 嘗試讀取 settings.ini 並更新 adb_config """
        if not cls.INI_PATH.exists():
            return

        config = configparser.ConfigParser()
        # 設定讀取編碼，避免中文路徑亂碼
        config.read(cls.INI_PATH, encoding='utf-8')

        # 如果 ini 裡面有 [ADB] 區塊，就更新字典
        if 'ADB' in config:
            adb_section = config['ADB']
            
            # 使用 get 更新，如果 ini 沒寫該欄位就維持原樣
            # 注意：INI 讀出來都是字串
            if adb_section.get('adb_path'):
                cls.adb_config['ADB_PATH'] = adb_section.get('adb_path')
            
            if adb_section.get('device_serial'):
                cls.adb_config['device_serial'] = adb_section.get('device_serial')

        if 'GAME' in config:
            cls.DEBUG_MODE = config.getboolean('Game', 'debug_mode', fallback=False)


# --- 自動執行載入 ---
GameConfig.load_settings()