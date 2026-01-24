import subprocess
import numpy as np
import random
import cv2
import time
import re
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
        
         # 1. 取得真實解析度
        self.real_w, self.real_h = self._get_device_resolution()
        
        # 2. 計算「等比」縮放比例
        # 我們比較 寬度比 和 高度比，取「比較小」的那個，確保畫面塞得進去且不變形
        ratio_w = self.real_w / self.adb_config["design_width"]
        ratio_h = self.real_h / self.adb_config["design_height"]
        
        self.scale = min(ratio_w, ratio_h) # ⭐️ 關鍵：只用一個比例
        
        # 3. 計算偏移量 (Offset) - 用來處理黑邊
        # 算出縮放後，內容實際佔用的寬高
        actual_content_w = self.adb_config["design_width"] * self.scale
        actual_content_h = self.adb_config["design_height"] * self.scale
        
        # 算出多出來的黑邊 (除以 2 是為了置中)
        self.offset_x = (self.real_w - actual_content_w) / 2
        self.offset_y = (self.real_h - actual_content_h) / 2
        
        print(f"📱 解析度: {self.real_w}x{self.real_h}")
        print(f"⚖️  縮放比: {self.scale:.3f} | ↔ X偏移: {self.offset_x:.1f} | ↕ Y偏移: {self.offset_y:.1f}")
        
    def _get_device_resolution(self) -> tuple[int, int]:
        """ 
        使用 ADB 獲取解析度
        回傳: (寬, 高) 
        保證不會回傳 None，失敗時回傳預設值 
        """
        try:
            # 1. 嘗試問手機
            output = self.device.shell("wm size")
            
            # 2. 嘗試抓數字
            if output:
                match = re.search(r"(\d+)x(\d+)", output)
                if match:
                    return int(match.group(1)), int(match.group(2))
            
        except Exception as e:
            print(f"⚠️ 解析度偵測失敗: {e}")
        
        # ==========================================
        # 🛡️ 安全網 (Safety Net)
        # 只要上面發生錯誤 (Exception) 或 沒抓到 (match is None)
        # 程式都會跑到這裡
        # ==========================================
        print(f"⚠️ 無法取得真實解析度，使用預設值: {self.adb_config["design_width"]}x{self.adb_config["design_height"]}")
        return self.adb_config["design_width"], self.adb_config["design_height"]


    def get_screenshot(self):
        """ 
        [核心功能] 獲取畫面 -> 裁切黑邊 -> 縮放至標準大小
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
                print("❌ 截圖解碼失敗 (回傳 None)")
                return None

            # 3. 判斷是否需要縮放與裁切
            # 如果比例是 1.0 且沒有偏移，代表解析度完全一樣，直接回傳
            if self.scale == 1.0 and self.offset_x == 0 and self.offset_y == 0:
                return raw_img

            # --- 處理不同解析度 (等比縮放邏輯) ---
            
            # A. 裁切 (Crop): 去掉手機多餘的黑邊
            # 陣列切片語法: img[y1:y2, x1:x2]
            y_start = int(self.offset_y)
            y_end = int(self.real_h - self.offset_y)
            x_start = int(self.offset_x)
            x_end = int(self.real_w - self.offset_x)
            
            # 防呆：確保裁切範圍合理 (避免負數導致報錯)
            if y_start >= y_end or x_start >= x_end:
                 print(f"⚠️ 裁切參數異常，回傳原始圖片 (Offset: {self.offset_x}, {self.offset_y})")
                 return raw_img

            cropped_img = raw_img[y_start:y_end, x_start:x_end]

            # B. 縮放 (Resize): 變回標準大小 (Design Resolution)
            target_size = (self.adb_config["design_width"], self.adb_config["design_height"])
            final_img = cv2.resize(cropped_img, target_size, interpolation=cv2.INTER_LINEAR)
            
            return final_img

        except Exception as e:
            print(f"❌ 截圖流程發生錯誤: {e}")
            import traceback
            traceback.print_exc() # 印出詳細錯誤位置，方便除錯
            return None

    def tap(self, x, y):
        """
        [輸出端] 標準座標 -> 乘上比例 -> 加上偏移量 -> 真實座標
        """
        # 公式： (標準座標 * 縮放比) + 黑邊偏移
        real_x = int(x * self.scale + self.offset_x)
        real_y = int(y * self.scale + self.offset_y)
        
        # print(f"👆 映射: ({x},{y}) -> ({real_x},{real_y})")
        self.device.click(real_x, real_y)

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
