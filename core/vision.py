import cv2
import numpy as np
import shutil  # 用來清理舊的 debug 資料夾
from pathlib import Path
from typing import List, Dict, Any
from .config import GameConfig
from .adb_controller import AdbController
from .logger import logger


class SudokuVision:
    """
    數獨視覺模組 (Physical Coordinates Version + Debug Mode)
    """
    def __init__(self, config: GameConfig, adb: AdbController, positions: dict | None = None):
        self.config = config
        self.adb = adb
        self.templates: Dict[int, List[np.ndarray]] = {}
        self.positions = None
        self._template_cache = {}
        self.scale = 1.0
        self.positions = positions if positions is not None else {}

    def set_screen_scale(self, screen_w: int):
        """主程式校正時呼叫，告訴視覺部現在的比例"""
        BASE_WIDTH = 1080
        self.scale = screen_w / BASE_WIDTH
        logger.debug(f"📐 視覺部已鎖定縮放比例: {self.scale:.2f}")


    def _cv2_imread_safe(self, file_path, flags: int = cv2.IMREAD_GRAYSCALE):
        """ 
        [工具] 解決 Windows 路徑含有中文或特殊字元無法讀取的問題 
        這是 find_and_get_pos 需要呼叫的幫手函式
        """
        try:
            # 先用 numpy 讀取原始數據 (避開路徑編碼問題)
            img_array = np.fromfile(str(file_path), dtype=np.uint8)
            # 再解碼成圖片
            img = cv2.imdecode(img_array, flags)
            return img
        except Exception as e:
            logger.warning(f"讀取圖片失敗: {file_path} | 錯誤: {e}")
            return None


    def _get_processed_template(self, template_name: str) -> np.ndarray | None:
        """
        [共用快取中心] 負責讀取硬碟、灰階化、動態縮放，並存入記憶體快取
        """
        
        # 🌟 聰明的雙層鑰匙：用 (檔名, 縮放比例) 當作快取字典的 Key
        cache_key = (template_name, self.scale)
        
        # 1. 如果「縮放好的版本」已經在快取裡，直接秒殺回傳！
        if cache_key in self._template_cache:
            return self._template_cache[cache_key]

        # 2. 如果沒有，先看看有沒有「原始大小 (scale=1.0)」的底圖
        raw_key = (template_name, 1.0)
        if raw_key not in self._template_cache:
            # 真的連底圖都沒有，才去老老實實讀硬碟 (只有程式剛開局會跑到這)
            template_path = self.config.TEMPLATE_FOLDER / template_name
            raw_img = self._cv2_imread_safe(template_path)
            
            if raw_img is None:
                logger.warning(f"❌ 找不到特徵圖: {template_path}")
                return None
                
            self._template_cache[raw_key] = raw_img

        # 3. 拿出底圖來進行縮放
        raw_template = self._template_cache[raw_key]
        if self.scale != 1.0:
            new_w = int(raw_template.shape[1] * self.scale)
            new_h = int(raw_template.shape[0] * self.scale)
            scaled_template = cv2.resize(raw_template, (new_w, new_h), interpolation=cv2.INTER_AREA)
        else:
            scaled_template = raw_template

        # 4. 🌟 把縮放好的圖存進快取！下次就算呼叫一萬次，也不用再算 cv2.resize 了
        self._template_cache[cache_key] = scaled_template
        
        return scaled_template
    
    
    def load_templates(self):
        """
        載入 1~9 的多重模板圖片
        支援檔名格式： "1.png", "1_v2.png", "1_bold.png" 等等
        只要檔名是以數字開頭，都會被載入
        """
        if not self.config.TEMPLATE_FOLDER.exists():
            logger.warning(f"找不到模板資料夾: {self.config.TEMPLATE_FOLDER}")
            return

        logger.debug(f"正在載入模板...")
        total_count = 0
        
        for i in range(1, 10):
            # 初始化該數字的模板列表
            if i not in self.templates:
                self.templates[i] = []
            
            # 使用 glob 搜尋所有以該數字開頭的 png 檔案
            # 例如找 "1" -> 會抓到 "1.png", "1_new.png", "1 (2).png"
            pattern = f"{i}*.png" 
            files = list(self.config.TEMPLATE_FOLDER.glob(pattern))
            
            # 為了避免抓到 "10.png" (雖然數獨只有1-9)，可以加個簡單判斷
            # 但這裡簡單處理即可，因為我們只跑 range(1,10)
            
            for t_path in files:
                # 排除像 "10.png" 這種誤判 (如果未來有兩位數的話)
                # 這裡檢查檔名第一個字元是否真的是該數字
                if not t_path.name.startswith(str(i)):
                    continue

                # 讀取並轉灰階
                img = self._get_processed_template(t_path.name)
                if img is not None:
                    self.templates[i].append(img)
                    total_count += 1

        logger.debug(f"共載入 {total_count} 張模板圖片 (涵蓋數字 1-9)")
        
    

    def _slice_board(self, full_img: np.ndarray) -> List[List[np.ndarray]]:
        """根據物理座標切割出 81 個格子"""

        # 安全防呆：確保老闆有把地圖交給我們
        if not self.positions:
            logger.warning("⚠️ 錯誤：視覺部尚未取得座標地圖！")
            dummy_img = np.zeros((10, 10), dtype=np.uint8)
            return [[dummy_img]*9 for _ in range(9)]
        

        cells : list[list[np.ndarray]] = []
        gray = cv2.cvtColor(full_img, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape
        crop_radius = int(self.positions["cell_size"] * 0.4)

        for row in range(9):
            row_cells: list[np.ndarray] = []

            for col in range(9):
                
                # 計算中心點
                center_x, center_y = self.positions["cells"][(row, col)]

                # 中心裁切
                x1 = center_x - crop_radius
                x2 = center_x + crop_radius
                y1 = center_y - crop_radius
                y2 = center_y + crop_radius

                # 邊界防呆
                if x1 < 0 or y1 < 0 or x2 > w or y2 > h:
                    row_cells.append(np.zeros((crop_radius*2, crop_radius*2), dtype=np.uint8))
                else:
                    # 正常裁切並加入
                    row_cells.append(gray[y1:y2, x1:x2])
            
            # 把這一列加進總陣列
            cells.append(row_cells)
        
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
        
        # ---除錯存檔區塊 ---
        if save_debug:
            current_dir = Path(__file__).parent.parent
            debug_dir = current_dir / Path("debug_cells_check")
            # 如果目錄存在，先清空舊的方便觀察
            if debug_dir.exists():
                shutil.rmtree(debug_dir)
            debug_dir.mkdir(parents=True, exist_ok=True)
            
            logger.debug(f"\n正在儲存 81 張格子圖至: {debug_dir.absolute()}")
            
            for r in range(9):
                for c in range(9):
                    fname = debug_dir / f"cell_{r}_{c}.png"
                    # 使用 imencode 支援中文路徑存檔
                    cv2.imencode(".png", cells[r][c])[1].tofile(str(fname))
            logger.debug("儲存完畢！請打開資料夾檢查圖片是否偏移。\n")
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
    


    def find_and_get_pos(self, screen, template_name, threshold : float | None = None):
        """ 
        主要找圖邏輯，包含完整的防呆機制 
        """
        threshold = threshold or self.config.vision_info["ANCHOR_CONFIDENCE"]

        # 4. 防呆檢查：螢幕截圖失敗
        if screen is None:
             logger.warning("螢幕截圖失敗 (Screen is None)，請檢查 ADB 連線")
             return None


        # 5. 防呆檢查：尺寸不合
        # (一定要在確認 template 不是 None 之後才能做)
        if (template := self._get_processed_template(template_name)) is None:
            return None

        if template.shape[0] > screen.shape[0] or template.shape[1] > screen.shape[1]:
            return None

        # ==========================================
        # 🌟 關鍵修復：確保大圖也是灰階！
        # 因為 template 已經被我們優化成純灰階了，screen 也必須是灰階
        # ==========================================
        if len(screen.shape) == 3:
            gray_screen = cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY)
        else:
            gray_screen = screen


        # 6. 開始匹配
        result = cv2.matchTemplate(gray_screen, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        
        if max_val >= threshold:
            h, w = template.shape[:2]
            center_x = max_loc[0] + w // 2
            center_y = max_loc[1] + h // 2
            if self.config.DEBUG_MODE == True:
                logger.debug(f"目前比對{template_name}，相似度{max_val}")
            return (center_x, center_y)
        
        elif self.config.DEBUG_MODE == True:
            logger.warning(f"未找到{template_name}")
            
        return None