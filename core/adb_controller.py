import subprocess
import numpy as np
import random
import cv2
import time
import adbutils as adb
from typing import Any




class AdbController:
    def __init__(self, adb_config : dict[str, Any]):
        self.adb_config = adb_config

        if self.adb_config["ADB_PATH"]:
            adb.adb_path = self.adb_config["ADB_PATH"]

        print(f"🔗 正在連線至裝置: {self.adb_config["device_serial"]} ...")
        try:
            self.device = adb.device(serial=self.adb_config["device_serial"])
            print(f"✅ 連線成功: {self.device.prop.name} (Serial: {self.device.serial})")
        except Exception as e:
            print(f"❌ 連線失敗，請檢查序號或 ADB 伺服器: {e}")
            raise e
        
    def get_screenshot(self):
        """ 
        獲取畫面並轉為 OpenCV 格式 
        (效能比 subprocess 快很多，且不需要處理 Windows 換行符號)
        """
        try:
            # 1. adbutils 直接回傳 PIL Image (RGB 格式)
            pil_image = self.device.screenshot()
            
            # 2. 將 PIL 轉為 OpenCV 格式 (RGB -> BGR)
            # 因為 OpenCV 習慣用 BGR，但 PIL 是 RGB
            open_cv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
            
            return open_cv_image
        except Exception as e:
            print(f"❌ 截圖失敗: {e}")
            return None

    def tap(self, x, y, max_offset = 3):
        """ 模擬點擊 (含隨機偏移) """
        dx = random.randint(-max_offset, max_offset)
        dy = random.randint(-max_offset, max_offset)
        final_x = x + dx
        final_y = y + dy
        self.device.click(final_x, final_y)

    def stop_app(self, package_name:str | None = None):
        target = package_name or self.adb_config["target_app_package"]
        print(f"正在關閉 APP: {target}")
        self.device.app_stop(target)

    def start_app(self, package_name:str | None = None):
        target = package_name or self.adb_config["target_app_package"]
        print(f"正在開啟 APP: {target}")
        self.device.app_start(target)

    def restart_app(self, package_name:str | None = None):
        """ [系統] 快速重啟 (殺掉 -> 打開) """
        self.stop_app(package_name)
        time.sleep(3.0) # 系統反應時間
        self.start_app(package_name)
