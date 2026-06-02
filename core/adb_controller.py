import numpy as np
import cv2
import time
import random
from typing import Any
from adbutils import adb
import os
from pathlib import Path
from .logger import logger


class AdbController:
    def __init__(self, adb_config: dict[str, Any]):
        """
        1. 初始化階段：只綁定設定檔，預設所有屬性。
        絕對不碰網路連線，保證瞬間建立物件不報錯。
        """
        self.adb_config = adb_config
        self.device: Any = None
        

        # 設定 ADB 路徑可以放在這裡，因為這只是修改本地變數
        self._setup_custom_adb_env()

    def _setup_custom_adb_env(self):
        """ 
        [內部工具] 動態注入 ADB 路徑，徹底消滅 Pylance 紅線與依賴問題 
        """
        # 假設你的 adb.exe 放在專案根目錄的 "tools" 資料夾下
        # 利用 pathlib 精準定位絕對路徑
        adb_path_str = self.adb_config.get("ADB_PATH")

        # 確認資料夾真的存在
        if adb_path_str:
            # 轉換為 pathlib 物件以方便操作
            custom_adb_file = Path(adb_path_str)
            
            if custom_adb_file.exists():
                # .parent 可以精準抓出資料夾位置 (例如: C:\tools)
                adb_folder = custom_adb_file.parent
                
                # 將該資料夾強制插隊到 Windows 系統變數 PATH 的最前面
                # 這樣底層的 adbutils 在呼叫 "adb" 指令時，一定會優先用到你指定的這支！
                os.environ["PATH"] = f"{adb_folder};{os.environ.get('PATH', '')}"
                logger.debug(f"🔧 已動態掛載自訂 ADB 引擎目錄: {adb_folder}")
            else:
                logger.warning(f"⚠️ 設定檔中的 ADB 路徑不存在: {custom_adb_file}")

    def connect(self) -> bool:
        """
        2. 連線階段：由外部主動呼叫，負責連線並更新設備狀態。
        """
        target_serial = self.adb_config.get("device_serial", "").strip()
        logger.debug(f"正在準備連線...")

        try:
            if not target_serial:
                logger.warning("未指定序號，正在自動搜尋裝置...")
                devices = adb.device_list() # type: ignore
                if not devices:
                    raise RuntimeError("未偵測到任何 ADB 裝置！請確認模擬器已開啟。")
                self.device = devices[0]
                self.device.shell("echo hello") # 測試連線
                logger.debug(f"自動鎖定裝置: {self.device.serial}")
            else:
                self.device = adb.device(serial=target_serial)
                self.device.shell("echo hello") # 測試連線
                logger.debug(f"連線成功: {self.device.serial}")
            
            return True
            
        except Exception as e:
            logger.warning(f"連線失敗: {e}")
            return False

    def get_screenshot(self):
        """ 
        [核心功能] 獲取畫面
        回傳: OpenCV BGR 格式圖片
        """
        try:
            cmd = "screencap -p"
            connection = self.device.shell(cmd, stream=True)
            
            # 2. 【修正點】改用迴圈分批讀取
            # Pylance 抱怨 read() 需要參數，我們就每次讀 4096 bytes (4KB)
            # 這樣也比較不會因為網路延遲造成圖片讀取不完整
            data_buffer = bytearray()
            while True:
                chunk = connection.read(4096) # 每次讀 4KB
                if not chunk:
                    break # 讀不到東西代表結束了
                data_buffer.extend(chunk)
            
            raw_bytes = bytes(data_buffer)
            # 2. 直接解碼為 OpenCV 格式 (預設就是 BGR，不用再 cvtColor)
            img_array = np.frombuffer(raw_bytes, np.uint8)
            raw_img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

            if raw_img is None:
                logger.warning("截圖解碼失敗 (回傳 None)")
                return None

            return raw_img
        
        except Exception as e:
            logger.warning(f"截圖流程發生錯誤: {e}")
            return None

    def tap(self, x, y, offset: int = 0, delay: tuple[float, float] | None = None):
        """
        [輸出端] 標準座標
        """
        # 1. 計算偏移
        click_x = x + random.randint(-offset, offset) if offset > 0 else x
        click_y = y + random.randint(-offset, offset) if offset > 0 else y

        # 2. 執行真實的 ADB 點擊指令
        self.device.click(click_x, click_y)

        # 3. 處理 UI 延遲
        if delay:
            min_delay, max_delay = delay
            time.sleep(random.uniform(min_delay, max_delay))
        

    def stop_app(self, package_name:str | None = None):
        target = package_name or self.adb_config["target_app_package"]
        logger.debug(f"正在關閉 APP: {target}")
        self.device.app_stop(target)

    def start_app(self, package_name:str | None = None):
        target = package_name or self.adb_config["target_app_package"]
        logger.debug(f"正在開啟 APP: {target}")
        self.device.app_start(target)

    def restart_app(self, package_name:str | None = None):
        self.stop_app(package_name)
        time.sleep(3.0) # 系統反應時間
        self.start_app(package_name)
