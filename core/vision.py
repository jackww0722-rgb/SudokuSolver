import cv2
import numpy as np
import subprocess
import shutil  # 用來清理舊的 debug 資料夾
from pathlib import Path
from typing import List, Dict, Optional

class SudokuVision:
    """
    數獨視覺模組 (Physical Coordinates Version + Debug Mode)
    """

    # ==========================================
    # ⚙️ 物理參數 (請確認這些與您的手機解析度吻合)
    # ==========================================
    BOARD_LEFT = 35
    BOARD_TOP = 505
    BOARD_WIDTH = 1011
    BOARD_HEIGHT = 1011

    # 自動計算
    CELL_WIDTH = BOARD_WIDTH // 9
    CELL_HEIGHT = BOARD_HEIGHT // 9
    
    # 裁切半徑 (從中心往外擴張 35px = 70x70)
    CROP_RADIUS = 35 

    def __init__(self, template_dir: Optional[Path] = None, adb_serial: str = "R5CW915J6XV"):
        self.adb_serial = adb_serial
        self.templates: Dict[int, List[np.ndarray]] = {}
        
        # 如果有傳入路徑，自動載入
        if template_dir:
            self.load_templates(template_dir)

    def load_templates(self, template_dir: Path):
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

    def capture_screen(self) -> Optional[np.ndarray]:
        """透過 ADB 截取原始畫質圖片"""
        try:
            cmd = ["adb", "-s", self.adb_serial, "exec-out", "screencap", "-p"]
            pipe = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
            image_bytes = pipe.stdout.read()
            
            if not image_bytes:
                print("[Vision] ❌ 截圖回傳為空")
                return None
            
            image_array = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
            return img

        except Exception as e:
            print(f"[Vision] ❌ ADB 截圖錯誤: {e}")
            return None

    def _slice_board(self, full_img: np.ndarray) -> List[List[np.ndarray]]:
        """根據物理座標切割出 81 個格子"""
        cells = [[None]*9 for _ in range(9)]
        gray = cv2.cvtColor(full_img, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape

        for row in range(9):
            for col in range(9):
                # 計算中心點
                cell_x_origin = self.BOARD_LEFT + (col * self.CELL_WIDTH)
                cell_y_origin = self.BOARD_TOP + (row * self.CELL_HEIGHT)
                center_x = cell_x_origin + (self.CELL_WIDTH // 2)
                center_y = cell_y_origin + (self.CELL_HEIGHT // 2)

                # 中心裁切
                x1 = center_x - self.CROP_RADIUS
                x2 = center_x + self.CROP_RADIUS
                y1 = center_y - self.CROP_RADIUS
                y2 = center_y + self.CROP_RADIUS

                # 邊界防呆
                if x1 < 0 or y1 < 0 or x2 > w or y2 > h:
                    cells[row][col] = np.zeros((self.CROP_RADIUS*2, self.CROP_RADIUS*2), dtype=np.uint8)
                    continue

                cells[row][col] = gray[y1:y2, x1:x2]
        
        return cells

    def recognize_board(self, save_debug: bool = False) -> List[List[int]]:
        """
        執行截圖 -> 切割 -> 識別
        :param save_debug: 是否儲存切割後的格子圖以便除錯
        """
        # 1. 截圖
        img = self.capture_screen()
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
        THRESHOLD = 0.5

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

    #grand order
    def scan_board(self):
        # 設定模板路徑
        current_dir = Path(__file__).parent.parent
        tpl_dir = current_dir / "templates"
        
        vision = SudokuVision(template_dir=tpl_dir)
        
        print("🚀 開始識別 (開啟除錯存圖模式)...")
        
        # 這裡設為 True，就會把格子存下來
        result = vision.recognize_board(save_debug=True)
        
        print("\n--- 識別結果 ---")
        for row in result:
            print(row)
        return result
            



# --- 測試區 ---
if __name__ == "__main__":
    # 設定模板路徑
    current_dir = Path(__file__).parent.parent
    tpl_dir = current_dir / "templates"
    
    vision = SudokuVision(template_dir=tpl_dir)
    
    print("🚀 開始識別 (開啟除錯存圖模式)...")
    
    # 這裡設為 True，就會把格子存下來
    result = vision.recognize_board(save_debug=True)
    
    print("\n--- 識別結果 ---")
    for row in result:
        print(row)