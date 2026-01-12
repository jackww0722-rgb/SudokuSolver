import cv2
import numpy as np
import pytesseract
from pathlib import Path

# Windows Tesseract 路徑設定 (請依您的環境確認)
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

class CellTransfomer:
    """負責單一格子的影像強化"""
    
    @staticmethod
    def process(img: np.ndarray, target_size: tuple = (100, 100)) -> np.ndarray:
        if img is None or img.size == 0:
            return np.zeros(target_size, dtype=np.uint8)

        # 1. 調整大小 (Scale Up)
        # Tesseract 在小圖上表現極差，強制放大能顯著提高準確率
        img_resized = cv2.resize(img, target_size, interpolation=cv2.INTER_CUBIC)

        # 2. 顏色反轉 (Inversion)
        # 這是您目前全滅的主因：必須轉成「白底黑字」
        img_inverted = cv2.bitwise_not(img_resized)

        # 3. 二值化 (Thresholding)
        # 讓字變得很黑，背景變得很白，去除灰色雜訊
        _, img_thresh = cv2.threshold(img_inverted, 127, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)

        # 4. 增加邊框 (Padding)
        # 避免數字黏在邊緣
        padding = 10
        img_padded = cv2.copyMakeBorder(
            img_thresh, 
            padding, padding, padding, padding, 
            cv2.BORDER_CONSTANT, 
            value=255 # 填補白色
        )
        
        return img_padded

class GridRecognizer:
    """負責整個網格的辨識與除錯"""
    
    def __init__(self, debug_dir: Path = None):
        self.debug_dir = debug_dir
        if self.debug_dir:
            self.debug_dir.mkdir(parents=True, exist_ok=True)

    def recognize_grid(self, cell_images: list[np.ndarray]) -> list[list[int]]:
        """
        輸入: 81 張原始切割後的圖片列表 (或 9x9 列表)
        輸出: 9x9 的數字矩陣
        """
        grid_result = []
        
        # 假設輸入是扁平的 81 張圖，或是已經分好 9x9
        # 這裡簡化邏輯，視為處理單一串流
        cells_flat = np.array(cell_images).reshape(-1)
        
        current_row = []
        
        print("開始辨識與除錯輸出...")
        
        for idx, cell_img in enumerate(cells_flat):
            # 1. 預處理
            processed_img = CellTransfomer.process(cell_img)
            
            # 2. (除錯用) 儲存電腦看到的樣子
            if self.debug_dir:
                # 存成 debug_cell_0.jpg, debug_cell_1.jpg ...
                save_path = self.debug_dir / f"cell_{idx}.jpg"
                cv2.imwrite(str(save_path), processed_img)

            # 3. OCR 辨識
            # --psm 10: 單字元模式
            # outputbase digits: 限制為數字
            config = r'--psm 10 --oem 3 -c tessedit_char_whitelist=123456789'
            text = pytesseract.image_to_string(processed_img, config=config).strip()
            
            # 4. 判定結果
            digit = int(text) if text.isdigit() else 0
            current_row.append(digit)
            
            # 每 9 個數字換一行
            if len(current_row) == 9:
                grid_result.append(current_row)
                current_row = []

        return grid_result

# --- 使用範例 ---
if __name__ == "__main__":
    # 模擬路徑
    base_dir = Path.cwd()
    output_debug_dir = base_dir / "debug_output"
    
    # 假設您已經有了切割好的 81 張圖片 (這裡是模擬載入您剛剛上傳的那張圖 81 次)
    # 實際程式中，這裡應該是您切割網格後的圖片 list
    sample_img_path = base_dir / "debug_cell_0_0_resized.jpg"
    if sample_img_path.exists():
        sample_img = cv2.imread(str(sample_img_path), cv2.IMREAD_GRAYSCALE)
        
        # 模擬 81 個格子
        mock_cells = [sample_img] * 81 
        
        recognizer = GridRecognizer(debug_dir=output_debug_dir)
        result_grid = recognizer.recognize_grid(mock_cells)
        
        print("\n辨識結果矩陣:")
        for row in result_grid:
            print(row)
            
        print(f"\n請檢查 {output_debug_dir} 資料夾，看看電腦處理後的圖片是否清晰。")
    else:
        print("找不到測試圖片")