import cv2
import numpy as np
import subprocess
import shutil  # 用來清理舊的 debug 資料夾
from pathlib import Path
from typing import List, Dict, Optional, Any
from .config import GameConfig
from .adb_controller import AdbController



class SudokuVision:
    """
    數獨視覺模組 (Physical Coordinates Version + Debug Mode)
    """
    def __init__(self, config: GameConfig, adb: AdbController):
        self.config = config
        self.adb = adb
        self.templates: Dict[int, List[np.ndarray]] = {}

        # 如果有傳入路徑，自動載入
        if self.config.TEMPLATE_FOLDER:
            self._load_templates(self.config.TEMPLATE_FOLDER)

    def _load_templates(self, template_dir: Path):
        """
        載入 1~9 的多重模板圖片
        支援檔名格式： "1.png", "1_v2.png", "1_bold.png" 等等
        只要檔名是以數字開頭，都會被載入
        """
        if not template_dir.exists():
            print(f"[Vision] ❌ 找不到模板資料夾: {template_dir}")
            return

        print(f"[Vision] 📂 正在載入多重模板...")
        total_count = 0
        
        for i in range(1, 10):
            # 初始化該數字的模板列表
            if i not in self.templates:
                self.templates[i] = []
            
            # 使用 glob 搜尋所有以該數字開頭的 png 檔案
            # 例如找 "1" -> 會抓到 "1.png", "1_new.png", "1 (2).png"
            pattern = f"{i}*.png" 
            files = list(template_dir.glob(pattern))
            
            # 為了避免抓到 "10.png" (雖然數獨只有1-9)，可以加個簡單判斷
            # 但這裡簡單處理即可，因為我們只跑 range(1,10)
            
            for t_path in files:
                # 排除像 "10.png" 這種誤判 (如果未來有兩位數的話)
                # 這裡檢查檔名第一個字元是否真的是該數字
                if not t_path.name.startswith(str(i)):
                    continue

                # 讀取並轉灰階
                img = cv2.imdecode(np.fromfile(str(t_path), dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
                if img is not None:
                    self.templates[i].append(img)
                    total_count += 1
                    # print(f"  👉 載入: {t_path.name}")

        print(f"[Vision] ✅ 共載入 {total_count} 張模板圖片 (涵蓋數字 1-9)")

    def _slice_board(self, full_img: np.ndarray) -> List[List[np.ndarray]]:
        """根據物理座標切割出 81 個格子"""
        cells : list[list[Any]] = [[None]*9 for _ in range(9)]
        gray = cv2.cvtColor(full_img, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape

        for row in range(9):
            for col in range(9):
                # 計算中心點
                cell_x_origin = self.config.region_info["left"] + (col * self.config.region_info["cell_w"])
                cell_y_origin = self.config.region_info["top"] + (row * self.config.region_info["cell_h"])
                center_x = cell_x_origin + (self.config.region_info["cell_w"] // 2)
                center_y = cell_y_origin + (self.config.region_info["cell_h"] // 2)

                # 中心裁切
                x1 = center_x - self.config.vision_info["CROP_RADIUS"]
                x2 = center_x + self.config.vision_info["CROP_RADIUS"]
                y1 = center_y - self.config.vision_info["CROP_RADIUS"]
                y2 = center_y + self.config.vision_info["CROP_RADIUS"]

                # 邊界防呆
                if x1 < 0 or y1 < 0 or x2 > w or y2 > h:
                    cells[row][col] = np.zeros((self.config.vision_info["CROP_RADIUS"]*2, self.config.vision_info["CROP_RADIUS"]*2), dtype=np.uint8)
                    continue

                cells[row][col] = gray[y1:y2, x1:x2]
        
        return cells

    def recognize_board(self, save_debug: bool = False) -> List[List[int]]:
        """
        執行截圖 -> 切割 -> 識別
        :param save_debug: 是否儲存切割後的格子圖以便除錯
        """
        # 1. 截圖
        img = self.adb.get_screenshot()
        if img is None:
            return [[0]*9 for _ in range(9)]

        # 2. 切割
        cells = self._slice_board(img)
        
        # --- 🛠️ 除錯存檔區塊 ---
        if save_debug:
            current_dir = Path(__file__).parent.parent
            debug_dir = current_dir / Path("debug_cells_check")
            # 如果目錄存在，先清空舊的方便觀察
            if debug_dir.exists():
                shutil.rmtree(debug_dir)
            debug_dir.mkdir(parents=True, exist_ok=True)
            
            print(f"\n[Debug] 📸 正在儲存 81 張格子圖至: {debug_dir.absolute()}")
            
            for r in range(9):
                for c in range(9):
                    fname = debug_dir / f"cell_{r}_{c}.png"
                    # 使用 imencode 支援中文路徑存檔
                    cv2.imencode(".png", cells[r][c])[1].tofile(str(fname))
            print("[Debug] ✅ 儲存完畢！請打開資料夾檢查圖片是否偏移。\n")
        # -----------------------

        # 3. 比對
        grid_result = [[0]*9 for _ in range(9)]
        THRESHOLD = 0.5 or self.config.vision_info["CONFIDENCE_THRESHOLD"]


        for r in range(9):
            for c in range(9):
                cell_img = cells[r][c]
                best_score = -1
                detected_num = 0

                for num, tmpl_list in self.templates.items():
                    for tmpl in tmpl_list:
                        if tmpl.shape[0] > cell_img.shape[0] or tmpl.shape[1] > cell_img.shape[1]:
                            continue

                        res = cv2.matchTemplate(cell_img, tmpl, cv2.TM_CCOEFF_NORMED)
                        score = np.max(res)

                        if score > best_score:
                            best_score = score
                            detected_num = num
                
                if best_score > THRESHOLD:
                    grid_result[r][c] = detected_num

        return grid_result
    
    def _cv2_imread_safe(self, file_path):
        """ 
        [工具] 解決 Windows 路徑含有中文或特殊字元無法讀取的問題 
        這是 find_and_get_pos 需要呼叫的幫手函式
        """
        try:
            # 先用 numpy 讀取原始數據 (避開路徑編碼問題)
            img_array = np.fromfile(str(file_path), dtype=np.uint8)
            # 再解碼成圖片
            img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            return img
        except Exception as e:
            print(f"⚠️ 讀取圖片失敗: {file_path} | 錯誤: {e}")
            return None

    def find_and_get_pos(self, screen, template_name, threshold : float | None = None):
        """ 
        主要找圖邏輯，包含完整的防呆機制 
        """
        threshold = threshold or self.config.vision_info["ANCHOR_CONFIDENCE"]

        # 1. 組合完整路徑
        template_path = self.config.TEMPLATE_FOLDER/template_name
        
        # 2. 呼叫上面的安全讀取法 (這行原本報錯，因為找不到上面的函式)
        template = self._cv2_imread_safe(template_path)
        
        # 3. 防呆檢查：圖片讀取失敗
        if template is None:
            print(f"❌ [Error] 找不到或無法讀取圖片: {template_path}")
            return None


        # 4. 防呆檢查：螢幕截圖失敗
        if screen is None:
             print("❌ [Error] 螢幕截圖失敗 (Screen is None)，請檢查 ADB 連線")
             return None


        # 5. 防呆檢查：尺寸不合
        # (一定要在確認 template 不是 None 之後才能做)
        if template.shape[0] > screen.shape[0] or template.shape[1] > screen.shape[1]:
            # print(f"⚠️ [Warning] 圖片比螢幕大: {template_name}")
            return None

        # 6. 開始匹配
        result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        
        if max_val >= threshold:
            h, w = template.shape[:2]
            center_x = max_loc[0] + w // 2
            center_y = max_loc[1] + h // 2
            return (center_x, center_y)
            
        return None