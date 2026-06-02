import sys
from pathlib import Path
import logging
from logging.handlers import TimedRotatingFileHandler

#=============================
DEBUG_MODE = True
#=============================

def get_base_path() -> Path:
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    else:
        return Path(__file__).resolve().parent.parent

BASE_DIR = get_base_path()


LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

def setup_logger():
    """建立一個支援「終端機顯示」與「檔案寫入」的雙向記錄器"""
    log = logging.getLogger("SudokuBot")
    
    # 預設攔截 INFO 等級以上的訊息
    # 如果 SysConfig 裡的 DEBUG_MODE 有開，就連 DEBUG 等級也一起攔截
    log.setLevel(logging.DEBUG if DEBUG_MODE else logging.INFO)

    # 避免重複綁定處理器 (這在熱重載時很重要)
    if not log.handlers:
        # 1. 檔案處理器 (寫入 txt 檔，指定 utf-8 避免 Windows 亂碼)


        #每天切割一次，保留最近 3 天
        file_handler = TimedRotatingFileHandler(
            filename=str(LOG_DIR / "bot_run.log"),
            when="midnight",     # 每天午夜結算
            interval=1,          # 間隔 1 天
            backupCount=3,       # 保留 3 天
            encoding='utf-8'
        )
        # 檔案裡的格式要嚴謹一點，包含完整日期
        file_formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        file_handler.setFormatter(file_formatter)

        # 2. 終端機處理器 (印在螢幕上)
        console_handler = logging.StreamHandler(sys.stdout)
        # 螢幕上的格式可以精簡一點，只要時間就好
        console_formatter = logging.Formatter('[%(asctime)s] %(message)s', datefmt='%H:%M:%S')
        console_handler.setFormatter(console_formatter)

        # 把兩個處理器裝上機器
        log.addHandler(file_handler)
        log.addHandler(console_handler)

    return log

logger = setup_logger()