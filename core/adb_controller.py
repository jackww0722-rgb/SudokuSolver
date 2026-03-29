import numpy as np
import cv2
import time
import re
from typing import Any
from adbutils import adb
import os
from pathlib import Path



class AdbController:
    def __init__(self, adb_config: dict[str, Any]):
        """
        1. 初始化階段：只綁定設定檔，預設所有屬性。
        絕對不碰網路連線，保證瞬間建立物件不報錯。
        """
        self.adb_config = adb_config
        self.device: Any = None
        
        # 預設解析度與縮放屬性
        self.real_w = 0
        self.real_h = 0
        self.scale = 1.0
        self.offset_x = 0.0
        self.offset_y = 0.0

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
                print(f"🔧 已動態掛載自訂 ADB 引擎目錄: {adb_folder}")
            else:
                print(f"⚠️ 設定檔中的 ADB 路徑不存在: {custom_adb_file}")

    def connect(self) -> bool:
        """
        2. 連線階段：由外部主動呼叫，負責連線並更新設備狀態。
        """
        target_serial = self.adb_config.get("device_serial", "").strip()
        print(f"正在準備連線...")

        try:
            if not target_serial:
                print("未指定序號，正在自動搜尋裝置...")
                devices = adb.device_list() # type: ignore
                if not devices:
                    raise RuntimeError("未偵測到任何 ADB 裝置！請確認模擬器已開啟。")
                self.device = devices[0]
                self.device.shell("echo hello") # 測試連線
                print(f"自動鎖定裝置: {self.device.serial}")
            else:
                self.device = adb.device(serial=target_serial)
                self.device.shell("echo hello") # 測試連線
                print(f"連線成功: {self.device.serial}")
            
            # 連線成功後，順便呼叫計算解析度的方法
            self._update_resolution_and_scale()
            return True
            
        except Exception as e:
            print(f"連線失敗: {e}")
            return False

    def _update_resolution_and_scale(self):
        """
        3. 計算階段：負責向設備要解析度，並計算縮放比例與偏移量。
        設為私有方法 (前面加底線)，因為外部不需要直接呼叫它。
        """
        if not self.device:
            return

        self.real_w, self.real_h = self._get_device_resolution()
        
        ratio_w = self.real_w / self.adb_config["design_width"]
        ratio_h = self.real_h / self.adb_config["design_height"]
        
        self.scale = min(ratio_w, ratio_h)
        actual_content_w = self.adb_config["design_width"] * self.scale
        actual_content_h = self.adb_config["design_height"] * self.scale
        
        self.offset_x = (self.real_w - actual_content_w) / 2
        self.offset_y = (self.real_h - actual_content_h) / 2
        
        print(f"解析度: {self.real_w}x{self.real_h}")
        print(f"縮放比: {self.scale:.3f} | ↔ X偏移: {self.offset_x:.1f} | ↕ Y偏移: {self.offset_y:.1f}")

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
            print(f"解析度偵測失敗: {e}")
        
        # ==========================================
        # 🛡️ 安全網 (Safety Net)
        # 只要上面發生錯誤 (Exception) 或 沒抓到 (match is None)
        # 程式都會跑到這裡
        # ==========================================
        print(f"無法取得真實解析度，使用預設值: {self.adb_config["design_width"]}x{self.adb_config["design_height"]}")
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
                print("截圖解碼失敗 (回傳 None)")
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
                 print(f"裁切參數異常，回傳原始圖片 (Offset: {self.offset_x}, {self.offset_y})")
                 return raw_img

            cropped_img = raw_img[y_start:y_end, x_start:x_end]

            # B. 縮放 (Resize): 變回標準大小 (Design Resolution)
            target_size = (self.adb_config["design_width"], self.adb_config["design_height"])
            final_img = cv2.resize(cropped_img, target_size, interpolation=cv2.INTER_LINEAR)
            
            return final_img

        except Exception as e:
            print(f"截圖流程發生錯誤: {e}")
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
        self.stop_app(package_name)
        time.sleep(3.0) # 系統反應時間
        self.start_app(package_name)
